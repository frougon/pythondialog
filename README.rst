===============================================================================
Python wrapper for the UNIX "dialog" utility
===============================================================================
Easy writing of graphical interfaces for terminal-based applications
-------------------------------------------------------------------------------

WARNING
-------

This version is a backport of pythondialog to Python 2. Unless you
*really* have to use Python 2, you should go to the `pythondialog home
page`_ and download the reference implementation which, at the time of
this writing (November 2013) and for the forseeable future, is targeted
at Python 3.

.. _pythondialog home page: http://pythondialog.sourceforge.net/

This version is only here to help users who are somehow forced to still
use Python 2, even though Python 3.0 was released on December 3, 2008.
It may be the last update for Python 2. In addition, the reference
implementation is less likely to have bugs.

Before using this backport, be sure to read the `Backport-specific
notes`_ below.


Overview
--------

pythondialog is a Python wrapper for the UNIX dialog_ utility
originally written by Savio Lam and later rewritten by Thomas E. Dickey.
Its purpose is to provide an easy to use, pythonic and as complete as
possible interface to dialog_ from Python code.

.. _dialog: http://invisible-island.net/dialog/dialog.html

pythondialog is free software, licensed under the GNU LGPL (GNU Lesser
General Public License). Its home page is located at:

  http://pythondialog.sourceforge.net/

and contains a `short example`_, screenshots_, a `summary of the recent
changes`_, links to the `pydoc3-generated documentation`_, the `Git
repository`_, the `mailing list`_, the `issue tracker`_, etc.

.. _short example:  http://pythondialog.sourceforge.net/#example
.. _screenshots:    http://pythondialog.sourceforge.net/gallery.html
.. _summary of the recent changes:
                    http://pythondialog.sourceforge.net/news.html
.. _pydoc3-generated documentation:
                    http://pythondialog.sourceforge.net/doc/pythondialog.html
.. _Git repository: https://sourceforge.net/p/pythondialog/code/
.. _mailing list:   https://sourceforge.net/p/pythondialog/mailman/
.. _issue tracker:  https://sourceforge.net/p/pythondialog/_list/tickets

If you want to get a quick idea of what this module allows one to do,
you can download a release tarball and run demo.py::

  python2 demo.py

Notes:

  - the preceding command uses "python2" because we want to use the
    Python 2 backport of pythondialog;
  - depending on your system, you may have to replace "python2" with
    "python" or "python2.7", for instance.


What is pythondialog good for? What are its limitations?
--------------------------------------------------------

As you might infer from the name, dialog is a high-level program that
generates dialog boxes. So is pythondialog. They allow you to build nice
interfaces quickly and easily, but you don't have full control over the
widgets, nor can you create new widgets without modifying dialog itself.
If you need to do low-level stuff, you should have a look at ncurses or
slang instead. For sophisticated text-mode interfaces, the `Urwid Python
library`_ looks rather interesting, too.

.. _Urwid Python library: http://excess.org/urwid/


Requirements
------------

* This backport of pythondialog requires Python 2.6 or later in the 2.x
  series. It has been tested with Python 2.6 and 2.7.

* The reference implementation supports more recent versions of the
  Python interpreter. Please visit the `pythondialog home page`_ for
  more information.

* Apart from that, pythondialog requires the dialog_ program (or a
  drop-in replacement for dialog). You can download dialog from:

    http://invisible-island.net/dialog/dialog.html

  Note that some features of pythondialog may require recent versions of
  dialog.


Quick installation instructions
-------------------------------

If you have `pip <https://pypi.python.org/pypi/pip>`_ installed, you
should be able to install this backport of pythondialog with::

  pip install python2-pythondialog

(which should be run with appropriate privileges; also make sure that
your 'pip' invocation runs with the Python 2 installation you want to
install the backport for)

For more detailed instructions, you can read the INSTALL file from a
release tarball. You may also want to consult the `pip documentation
<http://www.pip-installer.org/>`_.


Backport-specific notes
-----------------------

* The pythondialog documentation is written for the reference
  implementation (Python 3 at the time of this writing). To be on the
  safe side when using the Python 2 backport, you should use Unicode
  strings every time you pass “string data” to pythondialog, and you
  will get Unicode strings in return. Indeed, these correspond directly
  to Python 3 strings, and modern versions of pythondialog (>= 2.12) are
  all based on this type of string.

  The pythondialog documentation consistently uses the term “string” (as
  opposed to “Unicode string”) because it has been written for Python 3,
  but **you should definitely use Unicode strings when using the
  Python 2 backport**. Many things happen to work with byte strings, but
  in most cases, this is pure coincidence; others fail, and won't be
  fixed. This is not a bug.

  The easiest way to use Unicode strings everywhere (or almost
  everywhere) in Python 2.x with x >= 6, consists in using::

    from __future__ import unicode_literals

  at the beginning of your Python files. This method has the additional
  benefit of preparing your transition to Python 3.

* Don't use str() in Python 2 on objects such as pythondialog exceptions
  or dialog.DialogBackendVersion instances; use unicode() instead, which
  is the Python 2 equivalent of the Python 3 str() built-in. Of course,
  using repr() on any pythondialog object should return a byte string
  when run under Python 2, because this is how the repr() API works in
  Python 2. The same holds true for str(), but this one is not supported
  by the Python 2 backport of pythondialog: it is superseded, as already
  explained, by the much more powerful unicode().

* Before taking potentially expensive decisions, you should realize that
  Unicode support is *much*, much better in Python 3 than in Python 2,
  even though the basic types are largely the same (Unicode string in
  Python 2, native string in Python 3). In Python 3, native strings
  (simply called “strings” in the Python documentation) are natural and
  ubiquitous. They can be read and written from/to the standard I/O
  streams with sane encoding defaults. str() and repr() return native
  strings, as do all standard library calls whenever expected (i.e.,
  when the return value is text, as opposed to binary data). Python 3
  strings are both powerful and easy to use.

  By contrast, in Python 2, you always have to be very careful about
  what you manipulate: byte strings or Unicode strings. Most library
  calls in your code are a potential source of bug. Usually, this kind
  of bug only pops up when user data or input introduces non-ASCII
  characters in a byte string that is then either combined with an
  Unicode string, or used in a context where the expected encoding is
  different. This means that some users get annoyed by “crappy”
  software, while the responsible developers are often not aware of any
  problem---until a bug report is filed, if ever.

  Want to use traceback.format_exc() for instance? What does it return,
  byte string or Unicode string? Experiment. Answer: byte string. Then,
  how does it deal with, e.g., accented characters in an OSError
  exception message? Experiment. Answer: it outputs the repr()
  representation of an Unicode string that uses backslash escapes for
  the non-ASCII characters, all of this inside the returned byte string.
  Conclusion: the messages seen by users will be very ugly and more or
  less undecipherable for many of them. Does it behave this way in all
  cases? Tough question. Use the source, Luke...

  With other library calls, you might get non-ASCII characters in a byte
  string. Then, the question would be: what encoding has been used to
  encode them, and is there a reliable way to detect it? In many cases,
  this is not documented and/or depends on parameters under user
  control, such as the locale settings. Again, you have to waste time
  figuring out the encoding, and often can't be sure whether your answer
  is correct in all cases.

  **Bottom line:**

    There are good reasons why the Python developers broke compatibility
    at such a fundamental level as string management between Python 2
    and Python 3. Getting Unicode support completely right in Python 2
    may require more work than porting your code to Python 3. Besides,
    future maintainance and evolutions of your program will definitely
    be easier once it is written in Python 3. Think about it.


Documentation
-------------

**Important:** be sure to read the `Backport-specific notes`_ above.

pythondialog is fully documented through Python docstrings. This
documentation can be browsed with the pydoc standalone program (maybe
pydoc2 or something such as pydoc2.7, depending on your Python
installation) or by simply opening dialog.py in a pager or editor. The
documentation of the latest version as rendered by pydoc3 should be
available at:

  http://pythondialog.sourceforge.net/doc/pythondialog.html

To generate the documentation yourself from dialog.py, you can type
"pydoc dialog" at the command prompt in the pythondialog base directory
or "pydoc /path/to/dialog.py". Alternatively, you can type::

   >>> import dialog; help(dialog)

at a Python command prompt (corresponding to the Python version you
installed pythondialog for, of course).

You can extract the documentation from dialog.py to an HTML file with
"pydoc -w dialog" or "pydoc -w /path/to/dialog.py". This will generate
dialog.html in the current directory.

Alternatively, if pythondialog is already installed, pydoc can act as
an HTTP server and provide the documentation to web browsers. For
instance, launching "pydoc -p 1234" will make it listen on TCP
port 1234. You can then point your browser to http://localhost:1234/ and
read the documentation.

See the pydoc module documentation for more information.


Enabling Deprecation Warnings
-----------------------------

There are a few places in dialog.py that send a DeprecationWarning to
warn developers about obsolete features. However, because of:

  - the dialog output to the terminal;
  - the fact that such warnings are silenced by default since Python 2.7
    and 3.2;

you have to do two things in order to see them:

  - redirect the standard error stream to a file;
  - enable the warnings for the Python interpreter.

For instance, to see the warnings produced when running the demo, you
can do::

   python2 -Wd demo.py 2>/path/to/file

and examine /path/to/file. This can also help you to find files that are
still open when your program exits.

**Note:**

  If your program is terminated by an unhandled exception while stderr
  is redirected as in the preceding command, you won't see the traceback
  until you examine the file stderr was redirected to. This can be
  disturbing, as your program may exit with no apparent reason in such
  conditions.

For more explanations and other methods to enable deprecation warnings,
please refer to:

  http://docs.python.org/2/whatsnew/2.7.html


Troubleshooting
---------------

If you have a problem with a pythondialog call, you should read its
documentation and the dialog(1) manual page. If this is not enough, you
can enable logging of shell command-line equivalents of all dialog calls
made by your program with a simple call to Dialog.setup_debug(), first
available in pythondialog 2.12. An example of this can be found in
demo.py.

As of version 2.12, you can also enable this debugging facility for
demo.py by calling it with the --debug flag (cf. 'demo.py --help').


Using Xdialog instead of dialog
-------------------------------

As far as I can tell, Xdialog has not been ported to GTK+ 2 or later. It
is not in Debian stable nor unstable (June 23, 2013). It is not
installed on my system (because of the GTK+ 1.2 dependency), and
according to the Xdialog-specific patches I received from Peter Åstrand
in 2004, was not a drop-in replacement for dialog (in particular,
Xdialog seemed to want to talk to the caller through stdout instead of
stderr, grrrrr!).

All this to say that, even though I didn't remove the options to use
another backend than dialog, nor did I remove the handful of little,
non-invasive modifications that help pythondialog work better with
Xdialog, I don't really support the latter. I test everything with
dialog, and nothing with Xdialog.

That being said, here is the *old* text of this section (from 2004), in
case you are still interested:

  Starting with 2.06, there is an "Xdialog" compatibility mode that you
  can use if you want pythondialog to run the graphical Xdialog program
  (which *should* be found under http://xdialog.free.fr/) instead of
  dialog (text-mode, based on the ncurses library).

  The primary supported platform is still dialog, but as long as only
  small modifications are enough to make pythondialog work with Xdialog,
  I am willing to support Xdialog if people are interested in it (which
  turned out to be the case for Xdialog).

  The demo.py from pythondialog 2.06 has been tested with Xdialog 2.0.6
  and found to work well (barring Xdialog's annoying behaviour with the
  file selection dialog box).


Whiptail, anyone?
-----------------

Well, pythondialog seems not to work very well with whiptail. The reason
is that whiptail is not compatible with dialog anymore. Although you can
tell pythondialog the program you want it to invoke, only programs that
are mostly dialog-compatible are supported.


History
-------

pythondialog was originally written by Robb Shecter. Sultanbek Tezadov
added some features to it (mainly the first gauge implementation, I
guess). Florent Rougon rewrote most parts of the program to make it more
robust and flexible so that it can give access to most features of the
dialog program. Peter Åstrand took over maintainership between 2004 and
2009, with particular care for the Xdialog support. Florent Rougon took
over maintainership again starting from 2009...

.. 
  # Local Variables:
  # coding: utf-8
  # fill-column: 72
  # End:
