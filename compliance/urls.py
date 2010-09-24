from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^barcode/$', 'compliance.barcode.views.input'),
    (r'^barcode/input/$', 'compliance.barcode.views.input'),
    (r'^barcode/dirlist/$', 'compliance.barcode.views.dirlist'),
    (r'^barcode/documentation/$', 'compliance.barcode.views.documentation'),
    (r'^barcode/records/$', 'compliance.barcode.views.records'),
    (r'^barcode/search/$', 'compliance.barcode.views.search'),
    (r'^barcode/taskstatus/$', 'compliance.barcode.views.taskstatus'),
    (r'^barcode/(?P<record_id>\d+)/detail/$', 'compliance.barcode.views.detail'),
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve',
	            {'document_root':  settings.STATIC_DOC_ROOT}),
    (r'^admin/', include(admin.site.urls)),
)
