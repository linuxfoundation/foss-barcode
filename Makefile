# Top-level Makefile for foss-barcode.
# Copyright 2010 The Linux Foundation.  See LICENSE file for licensing.

NAME = foss-barcode
DESTDIR ?=
BASEDIR ?= /opt/linuxfoundation
ifndef BUILD_FOR_RPM
INSTALL = install -o compliance -g compliance
else
INSTALL = install
endif
ISREQ = is required for this application, please install either with your package manager or from source before proceeding. See 00README or README.txt for source locations.

default: checkreq fossbarcode/barcode.sqlite fossbarcode/media/docs/index.html README.txt

checkreq:
ifndef BUILD_FOR_RPM
	# check for needed binaries
	@for binary in python barcode qrencode pstopnm pnmtopng sam2p; do \
		type $$binary > /dev/null 2>&1; \
		if [ $$? -ne 0 ]; then \
			echo "$$binary $(ISREQ)"; \
			exit 1; \
		fi; \
	done;
	# check for needed python support
	@python -c 'from django.core.management import execute_manager' > /dev/null 2>&1; \
	if [ $$? -ne 0 ]; then \
		echo "Django support in python $(ISREQ)"; \
		exit 1; \
	fi;	
	@python -c 'from dulwich.repo import Repo' > /dev/null 2>&1; \
	if [ $$? -ne 0 ]; then \
		echo "Dulwich support in python $(ISREQ)"; \
		exit 1; \
	fi;	
endif

install: default
ifndef BUILD_FOR_RPM
	# create compliance account
	groupadd compliance
	id compliance >/dev/null 2>&1; \
	if [ $$? -ne 0 ]; then \
	useradd -d /home/compliance -s /bin/sh -p "" -c "compliance tester login" compliance -m -g compliance; \
	fi;	
endif

	$(INSTALL) -d $(DESTDIR)$(BASEDIR)
	$(INSTALL) -d $(DESTDIR)$(BASEDIR)/bin
	$(INSTALL) -m 755 foss-barcode.py $(DESTDIR)$(BASEDIR)/bin
	cp -ar fossbarcode $(DESTDIR)$(BASEDIR)
ifndef BUILD_FOR_RPM
	chown -R compliance.compliance $(DESTDIR)$(BASEDIR)
endif
	find $(DESTDIR)$(BASEDIR) -name '*.pyc' | xargs rm -f
	$(INSTALL) -m 644 fossbarcode/media/docs/*.html $(DESTDIR)$(BASEDIR)/fossbarcode/media/docs
	$(INSTALL) -d $(DESTDIR)$(BASEDIR)/share/icons/hicolor/16x16/apps
	$(INSTALL) -m 644 desktop/lf_small.png $(DESTDIR)$(BASEDIR)/share/icons/hicolor/16x16/apps
	$(INSTALL) -d $(DESTDIR)$(BASEDIR)/share/applications
	$(INSTALL) -m 644 desktop/$(NAME).desktop $(DESTDIR)$(BASEDIR)/share/applications
	$(INSTALL) -d $(DESTDIR)$(BASEDIR)/doc/$(NAME)
	$(INSTALL) -m 644 doc/LICENSE doc/Contributing $(DESTDIR)$(BASEDIR)/doc/$(NAME)
	$(INSTALL) -m 644 AUTHORS Changelog README.txt README.apache-mod_wsgi $(DESTDIR)$(BASEDIR)/doc/$(NAME)
	$(INSTALL) -d $(DESTDIR)/var$(BASEDIR)/log/fossbarcode

	# install the init script
	install -d $(DESTDIR)/etc/init.d
	install -d $(DESTDIR)/etc/sysconfig
	sed -i "s|###BASEDIR###|$(BASEDIR)|g" fossbarcode/scripts/fossbarcode
	install -m 755 fossbarcode/scripts/fossbarcode $(DESTDIR)/etc/init.d
	install -m 644 fossbarcode/etc/sysconfig/fossbarcode $(DESTDIR)/etc/sysconfig

ifndef BUILD_FOR_RPM
	# make the menu entry visible
	-xdg-desktop-menu install $(DESTDIR)$(BASEDIR)/share/applications/$(NAME).desktop
endif

uninstall:
	-rm -fr $(DESTDIR)$(BASEDIR)/$(NAME)
	-rm -fr $(DESTDIR)$(BASEDIR)/bin/foss-barcode.py
	-rm -fr $(DESTDIR)$(BASEDIR)/doc/$(NAME)
	-xdg-desktop-menu uninstall $(DESTDIR)$(BASEDIR)/share/applications/$(NAME).desktop
	-rm -fr $(DESTDIR)$(BASEDIR)/share/applications/$(NAME).desktop
	-rm -fr 
	-rm -fr /etc/init.d/fossbarcode
	-rm -fr /etc/sysconfig/fossbarcode
	-rm -fr /var$(DESTDIR)$(BASEDIR)/log/fossbarcode
	id compliance >/dev/null 2>&1; \
	if [ $$? -eq 0 ]; then \
	userdel compliance; \
	fi;
	grep -q '^compliance:' /etc/group; \
	if [ $$? -eq 0 ]; then \
	groupdel compliance; \
	fi;	

package:
	cd package && $(MAKE)

fossbarcode/barcode.sqlite: fossbarcode/barcode/models.py fossbarcode/barcode/fixtures/initial_data.xml
	rm -f fossbarcode/barcode.sqlite
	cd fossbarcode && python manage.py syncdb --noinput
	touch fossbarcode/barcode.sqlite

fixture_regen:
	(cd fossbarcode && python manage.py dumpdata --format xml barcode auth.user) | \
	  xmllint --format - > fossbarcode/barcode/fixtures/initial_data.xml

fossbarcode/media/docs/index.html:
	cd fossbarcode/media/docs && $(MAKE)

README.txt: fossbarcode/media/docs/index.html
	w3m -dump $< > $@

test:
	cd fossbarcode && python manage.py test

clean:
	cd package && $(MAKE) clean
	cd fossbarcode/media/docs && $(MAKE) clean
	rm -fr fossbarcode/media/user_data/*
	rm -f README.txt
	rm -f fossbarcode/barcode.sqlite

.PHONY: default clean package fixture_regen test checkreq install uninstall
