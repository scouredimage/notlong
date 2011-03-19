from django.conf.urls.defaults import *

handler500 = 'shorten.views.server_error'

urlpatterns = patterns('',
  (r'^shorten/$', 'shorten.views.shorten'),
  (r'^expand/$', 'shorten.views.expand'),
  (r'^(?P<token>[A-Za-z0-9]+)/$', 'shorten.views.follow'),
)
