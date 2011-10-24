import os
import shutil
import re
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
        component_license = License.objects.filter(license="GPL", version="3.0")[0]
        self.component = FOSS_Components(brecord=self.product,
                                         component="Open Source Test",
                                         version="3.0",
                                         copyright="Copyright 2010 Test Foundation",
                                         attribution="",
                                         license_id=component_license.id,
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
        self.assertEqual(self.component.brecord, self.product)
        self.assertEqual(str(self.component.license), "GPL 3.0")

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

        self.component.attribution = "Some people somewhere."
        self.component.save()
        self.product.commit("Change attribution.")

        repo = self.product.get_repo()
        self.assertEqual(len(repo.revision_history(repo.head())), 2)

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

    def testDeleteFile(self):
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

    def testGetFileContent(self):
        self.product.setup_directory()
        f = open(os.path.join(self.product.file_path(), "test"), "w")
        f.write("test content\n")
        f.close()
        self.product.register_new_file("test")
        self.assertTrue(self.product.commit("Adding test file."))

        self.assertEquals("test content\n",
                          self.product.get_file_content("test"))

    def testHistory(self):
        self.addComponent()
        history = [x for x in self.product.iter_history()]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0][2], "Add test component.")

class TestFileDataMixin(BarCodeHarness):
    def testNewObject(self):
        self.addComponent()
        data_file_path = os.path.join(self.product.file_path(), 
                                      "FOSS_Components_%d.pickle" % self.component.id)
        self.assertTrue(os.path.exists(data_file_path))

class TestProductRecord(BarCodeHarness):
    def testChecksum(self):
        self.assertEqual(self.product.calc_checksum(),
                         "ef7fb81294c22856d9593d44f489cdd3")

    def testMeCardPlus(self):
        test_strings = ["N:Test Company;",
                        "(Open Source Test 3.0 GPL 3.0),",
                        "(Open Source Library 1.0 GPL 3.0);"]
        self.addComponent()
        second_component = FOSS_Components(brecord=self.product,
                                           component="Open Source Library",
                                           version="1.0",
                                           copyright="Copyright 2010 Test Foundation",
                                           attribution="",
                                           license_id=self.component.license.id,
                                           license_url="http://testlib.example.com/license.html",
                                           url="http://testlib.example.com/")
        second_component.save()
        self.assertTrue(self.product.commit("Add second component."))
        mecard = self.product.record_to_mecard("qr+")
        for s in test_strings:
            self.assertTrue(s in mecard,
                            "could not find string '%s' in me card '%s'" % (s, mecard))

    def testBarcode(self):
        path_suffixes = ["-128.ps", "-128.png", "-qr.ps", "-qr.png",
                         "-qr+.ps", "-qr+.png"]
        self.product.setup_directory()
        self.product.checksum = self.product.calc_checksum()
        self.product.save()
        partial_path = os.path.join(self.product.file_path(),
                                    self.product.checksum)

        self.product.checksum_to_barcode()
        self.assertTrue(self.product.commit("Add barcodes."))

        for suffix in path_suffixes:
            self.assertTrue(os.path.exists(partial_path + suffix))

        repo = self.product.get_repo()
        tree = repo.tree(repo.commit(repo.head()).tree)
        for suffix in path_suffixes:
            self.assertTrue((self.product.checksum + suffix) in tree)

    def testClone(self):
        self.addComponent()
        self.product.checksum_to_barcode()
        self.assertTrue(self.product.commit("Add QR code."))

        clone_product = self.product.clone(release="2")

        self.assertIsNotNone(clone_product)
        self.assertEqual(Product_Record.objects.all().count(), 2)
        self.assertEqual(clone_product.company, self.product.company)
        self.assertEqual(clone_product.product, self.product.product)
        self.assertEqual(clone_product.version, self.product.version)
        self.assertNotEqual(clone_product.release, self.product.release)
        self.assertEqual(clone_product.foss_components_set.count(),
                         self.product.foss_components_set.count())

        clone_component = clone_product.foss_components_set.all()[0]
        self.assertEqual(clone_component.component, self.component.component)

        old_repo = self.product.get_repo()
        clone_repo = clone_product.get_repo()
        self.assertEqual(len(clone_repo.revision_history(clone_repo.head())),
                         len(old_repo.revision_history(old_repo.head())) + 1)

    def testNoExactClone(self):
        clone_failed = False
        try:
            self.product.clone(release=self.product.release)
        except ValueError:
            clone_failed = True
        self.assertTrue(clone_failed)

    def testChecksumHistory(self):
        # FIXME: fixing this bug has been put off for now.
        return

        self.addComponent()
        repo = self.product.get_repo()
        starting_history = len(repo.revision_history(repo.head()))

        self.product.checksum_to_barcode()
        self.assertTrue(self.product.commit('Calculated barcode.'))
        old_checksum = self.product.checksum
        old_revision = self.product.get_repo().head()

        self.product.company = "Testing Industries"
        self.product.save()
        self.product.checksum = self.product.calc_checksum()
        self.product.checksum_to_barcode()
        self.assertTrue(self.product.commit('Changed company name and re-calc barcode.'))

        self.assertNotEqual(old_checksum, self.product.checksum)

        self.product.switch_revision(old_revision)
        self.assertEqual(old_checksum, self.product.checksum)

    def testDelete(self):
        self.addComponent()
        product_id = self.product.id
        product_file_path = self.product.file_path()
        self.assertTrue(os.path.exists(product_file_path))
        self.assertTrue(os.path.exists(
                os.path.join(product_file_path,
                             self.component.data_file_name)))

        self.product.delete()

        not_found = False
        try:
            Product_Record.objects.get(id=product_id)
        except Product_Record.DoesNotExist:
            not_found = True
        self.assertTrue(not_found)

        self.assertFalse(os.path.exists(product_file_path))

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

    def testLoadObject(self):
        self.addComponent()
        self.assertEqual(self.component.brecord, self.product)

        loaded_component = FOSS_Components.objects.get(id=self.component.id)

        self.assertEqual(loaded_component.id, self.component.id)
        self.assertEqual(loaded_component.brecord.id, self.component.brecord.id)
        self.assertEqual(loaded_component.component, self.component.component)
        self.assertEqual(loaded_component.license, self.component.license)
        self.assertEqual(loaded_component.url, self.component.url)

    def testLoadObjectRevision(self):
        self.addComponent()
        commit_id = self.product.get_repo().head()
        self.component.attribution = "Some people somewhere."
        self.component.save()
        self.product.commit("Change attribution.")

        old_component = FOSS_Components.objects.get(id=self.component.id)
        old_component.switch_revision(commit_id)
        self.assertEqual(old_component.id, self.component.id)
        self.assertEqual(old_component.attribution, "")

    def testReadOnly(self):
        self.addComponent()
        commit_id = self.product.get_repo().head()
        self.component.attribution = "Some people somewhere."
        self.component.save()
        self.product.commit("Change attribution.")
        old_component = FOSS_Components.objects.get(id=self.component.id)
        old_component.switch_revision(commit_id)

        old_component.license = "More people elsewhere."
        write_failed = False
        try:
            old_component.save()
        except ReadOnlyError:
            write_failed = True
        self.assertTrue(write_failed)

class TestLicense(BarCodeHarness):
    def testFixtures(self):
        self.assertTrue(License.objects.all().count() > 0)
        self.assertTrue(LicenseAlias.objects.all().count() > 0)
