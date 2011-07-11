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
    pass
