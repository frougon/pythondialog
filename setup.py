#! /usr/bin/env python

# setup.py --- Setup script for pythondialog
# Copyright (c) 2002, 2003, 2004 Florent Rougon
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os, string, sys
from distutils.core import setup

# Note:
#  The Distutils included in Python 2.1 don't understand the "license" keyword
#  argument of setup correctly (they only understand licence); as I don't want
#  to mispell it, if you run the Distutils from Python 2.1, you will get
#  License: UNKNOWN. This problem does not appear with the version included in
#  Python 2.2.

PACKAGE = "pythondialog"
VERSION = "2.7"

def main():
    setup(name=PACKAGE,
          version=VERSION,
          description="A Python interface to the UNIX dialog utility and "
          "mostly-compatible programs",
#         Doesn't work great with several authors...
          author="Robb Shecter, Sultanbek Tezadov, Florent Rougon, Peter Astrand",
          author_email="robb@acm.org, http://sultan.da.ru/, flo@via.ecp.fr",
          maintainer="Peter Astrand",
          maintainer_email="peter@cendio.se",
          url="http://pythondialog.sourceforge.net/",
          license="LGPL",
          platforms="UNIX",
          long_description="""\
A Python interface to the UNIX dialog utility, designed to provide
an easy, pythonic and as complete as possible way to use the dialog
features from Python code.
Back-end programs that are almost compatible with dialog are also
supported if someone cares about them.""",
          keywords=["dialog", "Xdialog", "whiptail", "text-mode interface"],
          py_modules=["dialog"])

if __name__ == "__main__": main()
