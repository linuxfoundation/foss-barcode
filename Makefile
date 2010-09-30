# Top-level Makefile for foss-barcode.
# Copyright 2010 The Linux Foundation.  See LICENSE file for licensing.

default: compliance/barcode.sqlite compliance/media/docs/index.html README.txt

package:
	cd package && $(MAKE)

compliance/barcode.sqlite: compliance/barcode/models.py compliance/barcode/fixtures/initial_data.xml
	rm -f compliance/barcode.sqlite
	cd compliance && python manage.py syncdb --noinput

fixture_regen:
	(cd compliance && python manage.py dumpdata --format xml) | \
	  xmllint --format - > compliance/barcode/fixtures/initial_data.xml

compliance/media/docs/index.html:
	cd compliance/media/docs && $(MAKE)

README.txt: compliance/media/docs/index.html
	w3m -dump $< > $@

clean:
	cd package && $(MAKE) clean
	cd compliance/media/docs && $(MAKE) clean
	rm -f README.txt
	rm -f compliance/barcode.sqlite

.PHONY: default clean package fixture_regen
