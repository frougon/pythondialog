#! /usr/bin/env python
# -*- coding: utf-8 -*-

# setup.py --- Setup script for pythondialog
# Copyright (c) 2002, 2003, 2004, 2009, 2010 Florent Rougon
#
# This file is part of pythondialog.
#
# pythondialog is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# pythondialog is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston,
# MA  02110-1301 USA.

import os, sys
from distutils.core import setup


PACKAGE = "pythondialog"
VERSION = "2.10"

def main():
    setup(name=PACKAGE,
          version=VERSION,
          description="A Python interface to the UNIX dialog utility and "
          "mostly-compatible programs",
#         Doesn't work great with several authors...
          author="Robb Shecter, Sultanbek Tezadov, Florent Rougon, "
                 "Peter Åstrand",
          author_email="robb@acm.org, http://sultan.da.ru/, flo@via.ecp.fr, "
                       "peter@cendio.se",
          maintainer="Florent Rougon",
          maintainer_email="flo@via.ecp.fr",
          url="http://people.via.ecp.fr/~flo/",
          download_url="http://people.via.ecp.fr/~flo/projects/pythondialog/"
          "dist/python2-%s-%s.tar.gz" % (PACKAGE, VERSION),
          license="LGPL",
          # Well, there isn't much UNIX-specific code in dialog.py, if at all.
          # I am putting Unix here only because of the dialog dependency...
          # Note: using the "Unix" case instead of "UNIX", because it is
          # spelled this way in Trove classifiers.
          platforms=["Unix"],
          long_description="""\
Python interface to the UNIX dialog utility
-------------------------------------------

pythondialog provides an easy, pythonic and comprehensive way to use the
dialog_ features from Python code. Backend programs that are almost compatible
with dialog are also supported if someone cares about them.

.. _dialog: http://invisible-island.net/dialog/dialog.html""",
          keywords=["dialog", "Xdialog", "whiptail", "text-mode interface"],
          classifiers=[
            "Programming Language :: Python",
            # From http://diveintopython3.org/packaging.html, I infer that
            # specifying "Python :: 2" would imply pythondialog is not going
            # to support Python 3, which would be untrue (cf. the Django
            # example).
            # "Programming Language :: Python :: 2",
            "Development Status :: 5 - Production/Stable",
            "Environment :: Console :: Curses",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: GNU Library or Lesser General Public "
            "License (LGPL)",
            "Operating System :: Unix",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Topic :: Software Development :: User Interfaces",
            "Topic :: Software Development :: Widget Sets"],
          py_modules=["dialog"])

if __name__ == "__main__": main()
