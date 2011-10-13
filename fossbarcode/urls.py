from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^barcode/$', 'fossbarcode.barcode.views.input'),
    (r'^barcode/checksum/(?P<checksum>[0-9a-fA-F]+)$', 'fossbarcode.barcode.views.by_checksum'),
    (r'^barcode/input/$', 'fossbarcode.barcode.views.input'),
    (r'^barcode/documentation/$', 'fossbarcode.barcode.views.documentation'),
    (r'^barcode/records/$', 'fossbarcode.barcode.views.records'),
    (r'^barcode/search/$', 'fossbarcode.barcode.views.search'),
    (r'^barcode/search_dupes/$', 'fossbarcode.barcode.views.search_dupes'),
    (r'^barcode/sysconfig/$', 'fossbarcode.barcode.views.sysconfig'),
    (r'^barcode/taskstatus/$', 'fossbarcode.barcode.views.taskstatus'),
    url(r'^barcode/(?P<record_id>\d+)/detail/$', 'fossbarcode.barcode.views.detail', name="detail-url"),
    url(r'^barcode/(?P<record_id>\d+)/detail/(?P<revision>[0-9a-fA-F]+)$', 'fossbarcode.barcode.views.detail', name="detail-revision-url"),
    url(r'^barcode/(?P<record_id>\d+)/detail/(?P<revision>[0-9a-fA-F]+)/(?P<path>.+)$', 'fossbarcode.barcode.views.history_file', name="history-file-url"),
    url(r'^barcode/(?P<record_id>\d+)/json/history/$', 'fossbarcode.barcode.views.history_json', name="history-url"),
    url(r'^barcode/licenses/$', 'fossbarcode.barcode.views.licenses_json', name='licenses-url'),
    url(r'^barcode/licenses/new$', 'fossbarcode.barcode.views.new_license', name='new-license-url'),
    url(r'^barcode/licenses/(?P<license_id>\d+)/json/$', 'fossbarcode.barcode.views.license_json', name='license-url'),
    (r'^site_media/js/history.js', 'fossbarcode.barcode.views.history_js'),
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve',
	            {'document_root':  settings.STATIC_DOC_ROOT}),
    (r'^admin/', include(admin.site.urls)),
)
