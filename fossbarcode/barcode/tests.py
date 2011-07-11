import os
import shutil
from django.conf import settings
from django.test import TestCase
from fossbarcode.barcode.models import *

class BarCodeHarness(TestCase):
    def setUp(self):
        if os.path.exists(settings.USERDATA_ROOT):
            shutil.rmtree(settings.USERDATA_ROOT)

        self.product = Product_Record(company="Test Company",
                                      product="Test Product",
                                      version="1.0",
                                      release="1",
                                      website="http://testcompany.example.com/",
                                      contact="Joe Tester",
                                      email="joe@testcompany.example.com")
        self.product.save()

    # We add the component as an explicit step, because it will
    # trigger the creation of the data directory prematurely.
    def addComponent(self):
        self.component = FOSS_Components(brecord=self.product,
                                         package="Open Source Test",
                                         version="3.0",
                                         copyright="Copyright 2010 Test Foundation",
                                         attribution="",
                                         license="Test License 1.0",
                                         license_url="http://testprj.example.com/license.html",
                                         url="http://testprj.example.com/")
        self.component.save()

    def tearDown(self):
        if os.path.exists(settings.USERDATA_ROOT):
            shutil.rmtree(settings.USERDATA_ROOT)

    def testBarCodeHarnessSetup(self):
        self.assertFalse(os.path.exists(settings.USERDATA_ROOT))
        self.assertIsNotNone(self.product)
        self.assertEqual(self.product.company, "Test Company")

class TestFileDataDirMixin(BarCodeHarness):
    def testSetupDirectoryNew(self):
        product_path = os.path.join(settings.USERDATA_ROOT,
                                    str(self.product.id))
        self.assertFalse(os.path.exists(product_path))
        self.product.setup_directory()
        self.assertTrue(os.path.exists(product_path))
        for subdir in ["spdx_files", "patches"]:
            self.assertTrue(os.path.exists(os.path.join(product_path, subdir)))

class TestFileDataMixin(BarCodeHarness):
    def testNewObject(self):
        self.addComponent()
        data_file_path = os.path.join(self.product.file_path(), 
                                      "FOSS_Components_%d.pickle" % self.component.id)
        self.assertTrue(os.path.exists(data_file_path))

    def testLoadObject(self):
        self.addComponent()
        self.assertEqual(self.component.brecord, self.product)

        loaded_component = FOSS_Components.objects.get(id=self.component.id)

        self.assertEqual(loaded_component.id, self.component.id)
        self.assertEqual(loaded_component.brecord.id, self.component.brecord.id)
        self.assertEqual(loaded_component.package, self.component.package)
        self.assertEqual(loaded_component.license, self.component.license)
        self.assertEqual(loaded_component.url, self.component.url)
