from django.db import models
from django.forms import ModelForm, forms, Form
from django import forms
import os
import re

# Create your models here.

class Product_Record(models.Model):
    company = models.CharField('Company Name', max_length=200)
    website = models.CharField('Company Website', max_length=200)
    record_date = models.DateTimeField('Test Date', auto_now=True)
    contact = models.CharField('Compliance Contact Name (optional)', max_length=200, blank=True)
    email = models.CharField('Compliance Contact Email', max_length=200)
    product = models.CharField('Product Name', max_length=200)
    version = models.CharField('Product Version', max_length=20)
    release = models.CharField('Product Release', max_length=20)
    checksum = models.CharField('Checksum', max_length=200, blank=True)
    def __unicode__(self):
        return self.product

class FOSS_Components(models.Model):
    brecord = models.ForeignKey(Product_Record)
    package = models.CharField(max_length=200)
    version = models.CharField(max_length=20)
    copyright = models.CharField(max_length=100)
    attribution = models.CharField(max_length=100)
    license = models.CharField(max_length=40)
    license_url = models.CharField(max_length=200)
    url = models.CharField(max_length=200)
    spdx_file = models.CharField(max_length=100, blank=True)
    def __unicode__(self):
        return self.package

class Patch_Files(models.Model):
    frecord = models.ForeignKey(FOSS_Components)
    path = models.CharField(max_length=400)
    def __unicode__(self):
        return self.path

class System_Settings(models.Model):
    name = models.CharField(max_length=32, db_index=True)
    value = models.CharField(max_length=128)
    descr = models.CharField(max_length=256)
    last_updated = models.DateTimeField('Updated', auto_now=True)
    user_updated = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s = %s" % (self.name, self.value)

class RecordForm(ModelForm):   
    class Meta:
        model = Product_Record

    foss_component = forms.CharField(max_length=200, required=False)
    foss_version = forms.CharField(max_length=20, required=False)
    foss_copyright = forms.CharField(max_length=100, required=False)
    foss_attribution = forms.CharField(max_length=100, required=False)
    foss_license = forms.CharField(max_length=40, required=False)
    foss_license_url = forms.CharField(max_length=200, required=False)
    foss_url = forms.CharField(max_length=200, required=False)
    foss_spdx = forms.CharField(max_length=100, required=False)


