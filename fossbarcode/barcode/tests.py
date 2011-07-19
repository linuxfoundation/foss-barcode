import os
import shutil
from django.conf import settings
from django.test import TestCase
from fossbarcode.barcode.models import *

class BarCodeHarness(TestCase):
    def setUp(self):
        if os.path.exists(settings.USERDATA_ROOT):
            shutil.rmtree(settings.USERDATA_ROOT)

        # File to copy around for testing.
        self.source_path = os.path.join(settings.STATE_ROOT, 
                                        "media/css/barstyle.css")

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
        self.product.commit("Add test component.")

    def tearDown(self):
        if os.path.exists(settings.USERDATA_ROOT):
            shutil.rmtree(settings.USERDATA_ROOT)

    def testBarCodeHarnessSetup(self):
        self.assertFalse(os.path.exists(settings.USERDATA_ROOT))
        self.assertIsNotNone(self.product)
        self.assertEqual(self.product.company, "Test Company")
        self.assertTrue(os.path.exists(self.source_path))

        self.addComponent()
        self.assertIsNotNone(self.component)
        self.assertEqual(self.component.license, "Test License 1.0")

class TestFileDataDirMixin(BarCodeHarness):
    def testSetupDirectoryNew(self):
        product_path = os.path.join(settings.USERDATA_ROOT,
                                    str(self.product.id))
        self.assertFalse(os.path.exists(product_path))
        self.product.setup_directory()
        self.assertTrue(os.path.exists(product_path))
        for subdir in [".git", "spdx_files", "patches"]:
            self.assertTrue(os.path.exists(os.path.join(product_path, subdir)))

        repo = self.product.get_repo()
        self.assertIsNotNone(repo)

    def testCommit(self):
        self.addComponent()

        self.component.license = "Test License 2.0"
        self.component.save()
        self.product.commit("Change component license.")

        repo = self.product.get_repo()
        self.assertEqual(len(repo.revision_history(repo.head())), 2)

    def testMultipleCommits(self):
        self.addComponent()
        self.component.license = "Test License 2.0"
        self.component.save()
        self.product.commit("First change to component license.")
        self.component.license = "Test License 3.0"
        self.component.save()
        self.product.commit("Second change to component license.")

        repo = self.product.get_repo()
        self.assertEqual(len(repo.revision_history(repo.head())), 3)

        self.assertTrue(False, "not done with this test yet")

    def testNewFileFromExisting(self):
        dest_path = os.path.join(self.product.file_path(),
                                 "patches/barstyle.css")
        self.assertFalse(os.path.exists(dest_path))

        self.product.setup_directory()
        self.product.new_file_from_existing(self.source_path, "patches")
        self.assertTrue(os.path.exists(dest_path))

        self.assertTrue(self.product.commit("Test commit."))
        repo = self.product.get_repo()
        self.assertEqual(len(repo.revision_history(repo.head())), 1)

        commit = repo.commit(repo.head())
        tree = repo.tree(commit.tree)
        self.assertTrue("patches" in tree)
        subtree = repo.tree(tree["patches"][1])
        self.assertTrue("barstyle.css" in subtree)

    def testDelete(self):
        dest_path = os.path.join(self.product.file_path(),
                                 "patches/barstyle.css")
        self.product.setup_directory()
        self.product.new_file_from_existing(self.source_path, "patches")
        self.assertTrue(self.product.commit("Adding file for test."))
        repo = self.product.get_repo()
        prev_commit = repo.commit(repo.head())
        prev_tree = repo.tree(prev_commit.tree)
        self.assertTrue("patches" in prev_tree)
        self.assertTrue("barstyle.css" in repo.tree(prev_tree["patches"][1]))

        self.product.delete_file("patches/barstyle.css")
        self.assertTrue(self.product.commit("Test removing file."))
        current_commit = repo.commit(repo.head())

        self.assertEqual(current_commit.message, "Test removing file.")
        current_tree = repo.tree(current_commit.tree)
        self.assertFalse(os.path.exists(dest_path))
        self.assertFalse("patches" in current_tree)

    def testRemoveDirectory(self):
        self.assertFalse(os.path.exists(self.product.file_path()))
        self.product.setup_directory()
        self.product.new_file_from_existing(self.source_path, "patches")
        self.assertTrue(os.path.exists(self.product.file_path()))
        self.assertTrue(self.product.commit("Test commit."))
        repo = self.product.get_repo()
        self.assertEqual(len(repo.revision_history(repo.head())), 1)

        self.product.remove_directory()
        self.assertFalse(os.path.exists(self.product.file_path()))

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

    def testLoadObjectRevision(self):
        self.addComponent()
        self.component.license = "Test License 2.0"
        self.component.save()
        self.product.commit("Change component license.")

        repo = self.product.get_repo()
        commit_id = repo.revision_history(repo.head())[-1]
        old_component = FOSS_Components.objects.get(id=self.component.id,
                                                    revision=commit_id)
        self.assertEqual(old_component.id, self.component.id)
        self.assertEqual(old_component.license, "Test License 1.0")

class TestProductRecord(BarCodeHarness):
    def testChecksum(self):
        self.assertEqual(self.product.calc_checksum(),
                         "ef7fb81294c22856d9593d44f489cdd3")

    def testBarcode(self):
        self.product.setup_directory()
        self.product.checksum = self.product.calc_checksum()
        self.product.codetype = '128'
        self.product.save()
        partial_path = os.path.join(self.product.file_path(),
                                    self.product.checksum)

        self.product.checksum_to_barcode()
        self.assertTrue(os.path.exists(partial_path + ".ps"))
        self.assertTrue(os.path.exists(partial_path + ".png"))

    def testDetailedQRCode(self):
        self.product.setup_directory()
        self.product.checksum = self.product.calc_checksum()
        self.product.save()
        partial_path = os.path.join(self.product.file_path(),
                                    self.product.checksum)

        self.product.checksum_to_barcode()
        self.assertTrue(os.path.exists(partial_path + ".ps"))
        self.assertTrue(os.path.exists(partial_path + ".png"))

class TestFOSSComponents(BarCodeHarness):
    def testDelete(self):
        self.addComponent()
        component_fn = self.component.data_file_name
        self.assertTrue(os.path.exists(os.path.join(self.product.file_path(),
                                                    component_fn)))

        self.component.delete()
        self.assertTrue(self.product.commit("Remove component."))

        self.assertFalse(os.path.exists(os.path.join(self.product.file_path(),
                                                     component_fn)))
