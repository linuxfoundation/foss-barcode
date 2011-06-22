# Top-level Makefile for foss-barcode.
# Copyright 2010 The Linux Foundation.  See LICENSE file for licensing.

default: fossbarcode/barcode.sqlite fossbarcode/media/docs/index.html README.txt

package:
	cd package && $(MAKE)

fossbarcode/barcode.sqlite: fossbarcode/barcode/models.py fossbarcode/barcode/fixtures/initial_data.xml
	rm -f fossbarcode/barcode.sqlite
	cd fossbarcode && python manage.py syncdb --noinput

fixture_regen:
	(cd fossbarcode && python manage.py dumpdata --format xml) | \
	  xmllint --format - > fossbarcode/barcode/fixtures/initial_data.xml

fossbarcode/media/docs/index.html:
	cd fossbarcode/media/docs && $(MAKE)

README.txt: fossbarcode/media/docs/index.html
	w3m -dump $< > $@

clean:
	cd package && $(MAKE) clean
	cd fossbarcode/media/docs && $(MAKE) clean
	rm -f README.txt
	rm -f fossbarcode/barcode.sqlite

.PHONY: default clean package fixture_regen
