# dialog.py --- A python interface to the Linux "dialog" utility
# Copyright (C) 2000, 2002 Robb Shecter, Sultanbek Tezadov,
#                          Florent Rougon
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Python interface to dialog-like programs.

This module provides a Python interface to dialog-like programs such
as `dialog' and `whiptail'.

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

This module can raise the following exceptions:

  PythonDialogBug
  BadPythonDialogUsage
  UnexpectedDialogOutput
  DialogTerminatedBySignal
  DialogError

"""

from __future__ import nested_scopes
import os, popen2, tempfile, string, re, types, commands


# Values accepted for checklists
_on_rec = re.compile(r"on", re.IGNORECASE)
_off_rec = re.compile(r"off", re.IGNORECASE)

_calendar_date_rec = re.compile(
    r"(?P<day>\d\d)/(?P<month>\d\d)/(?P<year>\d\d\d\d)$")
_timebox_time_rec = re.compile(
    r"(?P<hour>\d\d):(?P<minute>\d\d):(?P<second>\d\d)$")


# This dictionary allows us to write the dialog common options in a Pythonic
# way (e.g. dialog_instance.checklist(args, ..., title="Foo", no_shadow=1)).
_common_args_syntax = {
    "aspect": lambda ratio: ("--aspect", str(ratio)),
    "backtitle": lambda backtitle: ("--backtitle", backtitle),
    "beep": lambda enable: _simple_option("--beep", enable),
    "beep_after": lambda enable: _simple_option("--beep-after", enable),
    # Warning: order = y, x!
    "begin": lambda coords: ("--begin", str(coords[0]), str(coords[1])),
    "cancel": lambda string: ("--cancel-label", string),
    "clear": lambda enable: _simple_option("--clear", enable),
    "cr_wrap": lambda enable: _simple_option("--cr-wrap", enable),
    "create_rc": lambda file: ("--create-rc", file),
    "defaultno": lambda enable: _simple_option("--defaultno", enable),
    "default_item": lambda string: ("--default-item", "string"),
    "help": lambda enable: _simple_option("--help", enable),
    "help_button": lambda enable: _simple_option("--help-button", enable),
    "help_label": lambda string: ("--help-label", string),
    "ignore": lambda enable: _simple_option("--ignore", enable),
    "item_help": lambda enable: _simple_option("--item-help", enable),
    "max_input": lambda size: ("--max-input", str(size)),
    "no_kill": lambda enable: _simple_option("--no-kill", enable),
    "no_cancel": lambda enable: _simple_option("--no-cancel", enable),
    "nocancel": lambda enable: _simple_option("--nocancel", enable),
    "no_shadow": lambda enable: _simple_option("--no-shadow", enable),
    "ok_label": lambda string: ("--ok-label", string),
    "print_maxsize": lambda enable: _simple_option("--print-maxsize",
                                                   enable),
    "print_size": lambda enable: _simple_option("--print-size", enable),
    "print_version": lambda enable: _simple_option("--print-version",
                                                   enable),
    "separate_output": lambda enable: _simple_option("--separate-output",
                                                     enable),
    "separate_widget": lambda string: ("--separate-widget", string),
    "shadow": lambda enable: _simple_option("--shadow", enable),
    "size_err": lambda enable: _simple_option("--size-err", enable),
    "sleep": lambda secs: ("--sleep", str(secs)),
    "stderr": lambda enable: _simple_option("--stderr", enable),
    "stdout": lambda enable: _simple_option("--stdout", enable),
    "tab_correct": lambda enable: _simple_option("--tab-correct", enable),
    "tab_len": lambda n: ("--tab-len", str(n)),
    "timeout": lambda secs: ("--timeout", str(secs)),
    "title": lambda title: ("--title", title),
    "trim": lambda enable: _simple_option("--trim", enable),
    "version": lambda enable: _simple_option("--version", enable)}
    

def _simple_option(option, enable):
    """Turn on or off the simplest dialog Common Options."""
    if enable:
        return (option,)
    else:
        # This will not add any argument to the command line
        return ()


def _find_in_path(prog_name):
    """Search an executable in the PATH, like the exec*p functions do.

    If PATH is not defined, the default path ":/bin:/usr/bin" is
    used, as with the C library exec*p functions.

    Return the absolute file name or None if no readable and
    executable file is found.

    """
    PATH = os.getenv("PATH", ":/bin:/usr/bin") # see the execvp(3) man page
    for dir in string.split(PATH, ":"):
        full_path = os.path.join(dir, prog_name)
        if os.path.isfile(full_path) \
           and os.access(full_path, os.R_OK | os.X_OK):
            return full_path
    return None


def _to_onoff(val):
    """Convert boolean expressions to "on" or "off"

    This function converts every non-zero integer as well as "on",
    "ON", "On" and "oN" to "on" and converts 0, "off", "OFF", etc. to
    "off".

    """
    if type(val) == types.IntType:
        if val:
            return "on"
        else:
            return "off"
    elif type(val) == types.StringType:
        if _on_rec.match(val):
            return "on"
        elif _off_rec.match(val):
            return "off"
    else:
        raise BadPythonDialogUsage("invalid boolean value: %s" % val)


def _compute_common_args(dict):
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

    """
    args = []
    for key in dict.keys():
        args.extend(_common_args_syntax[key](dict[key]))
    return args


# Exceptions raised by this module
class PythonDialogException(Exception):
    """Generic pythondialog exception.

    This class is meant to be derived for each specific exception.

    """
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.message)
    def complete_message(self):
        return "%s: %s." % (self.ExceptionPrettyIdentifier, self.message)
    ExceptionPrettyIdentifier = "pythondialog generic exception"


class ExecutableNotFound(PythonDialogException):
    """Exception raised when the dialog executable can't be found."""
    ExceptionPrettyIdentifier = "Executable not found"

class PythonDialogBug(PythonDialogException):
    """Exception raised when pythondialog finds a bug in his own code."""
    ExceptionPrettyIdentifier = "Bug in pythondialog"

class BadPythonDialogUsage(PythonDialogException):
    """Exception raised when pythondialog is used in an incorrect way."""
    ExceptionPrettyIdentifier = "Invalid use of pythondialog"

class UnexpectedDialogOutput(PythonDialogException):
    """Exception raised when the dialog-like program returns something not \
expected by pythondialog."""
    ExceptionPrettyIdentifier = "Unexpected dialog output"

class DialogTerminatedBySignal(PythonDialogException):
    """Exception raised when the dialog-like program is terminated by a \
signal."""
    ExceptionPrettyIdentifier = "dialog-like terminated by a signal"

class DialogError(PythonDialogException):
    """Exception raised when the dialog-like program exits with the \
code indicating an error."""
    ExceptionPrettyIdentifier = "dialog-like terminated due to an error"


# Main class of the module
class Dialog:

    """Class providing bindings for dialog-compatible programs.

    This class allows you to invoke dialog or a compatible program in
    a pythonic way to build quicky and easily simple but nice text
    interfaces.

    An application typically creates one instance of the Dialog class
    and uses it for all its widgets, but it is possible to use
    concurrently several instances of this class with different
    parameters (such as the background title) if you have the need
    for this.

    The exit codes (exit status) returned by dialog are to be
    compared with the DIALOG_OK, DIALOG_CANCEL, DIALOG_ESC and
    DIALOG_ERROR attributes of each Dialog instance (they are
    integers).

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

    The Dialog class has the following methods:

    add_persistent_args
    calendar
    checklist
    fselect

    gauge_start
    gauge_update
    gauge_stop

    infobox
    inputbox
    menu
    msgbox
    passwordbox
    radiolist
    scrollbox
    tailbox
    textbox
    timebox
    yesno

    clear                 (obsolete)
    setBackgroundTitle    (obsolete)


    Passing dialog "Common Options"
    -------------------------------

    Every widget method has a **kwargs argument allowing you to pass
    dialog so-called Common Options (see the dialog(1) manual page)
    to dialog for this widget call. For instance, if `d' is a Dialog
    instance, you can write:

      d.checklist(args, ..., title="A Great Title", no_shadow=1)

    The no_shadow option is worth looking at:

      1. It is an option that takes no argument as far as dialog is
         concerned (unlike the "--title" option, for instance). When
         you list it as a keyword argument, the option is really
         passed to dialog only if the value you gave it evaluates to
         true, e.g. "no_shadow=1" will cause "--no-shadow" to be
         passed to dialog whereas "no_shadow=0" will cause this
         option not to be passed to dialog at all.

      2. It is an option that has a hyphen (-) in its name, which you
         must change into an underscore (_) to pass it as a Python
         keyword argument. Therefore, "--no-shadow" is passed by
         giving a "no_shadow=1" keyword argument to a Dialog method
         (the leading two dashes are also consistently removed).


    Exceptions
    ----------

    Don't forget about the exceptions listed in this module's
    docstring when using this class.

    """

    def __init__(self, dialog="dialog",
                 DIALOGRC="", DIALOG_OK=0, DIALOG_CANCEL=1, DIALOG_ESC=2,
                 DIALOG_ERROR=3):
        # Store the values given for the DIALOG* environment variables, or go
        # with the defaults. Note that I don't modify os.environ as this would
        # affect calling modules.
        # DIALOGRC differs from the other DIALOG* vars in that:
        #   1. It is a string
        #   2. We may very well want it to be unset
        if DIALOGRC:
            self.DIALOGRC = DIALOGRC

        self.DIALOG_OK     = DIALOG_OK
        self.DIALOG_CANCEL = DIALOG_CANCEL
        self.DIALOG_ESC    = DIALOG_ESC
        self.DIALOG_ERROR  = DIALOG_ERROR

        self._dialog_prg = _find_in_path(dialog) # Find the full pathname
        if self._dialog_prg is None:
            raise ExecutableNotFound(
                "can't find the dialog/whiptail/whatever executable")
        self.dialog_persistent_arglist = []

    def add_persistent_args(self, arglist):
        self.dialog_persistent_arglist.extend(arglist)

    # For compatibility with the old dialog...
    def setBackgroundTitle(self, text):
        """Set the background title for dialog.

        This method is obsolete. Please remove calls to it from your
        programs.

	"""
	self.add_persistent_args(("--backtitle", text))

    def _call_program(self, cmdargs, **kwargs):
	"""Do the actual work of invoking the dialog-like program.

        Return a Popen3 object just after dialog being invoked.

        """
        if hasattr(self, "DIALOGRC"):
            DIALOGRC_string = "DIALOGRC='%s'" % self.DIALOGRC
        else:
            DIALOGRC_string = ""

        # Convert our 4 lists of shell arguments to 1 string with all the
        # arguments correctly quoted for the Bourne shell (note: the first
        # character is a space)
        cmd_plus_args_str = string.join(map(commands.mkarg,
                                            [self._dialog_prg] +
                                            self.dialog_persistent_arglist +
                                            _compute_common_args(kwargs) +
                                            cmdargs), "")
	return popen2.Popen3("%s DIALOG_OK=%d DIALOG_CANCEL=%d DIALOG_ESC=%d "
                             "DIALOG_ERROR=%d%s"
                             % (DIALOGRC_string, self.DIALOG_OK,
                                self.DIALOG_CANCEL,
                                self.DIALOG_ESC, self.DIALOG_ERROR,
                                cmd_plus_args_str), 1)

    def _wait_for_program_termination(self, process):
        """Wait for a dialog-like process to terminate.

        This function waits for the specified process to terminate,
        raises the appropriate exceptions in case of abnormal
        termination and returns the exit status and standard error
        output of the process as a tuple: (exit_code, stderr_string).

        This function does not close the process standard input,
        error and output streams.

        `process' is expected to be a popen2.Popen3 object.

        Notable exceptions: DialogError is raised if the dialog-like
        program returns with the exit status self.DIALOG_ERROR.

        """
        exit_info = process.wait()
        if os.WIFEXITED(exit_info):
            exit_code = os.WEXITSTATUS(exit_info)
        # As we wait()ed for p to terminate, there is no need to call
        # os.WIFSTOPPED()
        elif os.WIFSIGNALED(exit_info):
            raise DialogTerminatedBySignal("the dialog-like program was "
                                           "terminated by a signal")
        else:
            raise PythonDialogBug("please report this bug to the "
                                  "pythondialog maintainers")
        if exit_code == self.DIALOG_ERROR:
            raise DialogError("the dialog-like program exited with "
                              "code %d" % exit_code)
        return (exit_code, process.childerr.read())

    def _perform(self, cmdargs, **kwargs):
	"""Perform a complete dialog-like program invocation.

        This function invokes the dialog-like program, waits for its
        termination and returns its exit status and what it wrote on
        its standard error stream after having closed its standard
        input, output and error.

        """
        # Get the Popen3 object
        p = apply(self._call_program, [cmdargs], kwargs)
        (exit_code, output) = self._wait_for_program_termination(p)
        p.childerr.close()              # dialog's stderr
        p.fromchild.close()             # dialog's stdout
        p.tochild.close()               # dialog's stdin
        
	return (exit_code, output)

    # This is for compatibility with the old dialog.py
    def _perform_no_options(self, cmd):
	"""Call dialog without passing any more options."""
	return os.system(self._dialog_prg + ' ' + cmd)

    # For compatibility with the old dialog.py
    def clear(self):
	"""Clear the screen. Equivalent to the dialog --clear option.

        This method is obsolete. Please remove calls to it from your
        programs.

	"""
	self._perform_no_options('--clear')

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
        the left-, up-, right- and down-arrows. Use tab or backtab to
        move between windows. If the year is given as zero, the
        current date is used as an initial value.

        Return a tuple of the form (code, date) where `code' is the
        exit status (an integer) of the dialog-like program and
        `date' is a list of the form [day, month, year] (where `day',
        `month' and `year' are integers corresponding to the date
        chosen by the user) if the box was closed with OK, or None if
        it was closed with the Cancel button.

	"""
	(code, output) = apply(self._perform,
                               [["--calendar", text, str(height), str(width),
                                 str(day), str(month), str(year)]],
                               kwargs)
        if code == self.DIALOG_OK:
            mo = _calendar_date_rec.match(output)
            if mo is None:
                raise UnexpectedDialogOutput(
                    "the dialog-like program returned the following "
                    "unexpected date with the calendar box: %s" % output)
            date = map(int, mo.group("day", "month", "year"))
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
                       `status' specifies the initial on/off state of
                       each entry; can be 0 or 1 (integers, 1 meaning
                       checked, i.e. "on"), or "on", "off" or any
                       uppercase variant of these two strings.

        Return a tuple of the form (code, [tag, ...]) with the tags
        for the entries that were selected by the user. `code' is the
        exit status of the dialog-like program.

        If the user exits with ESC or CANCEL, the returned tag list
        is empty.

        """
        cmd = ["--checklist", text, str(height), str(width), str(list_height)]
        for t in choices:
            cmd.extend(((t[0], t[1], _to_onoff(t[2]))))
	(code, output) = apply(self._perform, [cmd], kwargs)
        # Extract the list of tags from the result (which is a string like
        # '"tag 1" "tag 2" "tag 3"...')
        if output:
            return (code, re.findall(r'"([^"]*)"', output))
        else:                           # empty selection
            return (code, [])

    def fselect(self, filepath, height, width, **kwargs):
        """Display a file selection dialog box.

        filepath -- initial file path
        height   -- height of the box
        width    -- width of the box
        
        The file-selection dialog displays a text-entry window in
        which you can type a filename (or directory), and above that
        two windows with directory names and filenames.

        Here filepath can be a filepath in which case the file and
        directory windows will display the contents of the path and
        the text-entry window will contain the preselected filename.

        Use tab or arrow keys to move between the windows. Within the
        directory or filename windows, use the up/down arrow keys to
        scroll the current selection. Use the space-bar to copy the
        current selection into the text-entry window.

        Typing any printable characters switches focus to the
        text-entry window, entering that character as well as
        scrolling the directory and filename windows to the closest
        match.

        Use a carriage return or the "OK" button to accept the
        current value in the text-entry window, or the "Cancel"
        button to cancel.

        Return a tuple of the form (code, path) where `code' is the
        exit status (an integer) of the dialog-like program and
        `path' is the path chosen by the user (whose last element may
        be a directory as well as a file).
              
	"""
	return apply(self._perform,
                     [["--fselect", filepath, str(height), str(width)]],
                     kwargs)
    
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

        Gauge typical usage (assuming that `d' is an instance of the
	Dialog class) looks like this:
	    d.gauge_start()
	    # do something
	    d.gauge_update(10)       # 10% of the whole task is done
	    # ...
	    d.gauge_update(100, "any text here") # work is done
	    exit_code = d.gauge_stop()           # cleanup actions

	"""
        self._gauge_process = apply(self._call_program,
                                    [["--gauge", text, str(height),
                                      str(width), str(percent)]],
                                    kwargs)

    def gauge_update(self, percent, text="", update_text=0):
	"""Update a running gauge box.
	
        percent     -- new percentage to show in the gauge meter
        text        -- new text to optionally display in the box
        update-text -- boolean indicating whether to update the
                       text in the box

        This function updates the percentage shown by the meter of a
        running gauge box (meaning `gauge_start' must have been
        called previously). If update_text is true (for instance, 1),
        the text displayed in the box is also updated.

	See the `gauge_start' function's documentation for
	information about how to use a gauge.

        Return value: undefined.
        
	"""
	if update_text:
	    gauge_data = "XXX\n%d\n%s\nXXX\n" % (percent, text)
	else:
	    gauge_data = "%d\n" % percent
	self._gauge_process.tochild.write(gauge_data)
	self._gauge_process.tochild.flush()
    
    # For "compatibility" with the old dialog.py...
    gauge_iterate = gauge_update

    def gauge_stop(self):
	"""Terminate a running gauge.

        This function performs the appropriate cleanup actions to
        terminate a running gauge (started with `gauge_start').
	
	See the `gauge_start' function's documentation for
	information about how to use a gauge.

        Return value: undefined.

	"""
        p = self._gauge_process
        p.tochild.close()               # dialog's stdin
        exit_code = self._wait_for_program_termination(p)[0]
        p.childerr.close()              # dialog's stderr
        p.fromchild.close()             # dialog's stdout
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

	"""
	return apply(self._perform,
                     [["--infobox", text, str(height), str(width)]],
                     kwargs)[0]

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

        Return a tuple of the form (code, string) where `code' is the
        exit status of the dialog-like program and `string' is the
        string entered by the user.

	"""
	return apply(self._perform,
                     [["--inputbox", text, str(height), str(width), init]],
                     kwargs)

    def menu(self, text, height=15, width=54, menu_height=7, choices=[],
             **kwargs):
        """Display a menu dialog box.

        text        -- text to display in the box
        height      -- height of the box
        width       -- width of the box
        menu_height -- number of entries displayed in the box (which
                       can be scrolled) at a given time
        choices     -- a sequence of (tag, item) or (tag, item, help)
                       tuples (the meaning of each `tag', `item' and
                       `help' is explained below)


        Overview
        --------

        As its name suggests, a menu box is a dialog box that can be
        used to present a list of choices in the form of a menu for
        the user to choose. Choices are displayed in the order given.

        Each menu entry consists of a `tag' string and an `item'
        string. The tag gives the entry a name to distinguish it from
        the other entries in the menu. The item is a short
        description of the option that the entry represents.

        The user can move between the menu entries by pressing the
        UP/DOWN keys, the first letter of the tag as a hot-key, or
        the number keys 1-9. There are menu-height entries displayed
        in the menu at one time, but the menu will be scrolled if
        there are more entries than that.


        Providing on-line help facilities
        ---------------------------------

        If this function is called with item_help=1 (keyword
        argument), the option --item-help is passed to dialog and the
        tuples contained in `choices' must contain 3 elements each :
        (tag, item, help). The help string for the highlighted item
        is displayed in the bottom line of the screen and updated as
        the user highlights other items.

        If item_help=0 or if this keyword argument is not passed to
        this function, the tuples contained in `choices' must contain
        2 elements each : (tag, item).

        If this function is called with help_button=1, it must also
        be called with item_help=1 (this is a limitation of dialog),
        therefore the tuples contained in `choices' must contain 3
        elements each as explained in the previous paragraphs. This
        will cause a Help button to be added to the right of the
        Cancel button (by passing --help-button to dialog).


        Return value
        ------------

        Return a tuple of the form (exit_info, string).

        `exit_info' is either:
          - an integer, being the the exit status of the dialog-like
            program
          - or the string "help", meaning that help_button=1 was
            passed and that the user chose the Help button instead of
            OK or Cancel.

        The meaning of `string' depends on the value of exit_info:
          - if `exit_info' is 0, `string' is the tag chosen by the
            user
          - if `exit_info' is "help", `string' is the `help' string
            from the `choices' argument corresponding to the item
            that was highlighted when the user chose the Help button
          - otherwise (the user chose Cancel or pressed Esc, or there
            was a dialog error), the value of `string' is undefined.

	"""
        cmd = ["--menu", text, str(height), str(width), str(menu_height)]
        for t in choices:
            cmd.extend(t)
	(code, output) = apply(self._perform, [cmd], kwargs)
        if "help_button" in kwargs.keys() and output.startswith("HELP "):
            return ("help", output[5:])
        else:
            return (code, output)

    def msgbox(self, text, height=10, width=30, **kwargs):
        """Display a message dialog box.

        text   -- text to display in the box
        height -- height of the box
        width  -- width of the box

        A message box is very similar to a yes/no box. The only
        difference between a message box and a yes/no box is that a
        message box has only a single OK button. You can use this
        dialog box to display any message you like. After reading
        the message, the user can press the ENTER key so that dialog
        will exit and the calling program can continue its
        operation.

        Return the exit status (an integer) of the dialog-like
        program.

	"""
	return apply(self._perform,
                     [["--msgbox", text, str(height), str(width)]],
                     kwargs)[0]

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

        Return a tuple of the form (code, password) where `code' is
        the exit status of the dialog-like program and `password' is
        the password entered by the user.

	"""
	return apply(self._perform,
                     [["--passwordbox", text, str(height), str(width), init]],
                     kwargs)

    def radiolist(self, text, height=15, width=54, list_height=7,
                  choices=[], **kwargs):
	"""Display a radiolist box.

        text        -- text to display in the box
        height      -- height of the box
        width       -- width of the box
        list_height -- number of entries displayed in the box (which
                       can be scrolled) at a given time
        choices     -- a list of tuples (tag, item, status) where
                       `status' specifies the initial on/off state
                       each entry; can be 0 or 1 (integers, 1 meaning
                       checked, i.e. "on"), or "on", "off" or any
                       uppercase variant of these two strings.
                       No more than one entry should  be set to on.

        A radiolist box is similar to a menu box. The main difference
        is that you can indicate which entry is initially selected,
        by setting its status to on.

        Return a tuple of the form (code, tag) with the tag for the
        entry that was chosen by the user. `code' is the exit status
        of the dialog-like program.

        If the user exits with ESC or CANCEL, or if all entries were
        initially set to off and not altered before the user chose
        OK, the returned tag is the empty string.

	"""
        cmd = ["--radiolist", text, str(height), str(width), str(list_height)]
        for t in choices:
            cmd.extend(((t[0], t[1], _to_onoff(t[2]))))
	return apply(self._perform, [cmd], kwargs)

    def scrollbox(self, text, height=20, width=78, **kwargs):
	"""Display a string in a scrollable box.

        text   -- text to display in the box
        height -- height of the box
        width  -- width of the box

        This method is a layer on top of textbox. The textbox option
        in dialog allows to display file contents only. This method
        allows you to display any text in a scrollable box. This is
        simply done by creating a temporary file, calling textbox and
        deleting the temporary file afterwards.

        Return an integer, which is:
          - the dialog-like program's exit status if all went well
            until its execution
          - -1 if an error occurred before dialog's invocation for
            the textbox widget

        Notable exception: IOError can be raised while playing with
        the temporary file.

	"""
        fName = tempfile.mktemp()
        res = -1
        try:
            f = open(fName, "wb")
            f.write(text)
            f.close()
            res = apply(self._perform,
                        [["--textbox", fName, str(height),
                          str(width)]], kwargs)
        finally:
            if type(f) == types.FileType:
                f.close()               # Safe, even several times
                os.unlink(fName)
        return res

    def tailbox(self, filename, height=20, width=60, **kwargs):
        """Display the contents of a file in a dialog box, as in "tail -f".

        filename -- name of the file whose contents is to be
                    displayed in the box
        height   -- height of the box
        width    -- width of the box

        Display the contents of the specified file, updating the
        dialog box whenever the file grows, as with the "tail -f"
        command.

        Return the exit status (an integer) of the dialog-like
        program.

	"""
	return apply(self._perform,
                     [["--tailbox", filename, str(height), str(width)]],
                     kwargs)[0]
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

	"""
        # This is for backward compatibility... not that it is
        # stupid, but I prefer explicit programming.
        if "title" not in kwargs.keys():
	    kwargs["title"] = filename
	return apply(self._perform,
                     [["--textbox", filename, str(height), str(width)]],
                     kwargs)[0]

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

        Return a tuple of the form (code, time) where `code' is the
        exit status (an integer) of the dialog-like program and
        `time' is a list of the form [hour, minute, second] (where
        `hour', `minute' and `second' are integers corresponding to
        the time chosen by the user) if the box was closed with OK,
        or None if it was closed with the Cancel button.

	"""
	(code, output) = apply(self._perform,
                               [["--timebox", text, str(height), str(width),
                                 str(hour), str(minute), str(second)]],
                               kwargs)
        if code == self.DIALOG_OK:
            mo = _timebox_time_rec.match(output)
            if mo is None:
                raise UnexpectedDialogOutput(
                    "the dialog-like program returned the following "
                    "unexpected time with the --timebox option: %s" % output)
            time = map(int, mo.group("hour", "minute", "second"))
        else:
            time = None
        return (code, time)

    def yesno(self, text, height=10, width=30, **kwargs):
        """Display a yes/no dialog box.

        text   -- text to display in the box
        height -- height of the box
        width  -- width of the box

        A yes/no dialog box of size `height' rows by `width' columns
        will be displayed. The string specified by `text' is
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

	"""
	return apply(self._perform,
                     [["--yesno", text, str(height), str(width)]],
                     kwargs)[0]
