from django.db import models
from django.forms import ModelForm, forms, Form
from django import forms
import os
import re

# Create your models here.

class Barcode_Record(models.Model):
    company = models.CharField('Company Name', max_length=200)
    website = models.CharField('FOSS Website (optional)', max_length=200, blank=True)
    record_date = models.DateTimeField('Test Date', auto_now=True)
    contact = models.CharField('Compliance Contact Name (optional)', max_length=200, blank=True)
    email = models.CharField('Compliance Contact Email', max_length=200)
    product = models.CharField('Product Name', max_length=200)
    version = models.CharField('Product Version', max_length=20)
    release = models.CharField('Product Release', max_length=20)
    checksum = models.CharField('Checksum', max_length=200, blank=True)
    def __unicode__(self):
        return self.product

class SPDX_Files(models.Model):
    brecord = models.ForeignKey(Barcode_Record)
    path = models.CharField(max_length=400)
    def __unicode__(self):
        return self.path

class FOSS_Components(models.Model):
    brecord = models.ForeignKey(Barcode_Record)
    package = models.CharField(max_length=200)
    version = models.CharField(max_length=20)
    license = models.CharField(max_length=40)
    url = models.CharField(max_length=200)
    def __unicode__(self):
        return self.package

class Patch_Files(models.Model):
    frecord = models.ForeignKey(FOSS_Components)
    path = models.CharField(max_length=400)
    def __unicode__(self):
        return self.path

class RecordForm(ModelForm):   
    class Meta:
        model = Barcode_Record

    spdx_files = forms.CharField(widget=forms.Textarea, required=False)
    foss_component = forms.CharField(max_length=200, required=False)
    foss_version = forms.CharField(max_length=20, required=False)
    foss_license = forms.CharField(max_length=40, required=False)
    foss_url = forms.CharField(max_length=200, required=False)

