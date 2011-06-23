# Database settings.  These have been moved out of the normal Django
# settings file so they can be changed on their own without
# interfering with other configuration settings.

# Imports.

import os
from setutils import get_project_root

# By default, this web application uses a simple SQLite database, with
# the data file located in the installation directory.  This is
# probably suitable when used by a single user, or when shared within
# a small company or project team.

DATABASES = {
    'default': {
        'NAME': os.path.join(get_project_root(), 'fossbarcode',
                             'barcode.sqlite'),
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

# For more demanding use, we recommend switching to a more traditional
# database server.  The tool can be set up to use any database server
# supported by Django; as of Django 1.3, that includes MySQL 4.1 or
# later, PostgreSQL 8.2 or later, and Oracle 9i or later.  Uncomment
# the section below corresponding to your choice, comment out the
# above SQLite section, and fill in the appropriate configuration
# entries for the database server in question.

# For MySQL, make sure you have MySQLdb 1.2.1p2 or later installed.
# Django recommends using the InnoDB engine, though MyISAM is also
# supported.

# DATABASES = {
#     'default': {
#         'NAME': 'fossbarcode',
#         'ENGINE': 'django.db.backends.mysql',
#         'HOST': '',            # Host name of MySQL server.
#         'PORT': '',            # Port to use for MySQL server.
#                                # Leave blank to use the default port.
#         'USER': '',            # MySQL user name
#         'PASSWORD': '',        # Password for MySQL user
#     }
# }

# There are two possible backends for PostgreSQL: one for the
# "traditional" PostgreSQL Python driver, and one for psycopg.  We
# recommend using the psycopg driver, as it is the most popular.

# DATABASES = {
#     'default': {
#         'NAME': 'fossbarcode',
#         'ENGINE': 'django.db.backends.postgresql_psycopg',
#         'HOST': '',            # Host name of PostgreSQL server.
#         'PORT': '',            # Port to use for PostgreSQL server.
#                                # Leave blank to use the default port.
#         'USER': '',            # PostgreSQL user name
#         'PASSWORD': '',        # Password for PostgreSQL user
#     }
# }

# Use of Oracle requires the cx_Oracle Python driver, version 4.3.1 or
# later.  Note that cx_Oracle 5.0 should *not* be used, due to a bug;
# 5.0.1 or greater is OK.

# The NAME parameter should identify a TNS entry.  Specify the user
# and password separately, rather than via a user/pass@dsn string.

# DATABASES = {
#     'default': {
#         'NAME': 'fossbarcode',
#         'ENGINE': 'django.db.backends.oracle',
#         'USER': '',            # Oracle user name
#         'PASSWORD': '',        # Password for Oracle user
#     }
# }
