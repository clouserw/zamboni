import calendar
from datetime import datetime, timedelta
from subprocess import Popen, PIPE

from django.conf import settings

import cronjobs
import commonware.log

import amo
from amo.utils import chunked
from addons.utils import AdminActivityLogMigrationTracker
from bandwagon.models import Collection
from cake.models import Session
from devhub.models import ActivityLog, LegacyAddonLog
from files.models import TestResultCache
from sharing import SERVICES_LIST, LOCAL_SERVICES_LIST
from stats.models import AddonShareCount, Contribution
from django.utils import translation

from . import tasks

log = commonware.log.getLogger('z.cron')


@cronjobs.register
def gc(test_result=True):
    """Site-wide garbage collections."""

    days_ago = lambda days: datetime.today() - timedelta(days=days)
    one_hour_ago = datetime.today() - timedelta(hours=1)

    log.debug('Collecting data to delete')

    logs = (ActivityLog.objects.filter(created__lt=days_ago(90))
            .exclude(action__in=amo.LOG_KEEP).values_list('id', flat=True))

    # Paypal only keeps retrying to verify transactions for up to 3 days. If we
    # still have an unverified transaction after 6 days, we might as well get
    # rid of it.
    contributions_to_delete = (Contribution.objects
            .filter(transaction_id__isnull=True, created__lt=days_ago(6))
            .values_list('id', flat=True))

    collections_to_delete = (Collection.objects.filter(
            created__lt=days_ago(2), type=amo.COLLECTION_ANONYMOUS)
            .values_list('id', flat=True))

    for chunk in chunked(logs, 100):
        tasks.delete_logs.delay(chunk)
    for chunk in chunked(contributions_to_delete, 100):
        tasks.delete_stale_contributions.delay(chunk)
    for chunk in chunked(collections_to_delete, 100):
        tasks.delete_anonymous_collections.delay(chunk)
    # Incomplete addons cannot be deleted here because when an addon is
    # rejected during a review it is marked as incomplete. See bug 670295.

    log.debug('Cleaning up sharing services.')
    service_names = [s.shortname for s in SERVICES_LIST]
    # collect local service names
    original_language = translation.get_language()
    for language in settings.LANGUAGES:
        translation.activate(language)
        service_names.extend([unicode(s.shortname)
                              for s in LOCAL_SERVICES_LIST])
    translation.activate(original_language)

    AddonShareCount.objects.exclude(service__in=set(service_names)).delete()

    log.debug('Cleaning up cake sessions.')
    # cake.Session uses Unix Timestamps
    two_days_ago = calendar.timegm(days_ago(2).utctimetuple())
    Session.objects.filter(expires__lt=two_days_ago).delete()

    log.debug('Cleaning up test results cache.')
    TestResultCache.objects.filter(date__lt=one_hour_ago).delete()

    log.debug('Cleaning up test results extraction cache.')
    if settings.NETAPP_STORAGE and settings.NETAPP_STORAGE != '/':
        cmd = ('find', settings.NETAPP_STORAGE, '-maxdepth', '1', '-name',
               'validate-*', '-mtime', '+7', '-type', 'd',
               '-exec', 'rm', '-rf', "{}", ';')

        output = Popen(cmd, stdout=PIPE).communicate()[0]

        for line in output.split("\n"):
            log.debug(line)

    else:
        log.warning('NETAPP_STORAGE not defined.')

    if settings.PACKAGER_PATH:
        log.debug('Cleaning up old packaged add-ons.')

        cmd = ('find', settings.PACKAGER_PATH,
               '-name', '*.zip', '-mtime', '+1', '-type', 'f',
               '-exec', 'rm', '{}', ';')
        output = Popen(cmd, stdout=PIPE).communicate()[0]

        for line in output.split("\n"):
            log.debug(line)

    if settings.COLLECTIONS_ICON_PATH:
        log.debug('Cleaning up uncompressed icons.')

        cmd = ('find', settings.COLLECTIONS_ICON_PATH,
               '-name', '*__unconverted', '-mtime', '+1', '-type', 'f',
               '-exec', 'rm', '{}', ';')
        output = Popen(cmd, stdout=PIPE).communicate()[0]

        for line in output.split("\n"):
            log.debug(line)

    if settings.USERPICS_PATH:
        log.debug('Cleaning up uncompressed userpics.')

        cmd = ('find', settings.USERPICS_PATH,
               '-name', '*__unconverted', '-mtime', '+1', '-type', 'f',
               '-exec', 'rm', '{}', ';')
        output = Popen(cmd, stdout=PIPE).communicate()[0]

        for line in output.split("\n"):
            log.debug(line)


@cronjobs.register
def migrate_admin_logs():
    # Get the highest id we've looked at.
    a = AdminActivityLogMigrationTracker()
    id = a.get() or 0

    # filter here for addappversion
    items = LegacyAddonLog.objects.filter(
            type=amo.LOG.ADD_APPVERSION.id, pk__gt=id).values_list(
            'id', flat=True)
    for chunk in chunked(items, 100):
        tasks.migrate_admin_logs.delay(chunk)
        a.set(chunk[-1])
