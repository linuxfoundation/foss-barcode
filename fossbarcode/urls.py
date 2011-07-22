from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^barcode/$', 'fossbarcode.barcode.views.input'),
    (r'^barcode/input/$', 'fossbarcode.barcode.views.input'),
    (r'^barcode/dirlist/$', 'fossbarcode.barcode.views.dirlist'),
    (r'^barcode/documentation/$', 'fossbarcode.barcode.views.documentation'),
    (r'^barcode/records/$', 'fossbarcode.barcode.views.records'),
    (r'^barcode/search/$', 'fossbarcode.barcode.views.search'),
    (r'^barcode/search_dupes/$', 'fossbarcode.barcode.views.search_dupes'),
    (r'^barcode/sysconfig/$', 'fossbarcode.barcode.views.sysconfig'),
    (r'^barcode/taskstatus/$', 'fossbarcode.barcode.views.taskstatus'),
    url(r'^barcode/(?P<record_id>\d+)/detail/$', 'fossbarcode.barcode.views.detail', name="detail-url"),
    url(r'^barcode/(?P<record_id>\d+)/detail/(?P<revision>[0-9a-fA-F]+)$', 'fossbarcode.barcode.views.detail', name="detail-revision-url"),
    url(r'^barcode/(?P<record_id>\d+)/json/history/$', 'fossbarcode.barcode.views.history_json', name="history-url"),
    (r'^site_media/js/history.js', 'fossbarcode.barcode.views.history_js'),
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve',
	            {'document_root':  settings.STATIC_DOC_ROOT}),
    (r'^admin/', include(admin.site.urls)),
)
