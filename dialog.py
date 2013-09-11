# dialog.py --- A Python interface to the ncurses-based "dialog" utility
# -*- coding: utf-8 -*-
#
# Copyright (C) 2002, 2003, 2004, 2009, 2010, 2013  Florent Rougon
# Copyright (C) 2004  Peter Åstrand
# Copyright (C) 2000  Robb Shecter, Sultanbek Tezadov
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston,
# MA  02110-1301 USA.

"""Python interface to dialog-like programs.

This module provides a Python interface to dialog-like programs such
as 'dialog' and 'Xdialog'.

It provides a Dialog class that retains some parameters such as the
program name and path as well as the values to pass as DIALOG*
environment variables to the chosen program.

For a quick start, you should look at the demo.py file that comes
with pythondialog. It demonstrates a simple use of each widget
offered by the Dialog class.

See the Dialog class documentation for general usage information,
list of available widgets and ways to pass options to dialog.


Notable exceptions
------------------

Here is the hierarchy of notable exceptions raised by this module:

  error
     ExecutableNotFound
     BadPythonDialogUsage
     PythonDialogSystemError
        PythonDialogOSError
           PythonDialogIOError  (should not be raised starting from
                                Python 3.3, as IOError becomes an
                                alias of OSError)
        PythonDialogErrorBeforeExecInChildProcess
        PythonDialogReModuleError
     UnexpectedDialogOutput
     DialogTerminatedBySignal
     DialogError
     UnableToCreateTemporaryDirectory
     PythonDialogBug
     ProbablyPythonBug

As you can see, every exception 'exc' among them verifies:

  issubclass(exc, error)

so if you don't need fine-grained error handling, simply catch
'error' (which will probably be accessible as dialog.error from your
program) and you should be safe.

Changed in version 2.12: PythonDialogIOError is now a subclass of
PythonDialogOSError in order to help with the transition from IOError
to OSError in the Python language. With this change, you can safely
replace "except PythonDialogIOError" clauses with
"except PythonDialogOSError" even if running under Python < 3.3.

"""

import collections
_VersionInfo = collections.namedtuple(
    "VersionInfo", ("major", "minor", "micro", "releasesuffix"))

class VersionInfo(_VersionInfo):
    def __str__(self):
        res = ".".join( ( str(elt) for elt in self[:3] ) )
        if self.releasesuffix:
            res += self.releasesuffix
        return res

    def __repr__(self):
        return "{0}.{1}".format(__name__, _VersionInfo.__repr__(self))

version_info = VersionInfo(2, 13, 1, None)
__version__ = str(version_info)


import sys, os, tempfile, random, re, warnings, traceback
from contextlib import contextmanager
from textwrap import dedent

# This is not for calling programs, only to prepare the shell commands that are
# written to the debug log when debugging is enabled.
try:
    from shlex import quote as _shell_quote
except ImportError:
    def _shell_quote(s):
        return "'%s'" % s.replace("'", "'\"'\"'")

# Exceptions raised by this module
#
# When adding, suppressing, renaming exceptions or changing their
# hierarchy, don't forget to update the module's docstring.
class error(Exception):
    """Base class for exceptions in pythondialog."""
    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        return self.complete_message()

    def __repr__(self):
        return "{0}.{1}({2!r})".format(__name__, self.__class__.__name__,
                                       self.message)

    def complete_message(self):
        if self.message:
            return "{0}: {1}".format(self.ExceptionShortDescription,
                                     self.message)
        else:
            return self.ExceptionShortDescription

    ExceptionShortDescription = "{0} generic exception".format("pythondialog")

# For backward-compatibility
#
# Note: this exception was not documented (only the specific ones were), so
#       the backward-compatibility binding could be removed relatively easily.
PythonDialogException = error

class ExecutableNotFound(error):
    """Exception raised when the dialog executable can't be found."""
    ExceptionShortDescription = "Executable not found"

class PythonDialogBug(error):
    """Exception raised when pythondialog finds a bug in his own code."""
    ExceptionShortDescription = "Bug in pythondialog"

# Yeah, the "Probably" makes it look a bit ugly, but:
#   - this is more accurate
#   - this avoids a potential clash with an eventual PythonBug built-in
#     exception in the Python interpreter...
class ProbablyPythonBug(error):
    """Exception raised when pythondialog behaves in a way that seems to \
indicate a Python bug."""
    ExceptionShortDescription = "Bug in python, probably"

class BadPythonDialogUsage(error):
    """Exception raised when pythondialog is used in an incorrect way."""
    ExceptionShortDescription = "Invalid use of pythondialog"

class PythonDialogSystemError(error):
    """Exception raised when pythondialog cannot perform a "system \
operation" (e.g., a system call) that should work in "normal" situations.

    This is a convenience exception: PythonDialogIOError, PythonDialogOSError
    and PythonDialogErrorBeforeExecInChildProcess all derive from this
    exception. As a consequence, watching for PythonDialogSystemError instead
    of the aformentioned exceptions is enough if you don't need precise
    details about these kinds of errors.

    Don't confuse this exception with Python's builtin SystemError
    exception.

    """
    ExceptionShortDescription = "System error"

class PythonDialogOSError(PythonDialogSystemError):
    """Exception raised when pythondialog catches an OSError exception that \
should be passed to the calling program."""
    ExceptionShortDescription = "OS error"

class PythonDialogIOError(PythonDialogOSError):
    """Exception raised when pythondialog catches an IOError exception that \
should be passed to the calling program.

    This exception should not be raised starting from Python 3.3, as
    the built-in exception IOError becomes an alias of OSError.

    """
    ExceptionShortDescription = "IO error"

class PythonDialogErrorBeforeExecInChildProcess(PythonDialogSystemError):
    """Exception raised when an exception is caught in a child process \
before the exec sytem call (included).

    This can happen in uncomfortable situations such as:
      - the system being out of memory;
      - the maximum number of open file descriptors being reached;
      - the dialog-like program being removed (or made
        non-executable) between the time we found it with
        _find_in_path and the time the exec system call attempted to
        execute it;
      - the Python program trying to call the dialog-like program
        with arguments that cannot be represented in the user's
        locale (LC_CTYPE)."""
    ExceptionShortDescription = "Error in a child process before the exec " \
                                "system call"

class PythonDialogReModuleError(PythonDialogSystemError):
    """Exception raised when pythondialog catches a re.error exception."""
    ExceptionShortDescription = "'re' module error"

class UnexpectedDialogOutput(error):
    """Exception raised when the dialog-like program returns something not \
expected by pythondialog."""
    ExceptionShortDescription = "Unexpected dialog output"

class DialogTerminatedBySignal(error):
    """Exception raised when the dialog-like program is terminated by a \
signal."""
    ExceptionShortDescription = "dialog-like terminated by a signal"

class DialogError(error):
    """Exception raised when the dialog-like program exits with the \
code indicating an error."""
    ExceptionShortDescription = "dialog-like terminated due to an error"

class UnableToCreateTemporaryDirectory(error):
    """Exception raised when we cannot create a temporary directory."""
    ExceptionShortDescription = "Unable to create a temporary directory"


@contextmanager
def OSErrorHandling():
    try:
        yield
    except OSError as e:
        raise PythonDialogOSError(str(e)) from e
    except IOError as e:
        raise PythonDialogIOError(str(e)) from e


try:
    # Values accepted for checklists
    _on_rec = re.compile(r"on$", re.IGNORECASE)
    _off_rec = re.compile(r"off$", re.IGNORECASE)

    _calendar_date_rec = re.compile(
        r"(?P<day>\d\d)/(?P<month>\d\d)/(?P<year>\d\d\d\d)$")
    _timebox_time_rec = re.compile(
        r"(?P<hour>\d\d):(?P<minute>\d\d):(?P<second>\d\d)$")
except re.error as e:
    raise PythonDialogReModuleError(str(e)) from e


# From dialog(1):
#
#   All options begin with "--" (two ASCII hyphens, for the benefit of those
#   using systems with deranged locale support).
#
#   A "--" by itself is used as an escape, i.e., the next token on the
#   command-line is not treated as an option, as in:
#        dialog --title -- --Not an option
def _dash_escape(args):
    """Escape all elements of 'args' that need escaping.

    'args' may be any sequence and is not modified by this function.
    Return a new list where every element that needs escaping has
    been escaped.

    An element needs escaping when it starts with two ASCII hyphens
    ('--'). Escaping consists in prepending an element composed of
    two ASCII hyphens, i.e., the string '--'.

    """
    res = []

    for arg in args:
        if arg.startswith("--"):
            res.extend(("--", arg))
        else:
            res.append(arg)

    return res

# We need this function in the global namespace for the lambda
# expressions in _common_args_syntax to see it when they are called.
def _dash_escape_nf(args):      # nf: non-first
    """Escape all elements of 'args' that need escaping, except the first one.

    See _dash_escape() for details. Return a new list.

    """
    if not args:
        raise PythonDialogBug("not a non-empty sequence: {0!r}".format(args))
    l = _dash_escape(args[1:])
    l.insert(0, args[0])
    return l

def _simple_option(option, enable):
    """Turn on or off the simplest dialog Common Options."""
    if enable:
        return (option,)
    else:
        # This will not add any argument to the command line
        return ()


# This dictionary allows us to write the dialog common options in a Pythonic
# way (e.g. dialog_instance.checklist(args, ..., title="Foo", no_shadow=True)).
#
# Options such as --separate-output should obviously not be set by the user
# since they affect the parsing of dialog's output:
_common_args_syntax = {
    "ascii_lines": lambda enable: _simple_option("--ascii-lines", enable),
    "aspect": lambda ratio: _dash_escape_nf(("--aspect", str(ratio))),
    "backtitle": lambda backtitle: _dash_escape_nf(("--backtitle", backtitle)),
    # Obsolete according to dialog(1)
    "beep": lambda enable: _simple_option("--beep", enable),
    # Obsolete according to dialog(1)
    "beep_after": lambda enable: _simple_option("--beep-after", enable),
    # Warning: order = y, x!
    "begin": lambda coords: _dash_escape_nf(
        ("--begin", str(coords[0]), str(coords[1]))),
    "cancel_label": lambda s: _dash_escape_nf(("--cancel-label", s)),
    # Old, unfortunate choice of key, kept for backward compatibility
    "cancel": lambda s: _dash_escape_nf(("--cancel-label", s)),
    "clear": lambda enable: _simple_option("--clear", enable),
    "colors": lambda enable: _simple_option("--colors", enable),
    "column_separator": lambda s: _dash_escape_nf(("--column-separator", s)),
    "cr_wrap": lambda enable: _simple_option("--cr-wrap", enable),
    "create_rc": lambda filename: _dash_escape_nf(("--create-rc", filename)),
    "date_format": lambda s: _dash_escape_nf(("--date-format", s)),
    "defaultno": lambda enable: _simple_option("--defaultno", enable),
    "default_button": lambda s: _dash_escape_nf(("--default-button", s)),
    "default_item": lambda s: _dash_escape_nf(("--default-item", s)),
    "exit_label": lambda s: _dash_escape_nf(("--exit-label", s)),
    "extra_button": lambda enable: _simple_option("--extra-button", enable),
    "extra_label": lambda s: _dash_escape_nf(("--extra-label", s)),
    "help": lambda enable: _simple_option("--help", enable),
    "help_button": lambda enable: _simple_option("--help-button", enable),
    "help_label": lambda s: _dash_escape_nf(("--help-label", s)),
    "hfile": lambda filename: _dash_escape_nf(("--hfile", filename)),
    "hline": lambda s: _dash_escape_nf(("--hline", s)),
    "ignore": lambda enable: _simple_option("--ignore", enable),
    "insecure": lambda enable: _simple_option("--insecure", enable),
    "item_help": lambda enable: _simple_option("--item-help", enable),
    "keep_tite": lambda enable: _simple_option("--keep-tite", enable),
    "keep_window": lambda enable: _simple_option("--keep-window", enable),
    "max_input": lambda size: _dash_escape_nf(("--max-input", str(size))),
    "no_cancel": lambda enable: _simple_option("--no-cancel", enable),
    "nocancel": lambda enable: _simple_option("--nocancel", enable),
    "no_collapse": lambda enable: _simple_option("--no-collapse", enable),
    "no_kill": lambda enable: _simple_option("--no-kill", enable),
    "no_label": lambda s: _dash_escape_nf(("--no-label", s)),
    "no_lines": lambda enable: _simple_option("--no-lines", enable),
    "no_mouse": lambda enable: _simple_option("--no-mouse", enable),
    "no_nl_expand": lambda enable: _simple_option("--no-nl-expand", enable),
    "no_ok": lambda enable: _simple_option("--no-ok", enable),
    "no_shadow": lambda enable: _simple_option("--no-shadow", enable),
    "no_tags": lambda enable: _simple_option("--no-tags", enable),
    "ok_label": lambda s: _dash_escape_nf(("--ok-label", s)),
    # cf. Dialog.maxsize()
    "print_maxsize": lambda enable: _simple_option("--print-maxsize",
                                                   enable),
    "print_size": lambda enable: _simple_option("--print-size", enable),
    # cf. Dialog.backend_version()
    "print_version": lambda enable: _simple_option("--print-version",
                                                   enable),
    "scrollbar": lambda enable: _simple_option("--scrollbar", enable),
    "separate_output": lambda enable: _simple_option("--separate-output",
                                                     enable),
    "separate_widget": lambda s: _dash_escape_nf(("--separate-widget", s)),
    "shadow": lambda enable: _simple_option("--shadow", enable),
    # Obsolete according to dialog(1)
    "size_err": lambda enable: _simple_option("--size-err", enable),
    "sleep": lambda secs: _dash_escape_nf(("--sleep", str(secs))),
    "stderr": lambda enable: _simple_option("--stderr", enable),
    "stdout": lambda enable: _simple_option("--stdout", enable),
    "tab_correct": lambda enable: _simple_option("--tab-correct", enable),
    "tab_len": lambda n: _dash_escape_nf(("--tab-len", str(n))),
    "time_format": lambda s: _dash_escape_nf(("--time-format", s)),
    "timeout": lambda secs: _dash_escape_nf(("--timeout", str(secs))),
    "title": lambda title: _dash_escape_nf(("--title", title)),
    "trace": lambda filename: _dash_escape_nf(("--trace", filename)),
    "trim": lambda enable: _simple_option("--trim", enable),
    "version": lambda enable: _simple_option("--version", enable),
    "visit_items": lambda enable: _simple_option("--visit-items", enable),
    "yes_label": lambda s: _dash_escape_nf(("--yes-label", s)) }


def _find_in_path(prog_name):
    """Search an executable in the PATH.

    If PATH is not defined, the default path ":/bin:/usr/bin" is
    used.

    Return a path to the file or None if no readable and executable
    file is found.

    Notable exception: PythonDialogOSError

    """
    with OSErrorHandling():
        # Note that the leading empty component in the default value for PATH
        # could lead to the returned path not being absolute.
        PATH = os.getenv("PATH", ":/bin:/usr/bin") # see the execvp(3) man page
        for d in PATH.split(":"):
            file_path = os.path.join(d, prog_name)
            if os.path.isfile(file_path) \
               and os.access(file_path, os.R_OK | os.X_OK):
                return file_path
        return None


def _path_to_executable(f):
    """Find a path to an executable.

    Find a path to an executable, using the same rules as the POSIX
    exec*p functions (see execvp(3) for instance).

    If 'f' contains a '/', it is assumed to be a path and is simply
    checked for read and write permissions; otherwise, it is looked
    for according to the contents of the PATH environment variable,
    which defaults to ":/bin:/usr/bin" if unset.

    The returned path is not necessarily absolute.

    Notable exceptions:

        ExecutableNotFound
        PythonDialogOSError

    """
    with OSErrorHandling():
        if '/' in f:
            if os.path.isfile(f) and \
                   os.access(f, os.R_OK | os.X_OK):
                res = f
            else:
                raise ExecutableNotFound("%s cannot be read and executed" % f)
        else:
            res = _find_in_path(f)
            if res is None:
                raise ExecutableNotFound(
                    "can't find the executable for the dialog-like "
                    "program")

    return res


def _to_onoff(val):
    """Convert boolean expressions to "on" or "off".

    Return:
      - "on" if 'val' is True, a non-zero integer, "on" or any case
        variation thereof;
      - "off" if 'val' is False, 0, "off" or any case variation thereof.

    Notable exceptions:

        PythonDialogReModuleError
        BadPythonDialogUsage

    """
    if isinstance(val, (bool, int)):
        return "on" if val else "off"
    elif isinstance(val, str):
        try:
            if _on_rec.match(val):
                return "on"
            elif _off_rec.match(val):
                return "off"
        except re.error as e:
            raise PythonDialogReModuleError(str(e)) from e

    raise BadPythonDialogUsage("invalid boolean value: {0!r}".format(val))


def _compute_common_args(mapping):
    """Compute the list of arguments for dialog common options.

    Compute a list of the command-line arguments to pass to dialog
    from a keyword arguments dictionary for options listed as "common
    options" in the manual page for dialog. These are the options
    that are not tied to a particular widget.

    This allows to specify these options in a pythonic way, such as:

       d.checklist(<usual arguments for a checklist>,
                   title="...",
                   backtitle="...")

    instead of having to pass them with strings like "--title foo" or
    "--backtitle bar".

    Notable exceptions: None

    """
    args = []
    for option, value in mapping.items():
        args.extend(_common_args_syntax[option](value))
    return args


def _create_temporary_directory():
    """Create a temporary directory (securely).

    Return the directory path.

    Notable exceptions:
        - UnableToCreateTemporaryDirectory
        - PythonDialogOSError
        - exceptions raised by the tempfile module

    """
    find_temporary_nb_attempts = 5
    for i in range(find_temporary_nb_attempts):
        with OSErrorHandling():
            tmp_dir = os.path.join(tempfile.gettempdir(),
                                   "%s-%d" \
                                   % ("pythondialog",
                                      random.randint(0, sys.maxsize)))
        try:
            os.mkdir(tmp_dir, 0o700)
        except os.error:
            continue
        else:
            break
    else:
        raise UnableToCreateTemporaryDirectory(
            "somebody may be trying to attack us")

    return tmp_dir


# DIALOG_OK, DIALOG_CANCEL, etc. are environment variables controlling
# dialog's exit status in the corresponding situation.
#
# Note:
#    - 127 must not be used for any of the DIALOG_* values. It is used
#      when a failure occurs in the child process before it exec()s
#      dialog (where "before" includes a potential exec() failure).
#    - 126 is also used (although in presumably rare situations).
_dialog_exit_status_vars = { "OK": 0,
                             "CANCEL": 1,
                             "ESC": 2,
                             "ERROR": 3,
                             "EXTRA": 4,
                             "HELP": 5,
                             "ITEM_HELP": 6}


# Main class of the module
class Dialog:
    """Class providing bindings for dialog-compatible programs.

    This class allows you to invoke dialog or a compatible program in
    a pythonic way to build quicky and easily simple but nice text
    interfaces.

    An application typically creates one instance of the Dialog class
    and uses it for all its widgets, but it is possible to
    concurrently use several instances of this class with different
    parameters (such as the background title) if you have a need
    for this.

    The exit code (exit status) returned by dialog is to be compared
    with the DIALOG_OK, DIALOG_CANCEL, DIALOG_ESC, DIALOG_ERROR,
    DIALOG_EXTRA, DIALOG_HELP and DIALOG_ITEM_HELP attributes of the
    Dialog instance (they are integers).

    Note: although this class does all it can to allow the caller to
          differentiate between the various reasons that caused a
          dialog box to be closed, its backend, dialog 0.9a-20020309a
          for my tests, doesn't always return DIALOG_ESC when the
          user presses the ESC key, but often returns DIALOG_ERROR
          instead. The exit codes returned by the corresponding
          Dialog methods are of course just as wrong in these cases.
          You've been warned.


    Public methods of the Dialog class (mainly widgets)
    ---------------------------------------------------

    The Dialog class has the following widget-producing methods:

      calendar
      checklist
      dselect
      editbox
      form
      fselect

      gauge_start
      gauge_update
      gauge_stop

      infobox
      inputbox
      inputmenu
      menu
      mixedform
      mixedgauge
      msgbox
      passwordbox
      passwordform
      pause
      programbox
      progressbox
      radiolist
      rangebox
      scrollbox
      tailbox
      textbox
      timebox
      yesno

    All these widgets are described in the docstrings of the
    corresponding Dialog methods. Many of these descriptions are
    adapted from the dialog(1) manual page, with the kind permission
    of Thomas Dickey.

    The Dialog class also has a few non-widget-producing methods:

      add_persistent_args
      backend_version
      maxsize
      set_background_title

      clear                 (has been OBSOLETE for many years!)
      setBackgroundTitle    (has been OBSOLETE for many years!)


    Passing dialog "Common Options"
    -------------------------------

    Every widget method has a **kwargs argument allowing you to pass
    dialog so-called Common Options (see the dialog(1) manual page)
    to dialog for this widget call. For instance, if 'd' is a Dialog
    instance, you can write:

      d.checklist(args, ..., title="A Great Title", no_shadow=True)

    The no_shadow option is worth looking at:

      1. It is an option that takes no argument as far as dialog is
         concerned (unlike the "--title" option, for instance). When
         you list it as a keyword argument, the option is really
         passed to dialog only if the value you gave it evaluates to
         True in a boolean context. For instance, "no_shadow=True"
         will cause "--no-shadow" to be passed to dialog whereas
         "no_shadow=False" will cause this option not to be passed to
         dialog at all.

      2. It is an option that has a hyphen (-) in its name, which you
         must change into an underscore (_) to pass it as a Python
         keyword argument. Therefore, "--no-shadow" is passed by
         giving a "no_shadow=True" keyword argument to a Dialog method
         (the leading two dashes are also consistently removed).


    Exceptions
    ----------

    Please refer to the specific methods' docstrings or simply to the
    module's docstring for a list of all exceptions that might be
    raised by this class' methods.

    """
    try:
        _print_maxsize_cre = re.compile(r"""^MaxSize:[ \t]+
                                            (?P<rows>\d+),[ \t]*
                                            (?P<columns>\d+)[ \t]*$""",
                                        re.VERBOSE)
        _print_version_cre = re.compile(
            r"^Version:[ \t]+(?P<version>.+?)[ \t]*$", re.MULTILINE)
    except re.error as e:
        raise PythonDialogReModuleError(str(e)) from e

    def __init__(self, dialog="dialog", DIALOGRC=None,
                 compat="dialog", use_stdout=None):
        """Constructor for Dialog instances.

        dialog     -- name of (or path to) the dialog-like program to
                      use; if it contains a '/', it is assumed to be
                      a path and is used as is; otherwise, it is
                      looked for according to the contents of the
                      PATH environment variable, which defaults to
                      ":/bin:/usr/bin" if unset.
        DIALOGRC --   string to pass to the dialog-like program as
                      the DIALOGRC environment variable, or None if
                      no modification to the environment regarding
                      this variable should be done in the call to the
                      dialog-like program
        compat     -- compatibility mode (see below)
        use_stdout -- read dialog's standard output stream instead of
                      its standard error stream in order to get
                      most 'results' (user-supplied strings, etc.;
                      basically everything apart from the exit
                      status). This is for compatibility with Xdialog
                      and should only be used if you have a good
                      reason to do so.


        The officially supported dialog-like program in pythondialog
        is the well-known dialog program written in C, based on the
        ncurses library. It is also known as cdialog and its home
        page is currently (2013-08-12) located at:

            http://invisible-island.net/dialog/dialog.html

        If you want to use a different program such as Xdialog, you
        should indicate the executable file name with the 'dialog'
        argument *and* the compatibility type that you think it
        conforms to with the 'compat' argument. Currently, 'compat'
        can be either "dialog" (for dialog; this is the default) or
        "Xdialog" (for, well, Xdialog).

        The 'compat' argument allows me to cope with minor
        differences in behaviour between the various programs
        implementing the dialog interface (not the text or graphical
        interface, I mean the "API"). However, having to support
        various APIs simultaneously is ugly and I would really prefer
        you to report bugs to the relevant maintainers when you find
        incompatibilities with dialog. This is for the benefit of
        pretty much everyone that relies on the dialog interface.

        Notable exceptions:

            ExecutableNotFound
            PythonDialogOSError

        """
        # DIALOGRC differs from the other DIALOG* variables in that:
        #   1. It should be a string if not None
        #   2. We may very well want it to be unset
        if DIALOGRC is not None:
            self.DIALOGRC = DIALOGRC

        # After reflexion, I think DIALOG_OK, DIALOG_CANCEL, etc.
        # should never have been instance attributes (I cannot see a
        # reason why the user would want to change their values or
        # even read them), but it is a bit late, now. So, we set them
        # based on the (global) _dialog_exit_status_vars.keys.
        for status, code in _dialog_exit_status_vars.items():
            varname = "DIALOG_" + status
            setattr(self, varname, code)

        self._dialog_prg = _path_to_executable(dialog)
        self.compat = compat
        self.dialog_persistent_arglist = []

        # Use stderr or stdout for reading dialog's output?
        if self.compat == "Xdialog":
            # Default to using stdout for Xdialog
            self.use_stdout = True
        else:
            self.use_stdout = False
        if use_stdout is not None:
            # Allow explicit setting
            self.use_stdout = use_stdout
        if self.use_stdout:
            self.add_persistent_args(["--stdout"])

        self.setup_debug(False)

    @classmethod
    def dash_escape(cls, args):
        """Escape all elements of 'args' that need escaping.

        'args' may be any sequence and is not modified by this method.
        Return a new list where every element that needs escaping has
        been escaped.

        An element needs escaping when it starts with two ASCII hyphens
        ('--'). Escaping consists in prepending an element composed of
        two ASCII hyphens, i.e., the string '--'.

        All high-level Dialog methods automatically perform dash
        escaping where appropriate. In particular, this is the case
        for every method that provides a widget: yesno(), msgbox(),
        etc. You only need to do it yourself when calling a low-level
        method such as add_persistent_args().

        """
        return _dash_escape(args)

    @classmethod
    def dash_escape_nf(cls, args):
        """Escape all elements of 'args' that need escaping, except the first one.

        See dash_escape() for details. Return a new list.

        All high-level Dialog methods automatically perform dash
        escaping where appropriate. In particular, this is the case
        for every method that provides a widget: yesno(), msgbox(),
        etc. You only need to do it yourself when calling a low-level
        method such as add_persistent_args().

        """
        return _dash_escape_nf(args)

    def add_persistent_args(self, args):
        """Add arguments to use for every subsequent dialog call.

        This method cannot guess which elements of 'args' are dialog
        options (such as '--title') and which are not (for instance,
        you might want to use '--title' or even '--' as an argument
        to a dialog option). Therefore, this method does not perform
        any kind of dash escaping; you have to do it yourself.
        dash_escape() and dash_escape_nf() may be useful for this
        purpose.

        """
        self.dialog_persistent_arglist.extend(args)

    def set_background_title(self, text):
        """Set the background title for dialog.

        text   -- string to use as the background title

        """
        self.add_persistent_args(self.dash_escape_nf(("--backtitle", text)))

    # For compatibility with the old dialog
    def setBackgroundTitle(self, text):
        """Set the background title for dialog.

        text   -- string to use as the background title

        This method is obsolete. Please remove calls to it from your
        programs.

        """
        warnings.warn("Dialog.setBackgroundTitle() has been obsolete for "
                      "many years; use Dialog.set_background_title() instead",
                      DeprecationWarning)
        self.set_background_title(text)

    def setup_debug(self, enable, file=None, always_flush=False):
        """Setup the debugging parameters.

        When enabled, all dialog commands are written to 'file' using
        Bourne shell syntax.

        enable         -- boolean indicating whether to enable or
                          disable debugging
        file           -- file object where to write debugging
                          information
        always_flush   -- boolean indicating whether to call
                          file.flush() after each command written

        """
        self._debug_enabled = enable

        if not hasattr(self, "_debug_logfile"):
            self._debug_logfile = None
        # Allows to switch debugging on and off without having to pass the file
        # object again and again.
        if file is not None:
            self._debug_logfile = file

        if enable and self._debug_logfile is None:
            raise BadPythonDialogUsage(
                "you must specify a file object when turning debugging on")

        self._debug_always_flush = always_flush
        self._debug_first_output = True

    def _write_command_to_file(self, env, arglist):
        envvar_settings_list = []

        if "DIALOGRC" in env:
            envvar_settings_list.append(
                "DIALOGRC={0}".format(_shell_quote(env["DIALOGRC"])))

        for var in _dialog_exit_status_vars.keys():
            varname = "DIALOG_" + var
            envvar_settings_list.append(
                "{0}={1}".format(varname, _shell_quote(env[varname])))

        command_str = ' '.join(envvar_settings_list +
                               list(map(_shell_quote, arglist)))
        s = "{separator}{cmd}\n\nArgs: {args!r}\n".format(
            separator="" if self._debug_first_output else ("-" * 79) + "\n",
            cmd=command_str, args=arglist)

        self._debug_logfile.write(s)
        if self._debug_always_flush:
            self._debug_logfile.flush()

        self._debug_first_output = False

    def _call_program(self, cmdargs, *, dash_escape="non-first",
                      use_persistent_args=True,
                      redir_child_stdin_from_fd=None, close_fds=(), **kwargs):
        """Do the actual work of invoking the dialog-like program.

        Communication with the dialog-like program is performed
        through one pipe(2) and optionally a user-specified file
        descriptor, depending on 'redir_child_stdin_from_fd'. The
        pipe allows the parent process to read what dialog writes on
        its standard error[*] stream.

        If 'use_persistent_args' is True (the default), the elements
        of self.dialog_persistent_arglist are passed as the first
        arguments to self._dialog_prg; otherwise,
        self.dialog_persistent_arglist is not used at all. The
        remaining arguments are those computed from kwargs followed
        by the elements of 'cmdargs'.

        If 'dash_escape' is the string "non-first", then every
        element of 'cmdargs' that starts with '--' is escaped by
        prepending an element consisting of '--', except the first
        one (which is usually a dialog option such as '--yesno').
        In order to disable this escaping mechanism, pass the string
        "none" as 'dash_escape'.

        If 'redir_child_stdin_from_fd' is not None, it should be an
        open file descriptor (i.e., an integer). That file descriptor
        will be connected to dialog's standard input. This is used by
        the gauge widget to feed data to dialog, as well as for
        progressbox() to allow dialog to read data from a
        possibly-growing file.

        If 'redir_child_stdin_from_fd' is None, the standard input in
        the child process (which runs dialog) is not redirected in
        any way.

        If 'close_fds' is passed, it should be a sequence of
        file descriptors that will be closed by the child process
        before it exec()s the dialog-like program.

          [*] standard ouput stream with 'use_stdout'

        Notable exception: PythonDialogOSError (if any of the pipe(2)
                           or close(2) system calls fails...)

        """
        # We want to define DIALOG_OK, DIALOG_CANCEL, etc. in the
        # environment of the child process so that we know (and
        # even control) the possible dialog exit statuses.
        new_environ = {}
        new_environ.update(os.environ)
        for var in _dialog_exit_status_vars:
            varname = "DIALOG_" + var
            new_environ[varname] = str(getattr(self, varname))
        if hasattr(self, "DIALOGRC"):
            new_environ["DIALOGRC"] = self.DIALOGRC

        if dash_escape == "non-first":
            # Escape all elements of 'cmdargs' that start with '--', except the
            # first one.
            cmdargs = self.dash_escape_nf(cmdargs)
        elif dash_escape != "none":
            raise PythonDialogBug("invalid value for 'dash_escape' parameter: "
                                  "{0!r}".format(dash_escape))

        arglist = [ self._dialog_prg ]

        if use_persistent_args:
            arglist.extend(self.dialog_persistent_arglist)

        arglist.extend(_compute_common_args(kwargs) + cmdargs)

        if self._debug_enabled:
            # Write the complete command line with environment variables
            # setting to the debug log file (Bourne shell syntax for easy
            # copy-pasting into a terminal, followed by repr(arglist)).
            self._write_command_to_file(new_environ, arglist)

        # Create a pipe so that the parent process can read dialog's
        # output on stderr (stdout with 'use_stdout')
        with OSErrorHandling():
            # rfd = File Descriptor for Reading
            # wfd = File Descriptor for Writing
            (child_output_rfd, child_output_wfd) = os.pipe()

        child_pid = os.fork()
        if child_pid == 0:
            # We are in the child process. We MUST NOT raise any exception.
            try:
                # 1) If the write end of a pipe isn't closed, the read end
                #    will never see EOF, which can indefinitely block the
                #    child waiting for input. To avoid this, the write end
                #    must be closed in the father *and* child processes.
                # 2) The child process doesn't need child_output_rfd.
                for fd in close_fds + (child_output_rfd,):
                    os.close(fd)
                # We want:
                #   - to keep a reference to the father's stderr for error
                #     reporting (and use line-buffering for this stream);
                #   - dialog's output on stderr[*] to go to child_output_wfd;
                #   - data written to fd 'redir_child_stdin_from_fd'
                #     (if not None) to go to dialog's stdin.
                #
                #       [*] stdout with 'use_stdout'
                father_stderr = os.fdopen(os.dup(2), mode="w", buffering=1)
                os.dup2(child_output_wfd, 1 if self.use_stdout else 2)
                if redir_child_stdin_from_fd is not None:
                    os.dup2(redir_child_stdin_from_fd, 0)

                os.execve(self._dialog_prg, arglist, new_environ)
            except:
                print(traceback.format_exc(), file=father_stderr)
                father_stderr.close()
                os._exit(127)

            # Should not happen unless there is a bug in Python
            os._exit(126)

        # We are in the father process.
        #
        # It is essential to close child_output_wfd, otherwise we will never
        # see EOF while reading on child_output_rfd and the parent process
        # will block forever on the read() call.
        # [ after the fork(), the "reference count" of child_output_wfd from
        #   the operating system's point of view is 2; after the child exits,
        #   it is 1 until the father closes it itself; then it is 0 and a read
        #   on child_output_rfd encounters EOF once all the remaining data in
        #   the pipe has been read. ]
        with OSErrorHandling():
            os.close(child_output_wfd)
        return (child_pid, child_output_rfd)

    def _wait_for_program_termination(self, child_pid, child_output_rfd):
        """Wait for a dialog-like process to terminate.

        This function waits for the specified process to terminate,
        raises the appropriate exceptions in case of abnormal
        termination and returns the exit status and stderr[*] output
        of the process as a tuple: (exit_code, output_string).

        'child_output_rfd' must be the file descriptor for the
        reading end of the pipe created by self._call_program(), the
        writing end of which was connected by self._call_program()
        to the child process's standard error[*].

        This function reads the process' output on standard error[*]
        from 'child_output_rfd' and closes this file descriptor once
        this is done.

          [*] actually, standard output if self.use_stdout is True

        Notable exceptions:

            DialogTerminatedBySignal
            DialogError
            PythonDialogErrorBeforeExecInChildProcess
            PythonDialogIOError    if the Python version is < 3.3
            PythonDialogOSError
            PythonDialogBug
            ProbablyPythonBug

        """
        exit_info = os.waitpid(child_pid, 0)[1]
        if os.WIFEXITED(exit_info):
            exit_code = os.WEXITSTATUS(exit_info)
        # As we wait()ed for the child process to terminate, there is no
        # need to call os.WIFSTOPPED()
        elif os.WIFSIGNALED(exit_info):
            raise DialogTerminatedBySignal("the dialog-like program was "
                                           "terminated by signal %d" %
                                           os.WTERMSIG(exit_info))
        else:
            raise PythonDialogBug("please report this bug to the "
                                  "pythondialog maintainer(s)")

        if exit_code == self.DIALOG_ERROR:
            raise DialogError(
                "the dialog-like program exited with code %d (was passed to "
                "it as the DIALOG_ERROR environment variable). Sometimes, "
                "the reason is simply that dialog was given a height or width "
                "parameter that is too big for the terminal in use."
                % exit_code)
        elif exit_code == 127:
            raise PythonDialogErrorBeforeExecInChildProcess(dedent("""\
            possible reasons include:
              - the dialog-like program could not be executed (this can happen
                for instance if the Python program is trying to call the
                dialog-like program with arguments that cannot be represented
                in the user's locale [LC_CTYPE]);
              - the system is out of memory;
              - the maximum number of open file descriptors has been reached;
              - a cosmic ray hit the system memory and flipped nasty bits.
            There ought to be a traceback above this message that describes
            more precisely what happened."""))
        elif exit_code == 126:
            raise ProbablyPythonBug(
                "a child process returned with exit status 126; this might "
                "be the exit status of the dialog-like program, for some "
                "unknown reason (-> probably a bug in the dialog-like "
                "program); otherwise, we have probably found a python bug")

        # We might want to check here whether exit_code is really one of
        # DIALOG_OK, DIALOG_CANCEL, etc. However, I prefer not doing it
        # because it would break pythondialog for no strong reason when new
        # exit codes are added to the dialog-like program.
        #
        # As it is now, if such a thing happens, the program using
        # pythondialog may receive an exit_code it doesn't know about. OK, the
        # programmer just has to tell the pythondialog maintainer about it and
        # can temporarily set the appropriate DIALOG_* environment variable if
        # he wants and assign the corresponding value to the Dialog instance's
        # DIALOG_FOO attribute from his program. He doesn't even need to use a
        # patched pythondialog before he upgrades to a version that knows
        # about the new exit codes.
        #
        # The bad thing that might happen is a new DIALOG_FOO exit code being
        # the same by default as one of those we chose for the other exit
        # codes already known by pythondialog. But in this situation, the
        # check that is being discussed wouldn't help at all.

        # Read dialog's output on its stderr (stdout with 'use_stdout')
        with OSErrorHandling():
            with os.fdopen(child_output_rfd, "r") as f:
                child_output = f.read()
            # The closing of the file object causes the end of the pipe we used
            # to read dialog's output on its stderr to be closed too. This is
            # important, otherwise invoking dialog enough times would
            # eventually exhaust the maximum number of open file descriptors.

        return (exit_code, child_output)

    def _perform(self, cmdargs, *, dash_escape="non-first",
                 use_persistent_args=True, **kwargs):
        """Perform a complete dialog-like program invocation.

        This function invokes the dialog-like program, waits for its
        termination and returns its exit status and whatever it wrote
        on its standard error stream.

        See _call_program() for a description of the parameters.

        Notable exceptions:

            any exception raised by self._call_program() or
            self._wait_for_program_termination()

        """
        (child_pid, child_output_rfd) = \
                    self._call_program(cmdargs, dash_escape=dash_escape,
                                       use_persistent_args=use_persistent_args,
                                       **kwargs)
        (exit_code, output) = \
                    self._wait_for_program_termination(child_pid,
                                                       child_output_rfd)
        return (exit_code, output)

    def _strip_xdialog_newline(self, output):
        """Remove trailing newline (if any) in Xdialog compatibility mode"""
        if self.compat == "Xdialog" and output.endswith("\n"):
            output = output[:-1]
        return output

    # This is for compatibility with the old dialog.py
    def _perform_no_options(self, cmd):
        """Call dialog without passing any more options."""

        warnings.warn("Dialog._perform_no_options() has been obsolete for "
                      "many years", DeprecationWarning)
        return os.system(self._dialog_prg + ' ' + cmd)

    # For compatibility with the old dialog.py
    def clear(self):
        """Clear the screen. Equivalent to the dialog --clear option.

        This method is obsolete. Please remove calls to it from your
        programs. You may use the clear(1) program to clear the screen.
        cf. clear_screen() in demo.py for an example.

        """
        warnings.warn("Dialog.clear() has been obsolete for many years.\n"
                      "You may use the clear(1) program to clear the screen.\n"
                      "cf. clear_screen() in demo.py for an example",
                      DeprecationWarning)
        self._perform_no_options('--clear')

    def backend_version(self):
        """Get the version of the dialog-like program (backend).

        If the exit status of the dialog-like program is
        self.DIALOG_OK, return its version as a string; otherwise,
        return None.

        This version is not to be confused with the pythondialog
        version.

        Notable exceptions:

            PythonDialogReModuleError
            any exception raised by self._perform()

        """
        code, output = self._perform(["--print-version"],
                                     use_persistent_args=False)
        if code == self.DIALOG_OK:
            try:
                mo = self._print_version_cre.match(output)
                if mo:
                    return mo.group("version")
                else:
                    raise PythonDialogBug(
                        "Unable to parse the output of '{0} --print-version': "
                        "{1!r}".format(self._dialog_prg, output))
            except re.error as e:
                raise PythonDialogReModuleError(str(e)) from e
        else:
            return None

    def maxsize(self, **kwargs):
        """Get the maximum size of dialog boxes.

        If the exit status of the dialog-like program is
        self.DIALOG_OK, return a (lines, cols) tuple of integers;
        otherwise, return None.

        If you want to obtain the number of lines and columns of the
        terminal, you should call this method with
        use_persistent_args=False, because arguments such as
        --backtitle modify the values returned.

        Notable exceptions:

            PythonDialogReModuleError
            any exception raised by self._perform()

        """
        code, output = self._perform(["--print-maxsize"], **kwargs)
        if code == self.DIALOG_OK:
            try:
                mo = self._print_maxsize_cre.match(output)
                if mo:
                    return tuple(map(int, mo.group("rows", "columns")))
                else:
                    raise PythonDialogBug(
                        "Unable to parse the output of '{0} --print-maxsize': "
                        "{1!r}".format(self._dialog_prg, output))
            except re.error as e:
                raise PythonDialogReModuleError(str(e)) from e
        else:
            return None

    def calendar(self, text, height=6, width=0, day=0, month=0, year=0,
                 **kwargs):
        """Display a calendar dialog box.

        text   -- text to display in the box
        height -- height of the box (minus the calendar height)
        width  -- width of the box
        day    -- inititial day highlighted
        month  -- inititial month displayed
        year   -- inititial year selected (0 causes the current date
                  to be used as the initial date)

        A calendar box displays month, day and year in separately
        adjustable windows. If the values for day, month or year are
        missing or negative, the current date's corresponding values
        are used. You can increment or decrement any of those using
        the left, up, right and down arrows. Use tab or backtab to
        move between windows. If the year is given as zero, the
        current date is used as an initial value.

        Return a tuple of the form (code, date) where 'code' is the
        exit status (an integer) of the dialog-like program and
        'date' is a list of the form [day, month, year] (where 'day',
        'month' and 'year' are integers corresponding to the date
        chosen by the user) if the box was closed with OK, or None if
        it was closed with the Cancel button.

        Notable exceptions:
            - any exception raised by self._perform()
            - UnexpectedDialogOutput
            - PythonDialogReModuleError

        """
        (code, output) = self._perform(
            ["--calendar", text, str(height), str(width), str(day),
               str(month), str(year)],
            **kwargs)
        if code == self.DIALOG_OK:
            try:
                mo = _calendar_date_rec.match(output)
            except re.error as e:
                raise PythonDialogReModuleError(str(e)) from e

            if mo is None:
                raise UnexpectedDialogOutput(
                    "the dialog-like program returned the following "
                    "unexpected date with the calendar box: %s" % output)
            date = [ int(s) for s in mo.group("day", "month", "year") ]
        else:
            date = None
        return (code, date)

    def checklist(self, text, height=15, width=54, list_height=7,
                  choices=[], **kwargs):
        """Display a checklist box.

        text        -- text to display in the box
        height      -- height of the box
        width       -- width of the box
        list_height -- number of entries displayed in the box (which
                       can be scrolled) at a given time
        choices     -- a list of tuples (tag, item, status) where
                       'status' specifies the initial on/off state of
                       each entry; can be True or False, 1 or 0, "on"
                       or "off" (True, 1 and "on" meaning checked),
                       or any case variation of these two strings.

        Return a tuple of the form (code, [tag, ...]) with the tags
        for the entries that were selected by the user. 'code' is the
        exit status of the dialog-like program.

        If the user exits with ESC or CANCEL, the returned tag list
        is empty.

        Notable exceptions:

            any exception raised by self._perform() or _to_onoff()

        """
        cmd = ["--checklist", text, str(height), str(width), str(list_height)]
        for t in choices:
            cmd.extend((t[0], t[1], _to_onoff(t[2])))

        # The dialog output cannot be parsed reliably (at least in dialog
        # 0.9b-20040301) without --separate-output (because double quotes in
        # tags are escaped with backslashes, but backslashes are not
        # themselves escaped and you have a problem when a tag ends with a
        # backslash--the output makes you think you've encountered an embedded
        # double-quote).
        kwargs["separate_output"] = True

        (code, output) = self._perform(cmd, **kwargs)

        # Since we used --separate-output, the tags are separated by a newline
        # in the output. There is also a final newline after the last tag.
        if output:
            return (code, output.split('\n')[:-1])
        else:                           # empty selection
            return (code, [])

    def _generic_form(self, widget_name, method_name, text, elements, height=0,
                      width=0, form_height=0, **kwargs):
        cmd = ["--%s" % widget_name, text, str(height), str(width),
               str(form_height)]

        for elt in elements:
            # Give names to make the code more readable
            if len(elt) == 8:   # code path for --form and --passwordform
                label, yl, xl, item, yi, xi, field_length, input_length = elt
            elif len(elt) == 9: # code path for --mixedform
                label, yl, xl, item, yi, xi, field_length, input_length, \
                    attributes = elt
            else:
                raise PythonDialogBug(
                    "unexpected length for 'elt': {0} (expected 8 or 9); "
                    "elt = {1!r}".format(len(elt), elt))

            for name, value in (("LABEL", label), ("ITEM", item)):
                if not isinstance(value, str):
                    raise BadPythonDialogUsage(
                        "Dialog.{0}: {1} element not a string: {2!r}".format(
                            method_name, name, value))

            cmd.extend((label, str(yl), str(xl), item, str(yi), str(xi),
                        str(field_length), str(input_length)))
            if len(elt) == 9:
                cmd.append(str(attributes))

        (code, output) = self._perform(cmd, **kwargs)

        return (code, output.split('\n')[:-1])

    def form(self, text, elements, height=0, width=0, form_height=0, **kwargs):
        """Display a form consisting of labels and fields.

        text        -- text to display in the box
        elements    -- sequence describing the labels and fields (see
                       below)
        height      -- height of the box
        width       -- width of the box
        form_height -- number of form lines displayed at the same time

        A form box consists in a series of fields and associated
        labels. This type of dialog is suitable for adjusting
        configuration parameters and similar tasks.

        Each element of 'elements' must itself be a sequence
        (LABEL, YL, XL, ITEM, YI, XI, FIELD_LENGTH, INPUT_LENGTH)
        containing the various parameters concerning a given field
        and the associated label.

        LABEL is a string that will be displayed at row YL, column
        XL. ITEM is a string giving the initial value for the field,
        which will be displayed at row YI, column XI (row and column
        numbers starting from 1).

        FIELD_LENGTH and INPUT_LENGTH are integers that respectively
        specify the number of characters used for displaying the
        field and the maximum number of characters that can be
        entered for this field. These two integers also determine
        whether the contents of the field can be modified, as
        follows:

          - if FIELD_LENGTH is zero, the field cannot be altered and
            its contents determines the displayed length;

          - if FIELD_LENGTH is negative, the field cannot be altered
            and the opposite of FIELD_LENGTH gives the displayed
            length;

          - if INPUT_LENGTH is zero, it is set to FIELD_LENGTH.

        Return a tuple of the form (code, list) where 'code' is the
        exit status (an integer) of the dialog-like program and
        'list' gives the contents of every editable field on exit,
        with the same order as in 'elements'.

        Notable exceptions:

            BadPythonDialogUsage
            any exception raised by self._perform()

        """
        return self._generic_form("form", "form", text, elements,
                                  height, width, form_height, **kwargs)

    def passwordform(self, text, elements, height=0, width=0, form_height=0,
                     **kwargs):
        """Display a form consisting of labels and invisible fields.

        This widget is identical to the form box, except that all
        text fields are treated as passwordbox widgets rather than
        inputbox widgets.

        By default (as in dialog), nothing is echoed to the terminal
        as the user types in the invisible fields. This can be
        confusing to users. Use the 'insecure' keyword argument if
        you want an asterisk to be echoed for each character entered
        by the user.

        Notable exceptions:

            BadPythonDialogUsage
            any exception raised by self._perform()

        """
        return self._generic_form("passwordform", "passwordform", text,
                                  elements, height, width, form_height,
                                  **kwargs)

    def mixedform(self, text, elements, height=0, width=0, form_height=0,
                  **kwargs):
        """Display a form consisting of labels and fields.

        text        -- text to display in the box
        elements    -- sequence describing the labels and fields (see
                       below)
        height      -- height of the box
        width       -- width of the box
        form_height -- number of form lines displayed at the same time

        A mixedform box is very similar to a form box, and differs
        from the latter by allowing field attributes to be specified.

        Each element of 'elements' must itself be a sequence (LABEL,
        YL, XL, ITEM, YI, XI, FIELD_LENGTH, INPUT_LENGTH, ATTRIBUTES)
        containing the various parameters concerning a given field
        and the associated label.

        ATTRIBUTES is a bit mask with the following meaning:

          bit 0  -- the field should be hidden (e.g., a password)
          bit 1  -- the field should be read-only (e.g., a label)

        For all other parameters, please refer to the documentation
        of the form box.

        The return value is the same as would be with the form box,
        except that field marked as read-only with bit 1 of
        ATTRIBUTES are also included in the output list.

        Notable exceptions:

            BadPythonDialogUsage
            any exception raised by self._perform()

        """
        return self._generic_form("mixedform", "mixedform", text, elements,
                                  height, width, form_height, **kwargs)

    def dselect(self, filepath, height=0, width=0, **kwargs):
        """Display a directory selection dialog box.

        filepath -- initial path
        height   -- height of the box
        width    -- width of the box

        The directory-selection dialog displays a text-entry window
        in which you can type a directory, and above that a window
        with directory names.

        Here, filepath can be a filepath in which case the directory
        window will display the contents of the path and the
        text-entry window will contain the preselected directory.

        Use tab or arrow keys to move between the windows. Within the
        directory window, use the up/down arrow keys to scroll the
        current selection. Use the space-bar to copy the current
        selection into the text-entry window.

        Typing any printable characters switches focus to the
        text-entry window, entering that character as well as
        scrolling the directory window to the closest match.

        Use a carriage return or the "OK" button to accept the
        current value in the text-entry window and exit.

        Return a tuple of the form (code, path) where 'code' is the
        exit status (an integer) of the dialog-like program and
        'path' is the directory chosen by the user.

        Notable exceptions:

            any exception raised by self._perform()

        """
        (code, output) = self._perform(
            ["--dselect", filepath, str(height), str(width)],
            **kwargs)

        return (code, output)

    def editbox(self, filepath, height=0, width=0, **kwargs):
        """Display a basic text editor dialog box.

        filepath -- file which determines the initial contents of
                    the dialog box
        height   -- height of the box
        width    -- width of the box

        The editbox dialog displays a copy of the file contents. You
        may edit it using the Backspace, Delete and cursor keys to
        correct typing errors. It also recognizes Page Up and Page
        Down. Unlike the inputbox, you must tab to the "OK" or
        "Cancel" buttons to close the dialog. Pressing the "Enter"
        key within the box will split the corresponding line.

        Return a tuple of the form (code, text) where 'code' is the
        exit status (an integer) of the dialog-like program and
        'text' is the contents of the text entry window on exit.

        Notable exceptions:

            any exception raised by self._perform()

        """
        (code, output) = self._perform(
            ["--editbox", filepath, str(height), str(width)],
            **kwargs)

        return (code, output)

    def fselect(self, filepath, height=0, width=0, **kwargs):
        """Display a file selection dialog box.

        filepath -- initial file path
        height   -- height of the box
        width    -- width of the box

        The file-selection dialog displays a text-entry window in
        which you can type a filename (or directory), and above that
        two windows with directory names and filenames.

        Here, filepath can be a file path in which case the file and
        directory windows will display the contents of the path and
        the text-entry window will contain the preselected filename.

        Use tab or arrow keys to move between the windows. Within the
        directory or filename windows, use the up/down arrow keys to
        scroll the current selection. Use the space-bar to copy the
        current selection into the text-entry window.

        Typing any printable character switches focus to the
        text-entry window, entering that character as well as
        scrolling the directory and filename windows to the closest
        match.

        Use a carriage return or the "OK" button to accept the
        current value in the text-entry window, or the "Cancel"
        button to cancel.

        Return a tuple of the form (code, path) where 'code' is the
        exit status (an integer) of the dialog-like program and
        'path' is the path chosen by the user (the last element of
        which may be a directory or a file).

        Notable exceptions:

            any exception raised by self._perform()

        """
        (code, output) = self._perform(
            ["--fselect", filepath, str(height), str(width)],
            **kwargs)

        output = self._strip_xdialog_newline(output)

        return (code, output)

    def gauge_start(self, text="", height=8, width=54, percent=0, **kwargs):
        """Display gauge box.

        text    -- text to display in the box
        height  -- height of the box
        width   -- width of the box
        percent -- initial percentage shown in the meter

        A gauge box displays a meter along the bottom of the box. The
        meter indicates a percentage.

        This function starts the dialog-like program telling it to
        display a gauge box with a text in it and an initial
        percentage in the meter.

        Return value: undefined.


        Gauge typical usage
        -------------------

        Gauge typical usage (assuming that 'd' is an instance of the
        Dialog class) looks like this:
            d.gauge_start()
            # do something
            d.gauge_update(10)       # 10% of the whole task is done
            # ...
            d.gauge_update(100, "any text here") # work is done
            exit_code = d.gauge_stop()           # cleanup actions


        Notable exceptions:
            - any exception raised by self._call_program()
            - PythonDialogOSError

        """
        with OSErrorHandling():
            # We need a pipe to send data to the child (dialog) process's
            # stdin while it is running.
            # rfd = File Descriptor for Reading
            # wfd = File Descriptor for Writing
            (child_stdin_rfd, child_stdin_wfd)  = os.pipe()

            (child_pid, child_output_rfd) = self._call_program(
                ["--gauge", text, str(height), str(width), str(percent)],
                redir_child_stdin_from_fd=child_stdin_rfd,
                close_fds=(child_stdin_wfd,), **kwargs)

            # fork() is done. We don't need child_stdin_rfd in the father
            # process anymore.
            os.close(child_stdin_rfd)

            self._gauge_process = {
                "pid": child_pid,
                "stdin": os.fdopen(child_stdin_wfd, "w"),
                "child_output_rfd": child_output_rfd
                }

    def gauge_update(self, percent, text="", update_text=False):
        """Update a running gauge box.

        percent     -- new percentage (integer) to show in the gauge
                       meter
        text        -- new text to optionally display in the box
        update_text -- boolean indicating whether to update the
                       text in the box

        This function updates the percentage shown by the meter of a
        running gauge box (meaning 'gauge_start' must have been
        called previously). If update_text is True, the text
        displayed in the box is also updated.

        See the 'gauge_start' function's documentation for
        information about how to use a gauge.

        Return value: undefined.

        Notable exception: PythonDialogIOError (PythonDialogOSError
                           from Python 3.3 onwards) can be raised if
                           there is an I/O error while writing to the
                           pipe used to talk to the dialog-like
                           program.

        """
        if not isinstance(percent, int):
            raise BadPythonDialogUsage(
                "the 'percent' argument of gauge_update() must be an integer, "
                "but {0!r} is not".format(percent))

        if update_text:
            gauge_data = "XXX\n{0}\n{1}\nXXX\n".format(percent, text)
        else:
            gauge_data = "{0}\n".format(percent)
        with OSErrorHandling():
            self._gauge_process["stdin"].write(gauge_data)
            self._gauge_process["stdin"].flush()

    # For "compatibility" with the old dialog.py...
    def gauge_iterate(*args, **kwargs):
        warnings.warn("Dialog.gauge_iterate() has been obsolete for "
                      "many years", DeprecationWarning)
        gauge_update(*args, **kwargs)

    def gauge_stop(self):
        """Terminate a running gauge widget.

        This function performs the appropriate cleanup actions to
        terminate a running gauge (started with 'gauge_start').

        See the 'gauge_start' function's documentation for
        information about how to use a gauge.

        Return value: undefined.

        Notable exceptions:
            - any exception raised by
              self._wait_for_program_termination()
            - PythonDialogIOError (PythonDialogOSError from
              Python 3.3 onwards) can be raised if closing the pipe
              used to talk to the dialog-like program fails.

        """
        p = self._gauge_process
        # Close the pipe that we are using to feed dialog's stdin
        with OSErrorHandling():
            p["stdin"].close()
        exit_code = \
                  self._wait_for_program_termination(p["pid"],
                                                     p["child_output_rfd"])[0]
        return exit_code

    def infobox(self, text, height=10, width=30, **kwargs):
        """Display an information dialog box.

        text   -- text to display in the box
        height -- height of the box
        width  -- width of the box

        An info box is basically a message box. However, in this
        case, dialog will exit immediately after displaying the
        message to the user. The screen is not cleared when dialog
        exits, so that the message will remain on the screen until
        the calling shell script clears it later. This is useful
        when you want to inform the user that some operations are
        carrying on that may require some time to finish.

        Return the exit status (an integer) of the dialog-like
        program.

        Notable exceptions:

            any exception raised by self._perform()

        """
        return self._perform(
            ["--infobox", text, str(height), str(width)],
            **kwargs)[0]

    def inputbox(self, text, height=10, width=30, init='', **kwargs):
        """Display an input dialog box.

        text   -- text to display in the box
        height -- height of the box
        width  -- width of the box
        init   -- default input string

        An input box is useful when you want to ask questions that
        require the user to input a string as the answer. If init is
        supplied it is used to initialize the input string. When
        entering the string, the BACKSPACE key can be used to
        correct typing errors. If the input string is longer than
        can fit in the dialog box, the input field will be scrolled.

        Return a tuple of the form (code, string) where 'code' is the
        exit status of the dialog-like program and 'string' is the
        string entered by the user.

        Notable exceptions:

            any exception raised by self._perform()

        """
        (code, string_) = self._perform(
            ["--inputbox", text, str(height), str(width), init],
            **kwargs)

        string_ = self._strip_xdialog_newline(string_)

        return (code, string_)

    def inputmenu(self, text, height=0, width=60, menu_height=7, choices=[],
             **kwargs):
        """Display an inputmenu dialog box.

        text        -- text to display in the box
        height      -- height of the box
        width       -- width of the box
        menu_height -- height of the menu (scrollable part)
        choices     -- a sequence of (tag, item) tuples, the meaning
                       of which is explained below


        Overview
        --------

        An inputmenu box is a dialog box that can be used to present
        a list of choices in the form of a menu for the user to
        choose. Choices are displayed in the order given. The main
        differences with the menu dialog box are:

          * entries are not automatically centered, but
            left-adjusted;

          * the current entry can be renamed by pressing the Rename
            button, which allows editing the 'item' part of the
            current entry.

        Each menu entry consists of a 'tag' string and an 'item'
        string. The tag gives the entry a name to distinguish it from
        the other entries in the menu and to provide quick keyboard
        access. The item is a short description of the option that
        the entry represents.

        The user can move between the menu entries by pressing the
        UP/DOWN keys or the first letter of the tag as a hot key.
        There are 'menu_height' lines (not entries!) displayed in the
        scrollable part of the menu at one time.

        BEWARE!

          It is strongly advised not to put any space in tags,
          otherwise the dialog output can be ambiguous if the
          corresponding entry is renamed, causing pythondialog to
          return a wrong tag string and new item text.

          The reason is that in this case, the dialog output is
          "RENAMED <tag> <item>" (without angle brackets) and
          pythondialog cannot guess whether spaces after the
          "RENAMED " prefix belong to the <tag> or the new <item>
          text.


        Return value
        ------------

        Return a tuple of the form (exit_info, tag, new_item_text)
        where:

        'exit_info' is either:
          - the string "accepted", meaning that an entry was accepted
            without renaming;
          - the string "renamed", meaning that an entry was accepted
            after being renamed;
          - an integer, being the exit status of the dialog-like
            program.

        'tag' indicates which entry was accepted (with or without
        renaming), if any. If no entry was accepted (e.g., if the
        dialog was exited with the Cancel button), then 'tag' is
        None.

        'new_item_text' gives the new 'item' part of the renamed
        entry if 'exit_info' is "renamed", otherwise it is None.

        Notable exceptions:

            any exception raised by self._perform()

        """
        cmd = ["--inputmenu", text, str(height), str(width), str(menu_height)]
        for t in choices:
            cmd.extend(t)
        (code, output) = self._perform(cmd, **kwargs)

        if code == self.DIALOG_OK:
            return ("accepted", output, None)
        elif code == self.DIALOG_EXTRA:
            if not output.startswith("RENAMED "):
                raise PythonDialogBug(
                    "'output' does not start with 'RENAMED ': {0!r}".format(
                        output))
            t = output.split(' ', 2)
            return ("renamed", t[1], t[2])
        else:
            return (code, None, None)

    def menu(self, text, height=15, width=54, menu_height=7, choices=[],
             **kwargs):
        """Display a menu dialog box.

        text        -- text to display in the box
        height      -- height of the box
        width       -- width of the box
        menu_height -- number of entries displayed in the box (which
                       can be scrolled) at a given time
        choices     -- a sequence of (tag, item) or (tag, item, help)
                       tuples (the meaning of each 'tag', 'item' and
                       'help' is explained below)


        Overview
        --------

        As its name suggests, a menu box is a dialog box that can be
        used to present a list of choices in the form of a menu for
        the user to choose. Choices are displayed in the order given.

        Each menu entry consists of a 'tag' string and an 'item'
        string. The tag gives the entry a name to distinguish it from
        the other entries in the menu and to provide quick keyboard
        access. The item is a short description of the option that
        the entry represents.

        The user can move between the menu entries by pressing the
        UP/DOWN keys, the first letter of the tag as a hot key, or
        the number keys 1-9. There are 'menu_height' entries
        displayed in the menu at one time, but the menu will be
        scrolled if there are more entries than that.


        Providing on-line help facilities
        ---------------------------------

        If this function is called with item_help=True (keyword
        argument), the option --item-help is passed to dialog and the
        tuples contained in 'choices' must contain 3 elements each:
        (tag, item, help). The help string for the highlighted item
        is displayed in the bottom line of the screen and updated as
        the user highlights other items.

        If item_help=False or if this keyword argument is not passed
        to this function, the tuples contained in 'choices' must
        contain 2 elements each: (tag, item).

        If this function is called with help_button=True, it must also
        be called with item_help=True (this is a limitation of dialog),
        therefore the tuples contained in 'choices' must contain 3
        elements each as explained in the previous paragraphs. This
        will cause a Help button to be added to the right of the
        Cancel button (by passing --help-button to dialog).


        Return value
        ------------

        Return a tuple of the form (exit_info, string).

        'exit_info' is either:
          - an integer, being the exit status of the dialog-like
            program
          - or the string "help", meaning that help_button=True was
            passed and that the user chose the Help button instead of
            OK or Cancel.

        The meaning of 'string' depends on the value of exit_info:
          - if 'exit_info' is 0, 'string' is the tag chosen by the
            user
          - if 'exit_info' is "help", 'string' is the 'help' string
            from the 'choices' argument corresponding to the item
            that was highlighted when the user chose the Help button
          - otherwise (the user chose Cancel or pressed Esc, or there
            was a dialog error), the value of 'string' is undefined.

        Notable exceptions:

            any exception raised by self._perform()

        """
        cmd = ["--menu", text, str(height), str(width), str(menu_height)]
        for t in choices:
            cmd.extend(t)
        (code, output) = self._perform(cmd, **kwargs)

        output = self._strip_xdialog_newline(output)

        if kwargs.get("help_button", False) and output.startswith("HELP "):
            return ("help", output[5:])
        else:
            return (code, output)

    def mixedgauge(self, text, height=0, width=0, percent=0, elements=[],
             **kwargs):
        """Display a mixed gauge dialog box.

        text        -- text to display in the middle of the box,
                       between the elements list and the progress bar
        height      -- height of the box
        width       -- width of the box
        percent     -- integer giving the percentage for the global
                       progress bar
        elements    -- a sequence of (tag, item) tuples, the meaning
                       of which is explained below

        A mixedgauge box displays a list of "elements" with status
        indication for each of them, followed by a text and finally a
        (global) progress bar along the bottom of the box.

        The top part ('elements') is suitable for displaying a task
        list. One element is displayed per line, with its 'tag' part
        on the left and its 'item' part on the right. The 'item' part
        is a string that is displayed on the right of the same line.

        The 'item' of an element can be an arbitrary string, but
        special values listed in the dialog(3) manual page translate
        into a status indication for the corresponding task ('tag'),
        such as: "Succeeded", "Failed", "Passed", "Completed", "Done",
        "Skipped", "In Progress", "Checked", "N/A" or a progress
        bar.

        A progress bar for an element is obtained by supplying a
        negative number for the 'item'. For instance, "-75" will
        cause a progress bar indicating 75 %% to be displayed on the
        corresponding line.

        For your convenience, if an 'item' appears to be an integer
        or a float, it will be converted to a string before being
        passed to the dialog-like program.

        'text' is shown as a sort of caption between the list and the
        global progress bar. The latter displays 'percent' as the
        percentage of completion.

        Contrary to the gauge widget, mixedgauge is completely
        static. You have to call mixedgauge() several times in order
        to display different percentages in the global progress bar,
        or status indicators for a given task.

        Return the exit status (an integer) of the dialog-like
        program.

        Notable exceptions:

            any exception raised by self._perform()

        """
        cmd = ["--mixedgauge", text, str(height), str(width), str(percent)]
        for t in elements:
            cmd.extend( (t[0], str(t[1])) )
        return self._perform(cmd, **kwargs)[0]

    def msgbox(self, text, height=10, width=30, **kwargs):
        """Display a message dialog box, with scrolling and line wrapping.

        text   -- text to display in the box
        height -- height of the box
        width  -- width of the box

        Display a text in a message box, with a scrollbar and
        percentage indication if the text is too long to fit in a
        single "screen".

        A message box is very similar to a yes/no box. The only
        difference between a message box and a yes/no box is that a
        message box has only a single OK button. You can use this
        dialog box to display any message you like. After reading
        the message, the user can press the Enter key so that dialog
        will exit and the calling program can continue its
        operation.

        msgbox() performs automatic line wrapping. If you want to
        force a newline at some point, simply insert it in 'text'. In
        other words (with the default settings), newline characters
        in 'text' *are* respected; the line wrapping process
        performed by dialog only inserts *additional* newlines when
        needed. If you want no automatic line wrapping, consider
        using scrollbox().

        Return the exit status (an integer) of the dialog-like
        program.

        Notable exceptions:

            any exception raised by self._perform()

        """
        return self._perform(
            ["--msgbox", text, str(height), str(width)],
            **kwargs)[0]

    def pause(self, text, height=15, width=60, seconds=5, **kwargs):
        """Display a pause dialog box.

        text       -- text to display in the box
        height     -- height of the box
        width      -- width of the box
        seconds    -- number of seconds to pause for (integer)

        A pause box displays a text and a meter along the bottom of
        the box, during a specified amount of time ('seconds'). The
        meter indicates how many seconds remain until the end of the
        pause. The widget exits when the specified number of seconds
        is elapsed, or immediately if the user presses the OK button,
        the Cancel button or the Esc key.

        Return the exit status (an integer) of the dialog-like
        program, which is DIALOG_OK if the pause ended automatically
        after 'seconds' seconds, or if the user pressed the OK button.

        Notable exceptions:

            any exception raised by self._perform()

        """
        return self._perform(
            ["--pause", text, str(height), str(width), str(seconds)],
            **kwargs)[0]

    def passwordbox(self, text, height=10, width=60, init='', **kwargs):
        """Display an password input dialog box.

        text   -- text to display in the box
        height -- height of the box
        width  -- width of the box
        init   -- default input password

        A password box is similar to an input box, except that the
        text the user enters is not displayed. This is useful when
        prompting for passwords or other sensitive information. Be
        aware that if anything is passed in "init", it will be
        visible in the system's process table to casual snoopers.
        Also, it is very confusing to the user to provide them with a
        default password they cannot see. For these reasons, using
        "init" is highly discouraged.

        By default (as in dialog), nothing is echoed to the terminal
        as the user enters the sensitive text. This can be confusing
        to users. Use the 'insecure' keyword argument if you want an
        asterisk to be echoed for each character entered by the user.

        Return a tuple of the form (code, password) where 'code' is
        the exit status of the dialog-like program and 'password' is
        the password entered by the user.

        Notable exceptions:

            any exception raised by self._perform()

        """
        (code, password) = self._perform(
            ["--passwordbox", text, str(height), str(width), init],
            **kwargs)

        password = self._strip_xdialog_newline(password)

        return (code, password)

    def _progressboxoid(self, widget, file_path=None, file_flags=os.O_RDONLY,
                        fd=None, text=None, height=20, width=78, **kwargs):
        if (file_path is None and fd is None) or \
                (file_path is not None and fd is not None):
            raise BadPythonDialogUsage(
                "{0}.{1}.{2}: either 'file_path' or 'fd' must be provided, and "
                "not both at the same time".format(
                    __name__, self.__class__.__name__, widget))

        with OSErrorHandling():
            if file_path is not None:
                if fd is not None:
                    raise PythonDialogBug(
                        "unexpected non-None value for 'fd': {0!r}".format(fd))
                # No need to pass 'mode', as the file is not going to be
                # created here.
                fd = os.open(file_path, file_flags)

            try:
                args = [ "--{0}".format(widget) ]
                if text is not None:
                    args.append(text)
                args.extend([str(height), str(width)])

                code = self._perform(args, redir_child_stdin_from_fd=fd,
                                     **kwargs)[0]
            finally:
                with OSErrorHandling():
                    if file_path is not None:
                        # We open()ed file_path ourselves, let's close it now.
                        os.close(fd)

        return code

    def progressbox(self, file_path=None, file_flags=os.O_RDONLY,
                    fd=None, text=None, height=20, width=78, **kwargs):
        """Display a possibly growing stream in a dialog box, as with "tail -f".

          file_path  -- path to the file that is going to be displayed
          file_flags -- flags used when opening 'file_path'; those
                        are passed to os.open() function (not the
                        built-in open function!). By default, only
                        one flag is used: os.O_RDONLY.

        OR, ALTERNATIVELY:

          fd       -- file descriptor for the stream to be displayed

        text     -- caption continuously displayed at the top, above the
                    stream text, or None to disable the caption
        height   -- height of the box
        width    -- width of the box

        Display the contents of the specified file, updating the
        dialog box whenever the file grows, as with the "tail -f"
        command.

        The file can be specified in two ways:
          - either by giving its path (and optionally os.open()
            flags) with parameters 'file_path' and 'file_flags';
          - or by passing its file descriptor with parameter 'fd' (in
            which case it may not even be a file; for instance, it
            could be an anonymous pipe created with os.pipe()).

        Return the exit status (an integer) of the dialog-like
        program.

        Notable exceptions:

            PythonDialogIOError    if the Python version is < 3.3
            PythonDialogOSError
            any exception raised by self._perform()

        """
        return self._progressboxoid(
            "progressbox", file_path=file_path, file_flags=file_flags,
            fd=fd, text=text, height=height, width=width, **kwargs)

    def programbox(self, file_path=None, file_flags=os.O_RDONLY,
                   fd=None, text=None, height=20, width=78, **kwargs):
        """Display a possibly growing stream in a dialog box, as with "tail -f".

        A programbox is very similar to a progressbox. The only
        difference between a program box and a progress box is that a
        program box displays an OK button, but only after the input
        stream has been exhausted (i.e., End Of File has been
        reached).

        This dialog box can be used to display the piped output of an
        external program. After the program completes, the user can
        press the Enter key to close the dialog and resume execution
        of the calling program.

        The parameters and exceptions are the same as for
        'progressbox'. Please refer to the corresponding
        documentation.

        This widget requires dialog >= 1.1 (2011-03-02).

        """
        return self._progressboxoid(
            "programbox", file_path=file_path, file_flags=file_flags,
            fd=fd, text=text, height=height, width=width, **kwargs)

    def radiolist(self, text, height=15, width=54, list_height=7,
                  choices=[], **kwargs):
        """Display a radiolist box.

        text        -- text to display in the box
        height      -- height of the box
        width       -- width of the box
        list_height -- number of entries displayed in the box (which
                       can be scrolled) at a given time
        choices     -- a list of tuples (tag, item, status) where
                       'status' specifies the initial on/off state of
                       each entry; can be True or False, 1 or 0, "on"
                       or "off" (True and 1 meaning "on"), or any case
                       variation of these two strings. No more than
                       one entry should be set to True.

        A radiolist box is similar to a menu box. The main difference
        is that you can indicate which entry is initially selected,
        by setting its status to True.

        Return a tuple of the form (code, tag) with the tag for the
        entry that was chosen by the user. 'code' is the exit status
        of the dialog-like program.

        If the user exits with ESC or CANCEL, or if all entries were
        initially set to False and not altered before the user chose
        OK, the returned tag is the empty string.

        Notable exceptions:

            any exception raised by self._perform() or _to_onoff()

        """
        cmd = ["--radiolist", text, str(height), str(width), str(list_height)]
        for t in choices:
            cmd.extend((t[0], t[1], _to_onoff(t[2])))
        (code, tag) = self._perform(cmd, **kwargs)

        tag = self._strip_xdialog_newline(tag)

        return (code, tag)

    def rangebox(self, text, height=0, width=0, min=None, max=None, init=None,
                 **kwargs):
        """Display an range dialog box.

        text   -- text to display above the actual range control
        height -- height of the box
        width  -- width of the box
        min    -- minimum value for the range control
        max    -- maximum value for the range control
        init   -- initial value for the range control

        The rangebox dialog allows the user to select from a range of
        values using a kind of slider. The range control shows the
        current value as a bar (like the gauge dialog).

        The return value is a tuple of the form (code, val) where
        'code' is the exit status of the dialog-like program, and
        'val' is an integer: the value chosen by the user.

        The Tab and arrow keys move the cursor between the buttons
        and the range control. When the cursor is on the latter, you
        can change the value with the following keys:

          Left/Right arrows   select a digit to modify

          +/-                 increment/decrement the selected digit
                              by one unit

          0-9                 set the selected digit to the given
                              value

        Some keys are also recognized in all cursor positions:

          Home/End            set the value to its minimum or maximum

          PageUp/PageDown     decrement/increment the value so that
                              the slider moves by one column

        This widget requires dialog >= 1.2 (2012-12-30).

        Notable exceptions:

            any exception raised by self._perform()

        """
        for name in ("min", "max", "init"):
            if not isinstance(locals()[name], int):
                raise BadPythonDialogUsage(
                    "{0!r} argument not an int: {1!r}".format(name,
                                                              locals()[name]))
        (code, value) = self._perform(
            ["--rangebox", text] + [ str(i) for i in
                                     (height, width, min, max, init) ],
            **kwargs)

        if code == self.DIALOG_OK:
            return (code, int(value))
        else:
            return (code, None)

    def scrollbox(self, text, height=20, width=78, **kwargs):
        """Display a string in a scrollable box, with no line wrapping.

        text   -- string to display in the box
        height -- height of the box
        width  -- width of the box

        This method is a layer on top of textbox. The textbox widget
        in dialog allows to display file contents only. This method
        allows you to display any text in a scrollable box. This is
        simply done by creating a temporary file, calling textbox() and
        deleting the temporary file afterwards.

        The text is not automatically wrapped. New lines in the
        scrollable box will be placed exactly as in 'text'. If you
        want automatic line wrapping, you should use the msgbox
        widget instead (the 'textwrap' module from the Python
        standard library is also worth knowing about).

        Return the dialog-like program's exit status.

        Notable exceptions:
            - UnableToCreateTemporaryDirectory
            - PythonDialogIOError    if the Python version is < 3.3
            - PythonDialogOSError
            - exceptions raised by the tempfile module (which are
              unfortunately not mentioned in its documentation, at
              least in Python 2.3.3...)

        """
        # In Python < 2.3, the standard library does not have
        # tempfile.mkstemp(), and unfortunately, tempfile.mktemp() is
        # insecure. So, I create a non-world-writable temporary directory and
        # store the temporary file in this directory.
        with OSErrorHandling():
            tmp_dir = _create_temporary_directory()
            fName = os.path.join(tmp_dir, "text")
            # If we are here, tmp_dir *is* created (no exception was raised),
            # so chances are great that os.rmdir(tmp_dir) will succeed (as
            # long as tmp_dir is empty).
            #
            # Don't move the _create_temporary_directory() call inside the
            # following try statement, otherwise the user will always see a
            # PythonDialogOSError instead of an
            # UnableToCreateTemporaryDirectory because whenever
            # UnableToCreateTemporaryDirectory is raised, the subsequent
            # os.rmdir(tmp_dir) is bound to fail.
            try:
                # No race condition as with the deprecated tempfile.mktemp()
                # since tmp_dir is not world-writable.
                with open(fName, mode="w") as f:
                    f.write(text)

                # Ask for an empty title unless otherwise specified
                if kwargs.get("title", None) is None:
                    kwargs["title"] = ""

                return self._perform(
                    ["--textbox", fName, str(height), str(width)],
                    **kwargs)[0]
            finally:
                if os.path.exists(fName):
                    os.unlink(fName)
                os.rmdir(tmp_dir)

    def tailbox(self, filename, height=20, width=60, **kwargs):
        """Display the contents of a file in a dialog box, as with "tail -f".

        filename -- name of the file, the contents of which is to be
                    displayed in the box
        height   -- height of the box
        width    -- width of the box

        Display the contents of the specified file, updating the
        dialog box whenever the file grows, as with the "tail -f"
        command.

        Return the exit status (an integer) of the dialog-like
        program.

        Notable exceptions:

            any exception raised by self._perform()

        """
        return self._perform(
            ["--tailbox", filename, str(height), str(width)],
            **kwargs)[0]
    # No tailboxbg widget, at least for now.

    def textbox(self, filename, height=20, width=60, **kwargs):
        """Display the contents of a file in a dialog box.

        filename -- name of the file whose contents is to be
                    displayed in the box
        height   -- height of the box
        width    -- width of the box

        A text box lets you display the contents of a text file in a
        dialog box. It is like a simple text file viewer. The user
        can move through the file by using the UP/DOWN, PGUP/PGDN
        and HOME/END keys available on most keyboards. If the lines
        are too long to be displayed in the box, the LEFT/RIGHT keys
        can be used to scroll the text region horizontally. For more
        convenience, forward and backward searching functions are
        also provided.

        Return the exit status (an integer) of the dialog-like
        program.

        Notable exceptions:

            any exception raised by self._perform()

        """
        # This is for backward compatibility... not that it is
        # stupid, but I prefer explicit programming.
        if kwargs.get("title", None) is None:
            kwargs["title"] = filename
        return self._perform(
            ["--textbox", filename, str(height), str(width)],
            **kwargs)[0]

    def timebox(self, text, height=3, width=30, hour=-1, minute=-1,
                second=-1, **kwargs):
        """Display a time dialog box.

        text   -- text to display in the box
        height -- height of the box
        width  -- width of the box
        hour   -- inititial hour selected
        minute -- inititial minute selected
        second -- inititial second selected

        A dialog is displayed which allows you to select hour, minute
        and second. If the values for hour, minute or second are
        negative (or not explicitely provided, as they default to
        -1), the current time's corresponding values are used. You
        can increment or decrement any of those using the left-, up-,
        right- and down-arrows. Use tab or backtab to move between
        windows.

        Return a tuple of the form (code, time) where 'code' is the
        exit status (an integer) of the dialog-like program and
        'time' is a list of the form [hour, minute, second] (where
        'hour', 'minute' and 'second' are integers corresponding to
        the time chosen by the user) if the box was closed with OK,
        or None if it was closed with the Cancel button.

        Notable exceptions:
            - any exception raised by self._perform()
            - PythonDialogReModuleError
            - UnexpectedDialogOutput

        """
        (code, output) = self._perform(
            ["--timebox", text, str(height), str(width),
               str(hour), str(minute), str(second)],
            **kwargs)
        if code == self.DIALOG_OK:
            try:
                mo = _timebox_time_rec.match(output)
                if mo is None:
                    raise UnexpectedDialogOutput(
                        "the dialog-like program returned the following "
                        "unexpected time with the --timebox option: %s" % output)
                time = [ int(s) for s in mo.group("hour", "minute", "second") ]
            except re.error as e:
                raise PythonDialogReModuleError(str(e)) from e
        else:
            time = None
        return (code, time)

    def treeview(self, text, height=0, width=0, list_height=0,
                 nodes=[], **kwargs):
        """Display a treeview box.

        text        -- text to display at the top of the box
        height      -- height of the box
        width       -- width of the box
        list_height -- number of lines reserved for the main part of
                       the box, where the tree is displayed
        nodes       -- a list of (tag, item, status, depth) tuples
                       describing nodes, where:
                         - 'tag' is used to indicate which node was
                           selected by the user on exit;
                         - 'item' is the text displayed for the node;
                         - 'status' specifies the initial on/off
                           state of each node; can be True or False,
                           1 or 0, "on" or "off" (True, 1 and "on"
                           meaning selected), or any case variation
                           of these two strings;
                         - 'depth' is a non-negative integer
                           indicating the depth of the node in the
                           tree (0 for the root node).

        Display nodes organized in a tree structure. Each node has a
        tag, an 'item' text, a selected status, and a depth in the
        tree. Only the 'item' texts are displayed in the widget; tags
        are only used for the return value. Only one node can be
        selected at a given time, as for the radiolist widget.

        Return a tuple of the form (code, tag) where:
          - 'tag' is the tag of the selected node when the user chose
            OK, or None if Cancel was pressed instead;
          - 'code' is the exit status of the dialog-like program.

        Notable exceptions:

            any exception raised by self._perform() or _to_onoff()

        """
        cmd = ["--treeview", text, str(height), str(width), str(list_height)]

        nselected = 0
        for i, t in enumerate(nodes):
            if not isinstance(t[3], int):
                raise BadPythonDialogUsage(
                    "fourth element of node {0} not an int: {1!r}".format(
                        i, t[3]))

            status = _to_onoff(t[2])
            if status == "on":
                nselected += 1

            cmd.extend((t[0], t[1], status, str(t[3])))

        if nselected != 1:
            raise BadPythonDialogUsage(
                "exactly one node must be selected, not {0}".format(nselected))

        (code, output) = self._perform(cmd, **kwargs)

        if code == self.DIALOG_OK:
            return (code, output)
        else:
            return (code, None)

    def yesno(self, text, height=10, width=30, **kwargs):
        """Display a yes/no dialog box.

        text   -- text to display in the box
        height -- height of the box
        width  -- width of the box

        A yes/no dialog box of size 'height' rows by 'width' columns
        will be displayed. The string specified by 'text' is
        displayed inside the dialog box. If this string is too long
        to fit in one line, it will be automatically divided into
        multiple lines at appropriate places. The text string can
        also contain the sub-string "\\n" or newline characters to
        control line breaking explicitly. This dialog box is useful
        for asking questions that require the user to answer either
        yes or no. The dialog box has a Yes button and a No button,
        in which the user can switch between by pressing the TAB
        key.

        Return the exit status (an integer) of the dialog-like
        program.

        Notable exceptions:

            any exception raised by self._perform()

        """
        return self._perform(
            ["--yesno", text, str(height), str(width)],
            **kwargs)[0]
