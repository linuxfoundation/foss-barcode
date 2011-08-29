from django.conf import settings
from django.db import models
from django.forms import ModelForm, forms, Form
from django import forms
import os
import re
import shutil
import pickle
import time
import hashlib
import subprocess
from dulwich.repo import Repo
from dulwich.objects import parse_timezone

# Custom exceptions.
class FileDataMixinCreateError(StandardError):
    pass

class ReadOnlyError(StandardError):
    pass

# Utility functions.

# strip 'pk' entry from serialized data
def strip_pk(data):
    data = re.sub('pk=".*?" ','', data)
    return data

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

    def load_from_fn(self, revision=None):
        self.set_data_path()
        self.set_data_fn()

        # Set defaults.
        for field in self._file_fields:
            if field not in self.__dict__:
                self.__dict__[field] = self._file_fields[field][1]


        try:
            record_data = self.brecord.get_file_content(self._file_name,
                                                        revision)
            if record_data:
                read_from = pickle.loads(record_data)
                self.__dict__.update(read_from)
        except KeyError:
            pass

    def write_to_fn(self):
        self.set_master_class()
        self.set_data_path()
        self.set_data_fn()

        to_write = {}
        for key in self.__dict__:
            if key in self._file_fields:
                to_write[key] = self.__dict__[key]

        path = os.path.join(self._file_path, self._file_name)
        file_exists = os.path.exists(path)
        f = open(path, "w")
        pickle.dump(to_write, f)
        f.close()
        if file_exists:
            self._master_class.register_modified_file(self._file_name)
        else:
            self._master_class.register_new_file(self._file_name)

# This mixin class actually manages the files being created by the
# FileDataMixin class.  Whichever model ends up being the "master"
# model should derive from this.  It handles the details of setting up
# the directory and the version control repository, and also handled
# commits and history.
class FileDataDirMixin:
    _subdirs = None
    current_changes = []

    def file_path(self):
        return os.path.join(settings.USERDATA_ROOT, str(self.id))

    def get_repo(self):
        return Repo(self.file_path())

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

            repo = Repo.init(file_path)

        return True

    def remove_directory(self):
        shutil.rmtree(self.file_path())

    def _add_blob_from_file(self, subpath):
        self.current_changes.append(subpath)

    def new_file_from_existing(self, orig_path, subdir=None):
        if subdir:
            dest_path = os.path.join(self.file_path(), subdir)
            dest_subpath = os.path.join(subdir, os.path.basename(orig_path))
        else:
            dest_path = self.file_path()
            dest_subpath = os.path.basename(orig_path)
        shutil.copy(orig_path, dest_path)

        self._add_blob_from_file(dest_subpath)

    def register_new_file(self, subpath):
        self._add_blob_from_file(subpath)

    def register_modified_file(self, subpath):
        self._add_blob_from_file(subpath)

    def delete_file(self, subpath):
        os.unlink(os.path.join(self.file_path(), subpath))
        self.current_changes.append(subpath)

    def iter_history(self):
        repo = self.get_repo()
        for commit in repo.revision_history(repo.head()):
            yield (commit.id, commit.commit_time, commit.message)

    def get_file_content(self, subpath, revision=None):
        if revision:
            repo = self.get_repo()

            traverse = repo.commit(revision).tree
            for path_component in os.path.split(subpath):
                if path_component:
                    traverse = repo.tree(traverse)[path_component][1]
            return repo.get_blob(traverse).data
        else:
            data_full_path = os.path.join(self.file_path(), subpath)
            if os.path.exists(data_full_path):
                data_file = open(data_full_path)
                return data_file.read()
            else:
                return ""

    def commit(self, commit_msg):
        if not self.current_changes:
            return False

        # FIXME: get real values for these.
        author = "FOSS Barcode <foss-barcode@linuxfoundation.org>"
        tz = parse_timezone('-0400')[0]

        repo = self.get_repo()
        repo.stage([str(x) for x in self.current_changes])
        commit_id = repo.do_commit(commit_msg, committer=author,
                                   commit_timezone=tz)

        self.current_changes = []
        return True

class Product_Record(models.Model, FileDataDirMixin):
    _subdirs = ["spdx_files", "patches"]

    company = models.CharField('Company Name', max_length=200)
    product = models.CharField('Product Name', max_length=200)
    version = models.CharField('Product Version', max_length=20)
    release = models.CharField('Product Release', max_length=20)
    checksum = models.CharField('Checksum', max_length=200, blank=True)
    website = models.CharField('Company Website', max_length=200)
    record_date = models.DateTimeField('Last Updated', auto_now=True)
    contact = models.CharField('Compliance Contact Name (optional)', max_length=200, blank=True)
    email = models.CharField('Compliance Contact Email', max_length=200)
    spdx_file = models.CharField('SPDX<sup>TM</sup> File', max_length=200, blank=True)
    # for future fine tuning of how things can be changed
    released = models.BooleanField('Released to Production', default=False)

    def __unicode__(self):
        return self.product

    def clone(self, company=None, product=None, version=None, release=None, website=None, contact=None, email=None, spdx_file=None):
        # Create a clone of this product, including the same components,
        # patches, etc.  Must provide at least one different value for
        # company, product, version, or release.  Returns the new product.
        if not company:
            company = self.company
        if not product:
            product = self.product
        if not version:
            version = self.version
        if not release:
            release = self.release
        if not website:
            website = self.website
        if not contact:
            contact = self.contact
        if not email:
            email = self.email
        if not spdx_file:
            spdx_file = self.spdx_file

        if company == self.company and product == self.product and \
                version == self.version and release == self.release:
            raise ValueError, "cannot make an identical clone of a product"

        new_product = Product_Record(company=company, product=product,
                                     version=version, release=release,
                                     website=website,
                                     contact=contact, email=email, 
                                     spdx_file=spdx_file)
        new_product.save()

        shutil.copytree(self.file_path(), new_product.file_path(), ignore=shutil.ignore_patterns('*.png', '*.ps'))

        for component in self.foss_components_set.all():
            new_component = FOSS_Components(brecord=new_product,
                                            data_file_name=component.data_file_name)
            new_component.save()

        if self.checksum:
            new_product.checksum = new_product.calc_checksum()
            new_product.save()
            new_product.checksum_to_barcode()
            new_product.commit("Create new barcode after clone from record %d." % self.id)

        return new_product

    def calc_checksum(self):
        # create an xml file of the database data
        # FIXME - do we even need an xml dataset now with just these 4 fields?
        from django.core import serializers
        data = strip_pk(serializers.serialize("xml", [self], 
                                              fields=('company', 'product', 'version', 'release')))
    
        m = hashlib.md5()
        m.update(data)
        checksum = m.hexdigest()

        # and return
        return checksum

    # create eps and png files from a checksum
    def checksum_to_barcode(self):
        import Image

        if not self.checksum:
            self.checksum = self.calc_checksum()
            self.save()

        # FIXME - this is all in a state of flux, make them all, make some?
        # latest call is to make qr+ and 128 always, show the one selected in sysconfig
        # doing qr also, since the config end is all setup
        file_path = self.file_path()
        base_filename = self.checksum + "-"
        foss_file = os.path.join(settings.STATIC_DOC_ROOT, "images/foss.png")
        gen_types = [ "128", "qr", "qr+" ]
 
        for t in gen_types:
            ps_filename = base_filename + t + ".ps"
            ps_file = os.path.join(file_path, ps_filename)
            png_filename = base_filename + t + ".png"
            png_file = os.path.join(file_path, png_filename)

            if t == "128":
                result = os.system("barcode -b " + self.checksum + " -e 128 -m '0,0' -E > " + ps_file)
            else:
                # mecard data will either be basic (just the product url), or enhanced
                mecard = self.record_to_mecard(t)

                qrencode_pipe = \
                    subprocess.Popen("qrencode -v 6 -l Q -m 0 -o " + png_file,
                                     shell=True, stdin=subprocess.PIPE)
                qrencode_pipe.stdin.write(mecard)
                qrencode_pipe.stdin.close()
                result = qrencode_pipe.wait()
                if result == 0:
                    # overlay the foss.png image for branding
                    qrcode = Image.open(png_file)
                    overlay = Image.open(foss_file)

                    (xdim,ydim) = qrcode.size

                    qrcode.paste(overlay,((xdim-1)/2-28,(ydim-1)/2-13))
                    qrcode.save(png_file,"PNG")

            if result == 0:
                # image conversion tries to use root's settings, if started as root
                os.putenv('TMP', '/tmp')
                os.putenv('TMPDIR', '/tmp')
                if t == "128":
                    result = os.system("pstopnm -xsize 500 -portrait -stdout " + ps_file + " 2>/dev/null | pnmtopng 2>/dev/null > " + png_file)
                else:
                    result = os.system("sam2p -j:quiet " + png_file + " PS: " + ps_file)

            for fn in [ps_filename, png_filename]:
                if os.path.exists(os.path.join(file_path, fn)):
                    self.register_new_file(fn)

        return result

    # convert a record to a MECARD string
    # see http://www.nttdocomo.co.jp/english/service/imode/make/content/barcode/function/application/addressbook/
    def record_to_mecard(self, metype):
        mecard = 'MECARD:'
        settings_list = System_Settings.objects.all()
        for s in settings_list:
            if s.name == "host_site":
                host_site = s.value
            if s.name == "host_site_in_qrcode":
                host_site_in_qrcode = s.value

        if metype == "qr+":
            mecard += "N:" + self.company + ";URL:" + self.website + ";EMAIL:" + self.email
            mecard += ";NOTE:" + self.product + ", Version: " + self.version + ", Release: " + self.release
            mecard += ", Updated: " + self.record_date.strftime('%Y-%m-%d')
            # FOSS BoM
            has_foss = FOSS_Components.objects.filter(brecord = self).count()
            if has_foss:
                mecard += ", BoM: "
                foss_list = FOSS_Components.objects.filter(brecord = self)
                for f in foss_list:
                    mecard += "(" + f.package + " " + f.version + " " + f.license + "), "
                mecard = mecard[:-2] + ";"

        # url to central site
        if host_site_in_qrcode == "True" or metype == "qr":
            mecard += "URL:" + host_site + self.checksum + ";"

        return mecard

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
        "spdx_file": (str, ""),
        "patch_files": (list, [])
    }
    _read_only = False

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

    def switch_revision(self, revision):
        if revision == None:
            repo = self.brecord.get_repo()
            revision = repo.head()
            self._read_only = False
        else:
            self._read_only = True
        self.load_from_fn(revision)

    def save(self, *args, **kwargs):
        if self._read_only:
            raise ReadOnlyError, "cannot modify object not on HEAD revision"
        super(FOSS_Components, self).save(*args, **kwargs)
        self.write_to_fn()

    def delete(self, *args, **kwargs):
        if self.data_file_name:
            self.brecord.delete_file(self.data_file_name)
        super(FOSS_Components, self).delete(*args, **kwargs)

class System_Settings(models.Model):
    name = models.CharField(max_length=32, db_index=True)
    ftype = models.CharField(max_length=1, default='t', choices=(('b', 'boolean'), ('t', 'text'), ('c', 'choices')))
    value = models.CharField(max_length=128)
    descr = models.CharField(max_length=256)
    last_updated = models.DateTimeField('Updated', auto_now=True)
    user_updated = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s = %s" % (self.name, self.value)

class RecordForm(ModelForm):   
    class Meta:
        model = Product_Record

    foss_component = forms.CharField(label="Component", max_length=200, required=False)
    foss_version = forms.CharField(label="Version", max_length=20, required=False)
    foss_copyright = forms.CharField(label="Copyright Information", max_length=100, required=False)
    foss_attribution = forms.CharField(label="License Attribution", max_length=100, required=False)
    foss_license = forms.CharField(label="License Name and Version", max_length=40, required=False)
    foss_license_url = forms.CharField(label="License URL", max_length=200, required=False)
    foss_url = forms.CharField(label="Download URL", max_length=200, required=False)
    foss_spdx = forms.CharField(label="SPDX<sup>TM</sup> File", max_length=100, required=False)
    foss_patches = forms.CharField(label="Patches", max_length=200, required=False, widget=forms.Textarea(attrs={'cols': 20, 'rows': 4}))

class HeaderForm(ModelForm):
    class Meta:
        model = Product_Record

    header_commit_message = forms.CharField(label="Change Comments (for change history, required)",
                                            widget=forms.Textarea(attrs={'cols': 80, 'rows': 4}))

class ItemForm(RecordForm):
    class Meta(RecordForm.Meta):
        exclude = ('company', 'product', 'version', 'release', 'checksum', 'website', 'record_date' 'contact', 'email', 'released')

    item_commit_message = forms.CharField(label="Change Comments (for change history, required)",
                                          widget=forms.Textarea(attrs={'cols': 80, 'rows': 4}))

