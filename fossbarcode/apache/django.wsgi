import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

sys.path.append('/var/www/html/foss-barcode')
sys.path.append('/var/www/html/foss-barcode/fossbarcode')
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
