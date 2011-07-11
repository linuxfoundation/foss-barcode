from django.conf import settings
from django.db import models
from django.forms import ModelForm, forms, Form
from django import forms
import os
import re
import shutil
import pickle
import time

# Custom exceptions.
class FileDataMixinCreateError(StandardError):
    pass

# This is a special mix-in class which implements the loading and
# saving of some attributes via a pickle file.  It allows us to use
# traditional version control to audit certain data changes.
class FileDataMixin:
    # To use a FileDataMixin class, define this to be an array
    # of attribute names.  This will be called to get the ID
    # of the FileDataDirMixin object which should control the files.
    # For example, if the FileDataDirMixin object is accessed via
    # self.foo.bar, set this to ["foo", "bar"].
    _master_class_path = None

    # This should be set to a dict.  Each key becomes an attribute
    # of the class, and each value a tuple containing the data type
    # or class for this attribute and its default value.  So, for 
    # example, to have a string attribute named "foo" with a blank
    # default, you set this key-value pair:
    #   "foo": (str, "")
    # which then can be accessed via self.foo.
    _file_fields = None

    # These are calculated based on a number of things, including
    # the _master_class_path setting above.
    _master_class = None
    _file_path = None
    _file_name = None

    def set_master_class(self):
        if not self._master_class:
            o = self
            for p in self._master_class_path:
                o = getattr(o, p)
            self._master_class = o

            if not self._master_class.setup_directory():
                raise FileDataMixinCreateError()

    def set_data_path(self):
        if not self._file_path:
            self.set_master_class()
            self._file_path = self._master_class.file_path()

    def set_data_fn(self):
        if not self._file_name:
            fn_base = self.__class__.__name__ + "_%d.pickle"
            filenum = 1
            fn = fn_base % filenum
            while os.path.exists(os.path.join(self._file_path, fn)):
                filenum = filenum + 1
                fn = fn_base % filenum
            self._file_name = fn

    def sanitize_init(self, kwargs):
        new_kwargs = kwargs.copy()
        for key in kwargs:
            if key in self._file_fields:
                self.__dict__[key] = new_kwargs[key]
                del new_kwargs[key]
        return new_kwargs

    def load_from_fn(self):
        self.set_data_path()
        self.set_data_fn()

        # Set defaults.
        for field in self._file_fields:
            if field not in self.__dict__:
                self.__dict__[field] = self._file_fields[field][1]

        path = os.path.join(self._file_path, self._file_name)
        if os.path.exists(path):
            f = open(path)
            read_from = pickle.load(f)
            f.close()
            self.__dict__.update(read_from)

    def write_to_fn(self):
        self.set_data_path()
        self.set_data_fn()

        to_write = {}
        for key in self.__dict__:
            if key in self._file_fields:
                to_write[key] = self.__dict__[key]

        if not os.path.exists(self._file_path):
            os.makedirs(self._file_path)
        path = os.path.join(self._file_path, self._file_name)
        f = open(path, "w")
        pickle.dump(to_write, f)
        f.close()

# This mixin class actually manages the files being created by the
# FileDataMixin class.  Whichever model ends up being the "master"
# model should derive from this.  It handles the details of setting up
# the directory and the version control repository, and also handled
# commits and history.
class FileDataDirMixin:
    _subdirs = None

    def file_path(self):
        return os.path.join(settings.USERDATA_ROOT, str(self.id))

    def setup_directory(self):
        file_path = self.file_path()
        if not os.path.isdir(file_path):
            try:
                os.makedirs(file_path)
                if self._subdirs:
                    for subdir in self._subdirs:
                        os.mkdir(os.path.join(file_path, subdir))
            except OSError:
                if os.path.exists(file_path):
                    shutil.rmtree(file_path)
                return False
        return True

    def remove_directory(self):
        shutil.rmtree(self.file_path())

    def new_file_from_existing(self, orig_path, subdir=None):
        if subdir:
            dest_path = os.path.join(self.file_path(), subdir)
        else:
            dest_path = self.file_path()
        shutil.copy(orig_path, dest_path)

    def commit(self):
        pass

class Product_Record(models.Model, FileDataDirMixin):
    _subdirs = ["spdx_files", "patches"]

    company = models.CharField('Company Name', max_length=200)
    product = models.CharField('Product Name', max_length=200)
    version = models.CharField('Product Version', max_length=20)
    release = models.CharField('Product Release', max_length=20)
    checksum = models.CharField('Checksum', max_length=200, blank=True)
    website = models.CharField('Company Website', max_length=200)
    record_date = models.DateTimeField('Test Date', auto_now=True)
    contact = models.CharField('Compliance Contact Name (optional)', max_length=200, blank=True)
    email = models.CharField('Compliance Contact Email', max_length=200)

    def __unicode__(self):
        return self.product

class FOSS_Components(models.Model, FileDataMixin):
    _master_class_path = ["brecord"]
    _file_fields = {
        "package": (str, ""),
        "version": (str, ""),
        "copyright": (str, ""),
        "attribution": (str, ""),
        "license": (str, ""),
        "license_url": (str, ""),
        "url": (str, ""),
        "spdx_file": (str, "")
    }

    brecord = models.ForeignKey(Product_Record)
    data_file_name = models.CharField(max_length=100, blank=True)

    def __init__(self, *args, **kwargs):
        sanitized_kwargs = self.sanitize_init(kwargs)
        super(FOSS_Components, self).__init__(*args, **sanitized_kwargs)
        if self.data_file_name:
            self._file_name = self.data_file_name
        self.load_from_fn()
        if not self.data_file_name:
            self.data_file_name = self._file_name

    def __unicode__(self):
        return self.package

    def save(self, *args, **kwargs):
        super(FOSS_Components, self).save(*args, **kwargs)
        self.write_to_fn()

class Patch_Files(models.Model):
    frecord = models.ForeignKey(FOSS_Components)
    path = models.CharField(max_length=400)
    def __unicode__(self):
        return self.path

class System_Settings(models.Model):
    name = models.CharField(max_length=32, db_index=True)
    ftype = models.CharField(max_length=1, default='t', choices=(('b', 'bool'), ('t', 'text')))
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


