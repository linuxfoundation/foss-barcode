from compliance.barcode.models import Barcode_Record, SPDX_Files, FOSS_Components, Patch_Files
from django.contrib import admin

admin.site.register(Barcode_Record)
admin.site.register(SPDX_Files)
admin.site.register(FOSS_Components)
admin.site.register(Patch_Files)
