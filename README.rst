===============================================================================
Python wrapper for the UNIX "dialog" utility
===============================================================================
Easy writing of graphical interfaces for terminal-based applications
-------------------------------------------------------------------------------

Overview
--------

pythondialog is a Python wrapper for the UNIX dialog_ utility
originally written by Savio Lam and later rewritten by Thomas E. Dickey.

.. _dialog: http://invisible-island.net/dialog/dialog.html

Its purpose is to provide an easy to use, pythonic and as complete as
possible interface to dialog_ from Python code.

pythondialog is free software, licensed under the GNU LGPL (GNU Lesser
General Public License).

If you want to get a quick idea of what this module allows you to do,
you should run demo.py::

  python3 demo.py


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

* As of version 2.12, pythondialog requires Python 3.0 or later in the
  3.x series.

* Apart from that, pythondialog requires the dialog_ program (or a
  drop-in replacement for dialog). You can download dialog from:

    http://invisible-island.net/dialog/dialog.html


Documentation
-------------

pythondialog is fully documented through Python docstrings. This
documentation can be browsed with the pydoc3 standalone program or by
simply opening dialog.py in a pager.

You can type "pydoc3 dialog" at the command prompt in the pythondialog
base directory or "pydoc3 /path/to/dialog.py". Alternatively, you can
type::

   >>> import dialog; help(dialog)

at a Python 3 command prompt.

To browse the documentation in HTML format, you can launch an HTTP
server listening on port 1234 with "pydoc3 -p 1234 &" (yes, it is that
easy) and simply browse on http://localhost:1234/ afterwards.

Alternatively, you can dump the dialog.py documentation to an HTML file
with "pydoc3 -w dialog" or "pydoc3 -w /path/to/dialog.py". This will
generate dialog.html in the current directory.

See the pydoc module documentation for more information.


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
2009. Florent Rougon took maintainership again starting from 2009...

.. 
  # Local Variables:
  # coding: utf-8
  # fill-column: 72
  # End:
