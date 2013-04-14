from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

import commonware.log

from access.models import Group, GroupUser
from users.models import UserProfile

class Command(BaseCommand):
    help = ("Remove a user from a group. Syntax: \n"
            "    ./manage.py removeuserfromgroup <userid> <groupid>")

    log = commonware.log.getLogger('z.users')

    def handle(self, *args, **options):

        try:

            user = UserProfile.objects.get(pk=args[0])
            group = Group.objects.get(pk=args[1])

            # Doesn't actually check if the user was in the group or not
            GroupUser.objects.filter(user=user, group=group).delete()

            # This may double log due to the GroupUser callback. I don't mind.
            msg = "Removing %s from %s\n" % (user, group)
            self.log.info(msg)
            self.stdout.write(msg)
            # Surprised to see group changing is not a part of CEF logging
            # requirements...

        except IndexError:
            raise CommandError(self.help)
        except ValueError:
            raise CommandError("Use user and group IDs (those are numbers)")
        except Group.DoesNotExist:
            raise CommandError("Group (%s) does not exist." % args[1])
        except UserProfile.DoesNotExist:
            raise CommandError("User (%s) does not exist." % args[0])
