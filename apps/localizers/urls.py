from django.conf.urls.defaults import patterns, url, include

from . import views

# These will all start with /localizers/<locale_code>/
detail_patterns = patterns('',
    url('^$', views.locale_dashboard, name='localizers.locale_dashboard'),
    url('^categories/$', views.categories, name='localizers.categories'),
)

urlpatterns = patterns('',
    # URLs for a single user.
    ('^localizers/(?P<locale_code>[\w-]+)/', include(detail_patterns)),

    url('^localizers/set_motd$', views.set_motd, name='localizers.set_motd'),
    url('^localizers/$', views.summary, name='localizers.dashboard'),
)
