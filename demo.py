#! /usr/bin/env python3

# demo.py --- A simple demonstration program and cheap test suite for
#             pythondialog
# Copyright (C) 2002-2010, 2013  Florent Rougon
# Copyright (C) 2000  Robb Shecter, Sultanbek Tezadov
#
# This program is in the public domain.

"""Demonstration program for pythondialog.

This is a simple program demonstrating the possibilities offered by
the pythondialog module (which is itself a Python interface to the
well-known dialog utility, or any other program compatible with
dialog).

Please have a look at the documentation for the 'handle_exit_code'
function in order to understand the somewhat relaxed error checking
policy for pythondialog calls in this demo.

"""


import sys, os, locale, stat, time, getopt, subprocess, traceback, textwrap
import contextlib               # Not really indispensable here
import dialog

progname = os.path.basename(sys.argv[0])
progversion = "0.5"
version_blurb = """Demonstration program and cheap test suite for pythondialog.

Copyright (C) 2002-2010  Florent Rougon
Copyright (C) 2000  Robb Shecter, Sultanbek Tezadov

This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE."""

default_debug_filename = "pythondialog.debug"

usage = """Usage: {progname} [option ...]
Demonstration program and cheap test suite for pythondialog.

Options:
  -t, --test-suite             test all widgets; implies --fast
  -f, --fast                   fast mode (e.g., makes the gauge demo run faster)
      --debug                  enable logging of all dialog command lines
      --debug-file=FILE        where to write debug information (default:
                               {debug_file} in the current directory)
      --help                   display this message and exit
      --version                output version information and exit""".format(
    progname=progname, debug_file=default_debug_filename)

# Global parameters
params = {}

tw = textwrap.TextWrapper(width=78, break_long_words=False,
                          break_on_hyphens=True)
from textwrap import dedent

try:
    from textwrap import indent
except ImportError:
    def indent(text, prefix, predicate=None):
        l = []

        for line in text.splitlines(True):
            if (callable(predicate) and predicate(line)) \
                    or (not callable(predicate) and predicate) \
                    or (predicate is None and line.strip()):
                line = prefix + line
            l.append(line)

        return ''.join(l)


def handle_exit_code(d, code):
    """Sample function showing how to interpret the dialog exit codes.

    This function is not used after every call to dialog in this demo
    for two reasons:

       1. For some boxes, unfortunately, dialog returns the code for
          ERROR when the user presses ESC (instead of the one chosen
          for ESC). As these boxes only have an OK button, and an
          exception is raised and correctly handled here in case of
          real dialog errors, there is no point in testing the dialog
          exit status (it can't be CANCEL as there is no CANCEL
          button; it can't be ESC as unfortunately, the dialog makes
          it appear as an error; it can't be ERROR as this is handled
          in dialog.py to raise an exception; therefore, it *is* OK).

       2. To not clutter simple code with things that are
          demonstrated elsewhere.

    """
    # d is supposed to be a Dialog instance
    if code in (d.DIALOG_CANCEL, d.DIALOG_ESC):
        if code == d.DIALOG_CANCEL:
            msg = "You chose cancel in the last dialog box. Do you want to " \
                  "exit this demo?"
        else:
            msg = "You pressed ESC in the last dialog box. Do you want to " \
                  "exit this demo?"
        # "No" or "ESC" will bring the user back to the demo.
        # DIALOG_ERROR is propagated as an exception and caught in main().
        # So we only need to handle OK here.
        if d.yesno(msg) == d.DIALOG_OK:
            sys.exit(0)
        return d.DIALOG_CANCEL
    else:
        # 'code' can be d.DIALOG_OK (most common case) or, depending on the
        # particular dialog box, d.DIALOG_EXTRA, d.DIALOG_HELP,
        # d.DIALOG_ITEM_HELP... (cf. _dialog_exit_status_vars in dialog.py)
        return code


def infobox_demo(d):
    # Exit code thrown away to keep this demo code simple (however, real
    # errors are propagated by an exception)
    d.infobox("One moment, please. Just wasting some time here to "
              "show you the infobox...")

    time.sleep(0.5 if params["fast_mode"] else 4.0)


def gauge_demo(d):
    d.gauge_start("Progress: 0%", title="Still testing your patience...")

    for i in range(1, 101):
        if i < 50:
            d.gauge_update(i, "Progress: %d%%" % i, update_text=True)
        elif i == 50:
            d.gauge_update(i, "Over %d%%. Good." % i, update_text=True)
        elif i == 80:
            d.gauge_update(i, "Yeah, this boring crap will be over Really "
                           "Soon Now.", update_text=True)
        else:
            d.gauge_update(i)

        time.sleep(0.01 if params["fast_mode"] else 0.1)

    d.gauge_stop()


def mixedgauge_demo(d):
    for i in range(1, 101, 20):
        d.mixedgauge("This is the 'text' part of the mixedgauge\n"
                     "and this is a forced new line.",
                     percent=int(round(72+28*i/100)),
                     elements=[("Task 1", "Foobar"),
                               ("Task 2", 0),
                               ("Task 3", 1),
                               ("Task 4", 2),
                               ("Task 5", 3),
                               ("", 8),
                               ("Task 6", 5),
                               ("Task 7", 6),
                               ("Task 8", 7),
                               ("", ""),
                               # 0 is the dialog special code for "Succeeded",
                               # so these must not be equal to zero! That is
                               # why I made the range() above start at 1.
                               ("Task 9", -max(1, 100-i)),
                               ("Task 10", -i)])
        time.sleep(2)


def yesno_demo(d):
    # Return the answer given to the question (also specifies if ESC was
    # pressed)
    return d.yesno("Do you like this demo?", yes_label="Yes, I do",
                   no_label="No, I do not", width=40)


def msgbox_demo(d, answer):
    if answer == d.DIALOG_OK:
        msg = "Excellent! Press OK to see its source code (or another file " \
        "if not in the correct directory)."
    else:
        msg = "Well, feel free to send your complaints to /dev/null!\n\n" \
            "Sincerely yours, etc."

    d.msgbox(msg, width=50)


def textbox_demo(d):
    # Better use the absolute path for displaying in the dialog title
    filepath = os.path.abspath(__file__)
    d.textbox(filepath, width=76, title="Contents of %s" % filepath)


def inputbox_demo(d):
    # If the user presses Cancel, he is asked (by handle_exit_code) if he
    # wants to exit the demo. We loop as long as he tells us he doesn't want
    # to do so.
    while True:
        (code, answer) = d.inputbox("What's your name?", init="Snow White")
        if handle_exit_code(d, code) == d.DIALOG_OK:
            break
    return answer


def form_demo(d):
    while True:
        elements = [
            ("Size (cm)", 1, 1, "175", 1, 20, 4, 3),
            ("Weight (kg)", 2, 1, "85", 2, 20, 4, 3),
            ("City", 3, 1, "Groboule-les-Bains", 3, 20, 15, 25),
            ("State", 4, 1, "Some Lost Place", 4, 20, 15, 25),
            ("Country", 5, 1, "Nowhereland", 5, 20, 15, 20),
            ("My", 6, 1, "I hereby declare that, upon leaving this "
             "world, all", 6, 20, 0, 0),
            ("Very", 7, 1, "my fortune shall be transferred to Florent "
             "Rougon's", 7, 20, 0, 0),
            ("Last", 8, 1, "bank account number 000 4237 4587 32454/78 at "
             "Banque", 8, 20, 0, 0),
            ("Will", 9, 1, "Cantonale Vaudoise, Lausanne, Switzerland.",
             9, 20, 0, 0) ]

        (code, fields) = d.form(
            "Please fill in some personal information:", elements, width=77)

        if handle_exit_code(d, code) == d.DIALOG_OK:
            break

    return fields


def passwordform_demo(d):
    while True:
        elements = [
            ("Secret field 1", 1, 1, "", 1, 20, 12, 0),
            ("Secret field 2", 2, 1, "", 2, 20, 12, 0),
            ("Secret field 3", 3, 1, "Providing a non-empty initial content "
             "(like this) for an invisible field can be very confusing!",
             3, 20, 30, 160)]

        (code, fields) = d.passwordform(
            "Please enter all your secret passwords.\n\nOn purpose here, "
            "nothing is echoed when you type in the passwords. If you want "
            "asterisks, use the 'insecure' keyword argument as in the "
            "passwordbox demo.",
            elements, width=77, height=15, title="Passwordform demo")

        if handle_exit_code(d, code) == d.DIALOG_OK:
            break

    d.msgbox("Secret password 1: '%s'\n"
             "Secret password 2: '%s'\n"
             "Secret password 3: '%s'" % tuple(fields),
             width=60, height=20, title="The Whole Truth Now Revealed")

    return fields


def mixedform_demo(d):
    while True:
        HIDDEN    = 0x1
        READ_ONLY = 0x2

        elements = [
            ("Size (cm)", 1, 1, "175", 1, 20, 4, 3, 0x0),
            ("Weight (kg)", 2, 1, "85", 2, 20, 4, 3, 0x0),
            ("City", 3, 1, "Groboule-les-Bains", 3, 20, 15, 25, 0x0),
            ("State", 4, 1, "Some Lost Place", 4, 20, 15, 25, 0x0),
            ("Country", 5, 1, "Nowhereland", 5, 20, 15, 20, 0x0),
            ("My", 6, 1, "I hereby declare that, upon leaving this "
             "world, all", 6, 20, 54, 0, READ_ONLY),
            ("Very", 7, 1, "my fortune shall be transferred to Florent "
             "Rougon's", 7, 20, 54, 0, READ_ONLY),
            ("Last", 8, 1, "bank account number 000 4237 4587 32454/78 at "
             "Banque", 8, 20, 54, 0, READ_ONLY),
            ("Will", 9, 1, "Cantonale Vaudoise, Lausanne, Switzerland.",
             9, 20, 54, 0, READ_ONLY),
            ("Read-only field...", 10, 1, "... that doesn't go into the "
             "output list", 10, 20, 0, 0, 0x0),
            ("\/3r`/ 53kri7 (0d3", 11, 1, "", 11, 20, 15, 20, HIDDEN) ]

        (code, fields) = d.mixedform(
            "Please fill in some personal information:", elements, width=77)

        if handle_exit_code(d, code) == d.DIALOG_OK:
            break

    return fields


def menu_demo(d, name, city, state, country, size, weight, secret_code,
              last_will1, last_will2, last_will3, last_will4):
    while True:
        text = """\
Hello, %s from %s, %s, %s, %s cm, %s kg.
Thank you for giving us your Very Secret Code '%s'.

As expressly stated in the previous form, your Last Will reads: "%s"

All that was very interesting, thank you. However, in order to know you \
better and provide you with the best possible customer service, we would \
still need to know your favorite day of the week. Please indicate your \
preference below.""" \
            % (name, city, state, country, size, weight, secret_code,
               ' '.join([last_will1, last_will2, last_will3, last_will4]))

        (code, tag) = d.menu(text, height=23, width=76,
            choices=[("Monday", "Being the first day of the week..."),
                     ("Tuesday", "Comes after Monday"),
                     ("Wednesday", "Before Thursday day"),
                     ("Thursday", "Itself after Wednesday"),
                     ("Friday", "The best day of all"),
                     ("Saturday", "Well, I've had enough, thanks"),
                     ("Sunday", "Let's rest a little bit")])

        if handle_exit_code(d, code) == d.DIALOG_OK:
            break

    return tag


def checklist_demo(d):
    while True:
        # We could put non-empty items here (not only the tag for each entry)
        (code, tags) = d.checklist(text="What sandwich toppings do you like?",
                                   height=15, width=54, list_height=7,
                                   choices=[("Catsup", "",             False),
                                            ("Mustard", "",            False),
                                            ("Pesto", "",              False),
                                            ("Mayonaise", "",          True),
                                            ("Horse radish","",        True),
                                            ("Sun-dried tomatoes", "", True)],
                                   title="Do you prefer ham or spam?",
                                   backtitle="And now, for something "
                                   "completely different...")
        if handle_exit_code(d, code) == d.DIALOG_OK:
            break
    return tags


def radiolist_demo(d):
    while True:
        (code, tag) = d.radiolist(
            "What's your favorite kind of sandwich?",
            width=65,
            choices=[("Hamburger", "2 slices of bread, a steak...", False),
                     ("Hotdog", "doesn't bite any more", False),
                     ("Burrito", "no se lo que es", False),
                     ("Doener", "Huh?", False),
                     ("Falafel", "Erm...", False),
                     ("Bagel", "Of course!", False),
                     ("Big Mac", "Ah, that's easy!", True),
                     ("Whopper", "Erm, sorry", False),
                     ("Quarter Pounder", 'called "le Big Mac" in France', False),
                     ("Peanut Butter and Jelly", "Well, that's your own "
                      "business...", False),
                     ("Grilled cheese", "And nothing more?", False)])
        if handle_exit_code(d, code) == d.DIALOG_OK:
            break
    return tag


def calendar_demo(d):
    while True:
        (code, date) = d.calendar("When do you think Georg Cantor was born?",
                                  year=0)
        if handle_exit_code(d, code) == d.DIALOG_OK:
            break
    return date


def passwordbox_demo(d):
    while True:
        # 'insecure' keyword argument only asks dialog to echo asterisks when
        # the user types characters. Not *that* bad.
        (code, password) = d.passwordbox("What is your root password, "
                                         "so that I can crack your system "
                                         "right now?", insecure=True)
        if handle_exit_code(d, code) == d.DIALOG_OK:
            break
    return password


def comment_on_Cantor_date_of_birth(day, month, year):
    complement = "For your information, Georg Ferdinand Ludwig Philip Cantor, " \
        "a great mathematician, was born on March 3, 1845 in Saint " \
        "Petersburg, and died on January 6, 1918."

    if (year, month, day) == (1845, 3, 3):
        return "Spot-on! I'm impressed."
    elif year == 1845:
        return "You guessed the year right. {0}".format(complement)
    elif abs(year-1845) < 30:
        return "Not too far. {0}".format(complement)
    else:
        return "Well, not quite. {0}".format(complement)


def scrollbox_demo(d, name, favorite_day, toppings, sandwich, date,
                   password):
    tw71 = textwrap.TextWrapper(width=71, break_long_words=False,
                                break_on_hyphens=True)
    day, month, year = date
    msg = """\
Here are some vital statistics about you:

Name: %s
Favorite day of the week: %s
Favorite sandwich toppings:%s
Favorite sandwich: %s

Your answer about Georg Cantor's date of birth: %04d-%02d-%02d.
%s

Your root password is: ************************** (looks good!)""" \
     % (name, favorite_day,
        "\n    ".join([''] + toppings),
        sandwich, year, month, day,
        tw71.fill(comment_on_Cantor_date_of_birth(day, month, year)))
    d.scrollbox(msg, height=20, width=75, title="Great Report of the Year")


def dselect_demo(d, init_dir=None):
    init_dir = init_dir or params["home_dir"]
    # Make sure the directory we chose ends with os.sep so that dialog
    # shows its contents right away
    if not init_dir.endswith(os.sep):
        init_dir += os.sep

    while True:
        (code, path) = d.dselect(init_dir, 10, 50,
                                 title="Please choose a directory")
        if handle_exit_code(d, code) == d.DIALOG_OK:
            if not os.path.isdir(path):
                d.msgbox("Hmm. It seems that '%s' is not a directory" % path)
            else:
                d.msgbox("Directory '%s' thanks you for choosing him." % path)
                break
    return path


# Help strings used in several places
FSELECT_HELP = """\
Hint: the complete file path must be entered in the bottom field. One \
convenient way to achieve this is to use the SPACE bar when the desired file \
is highlighted in the top-right list.

As usual, you can use the TAB and arrow keys to move between controls. If in \
the bottom field, the SPACE key provides auto-completion."""

# The following help text was initially meant to be used for several widgets
# (at least progressbox and tailbox). Currently (dialog version 1.1-20100119),
# "dialog --tailbox" doesn't seem to work with FIFOs, so the "flexibility" of
# the help text is unused (another text is used when demonstrating --tailbox).
# However, this might change in the future...
def FIFO_HELP(widget):
    return """\
For demos based on the %(widget)s widget, you may use a FIFO, also called \
"named pipe". This is a special kind of file, to which you will be able to \
easily append data. With the %(widget)s widget, you can see the data stream \
flow in real time.

To create a FIFO, you can use the commmand mkfifo(1), like this:

  %% mkfifo /tmp/my_shiny_new_fifo

Then, you can cat(1) data to the FIFO like this:

  %% cat >>/tmp/my_shiny_new_fifo
  First line of text
  Second line of text
  ...

You can end the input to cat(1) by typing Ctrl-D at the beginning of a \
line.""" % {"widget": widget}


def fselect_demo(d, widget, init_dir=None, allow_FIFOs=False, **kwargs):
    init_dir = init_dir or params["home_dir"]
    # Make sure the directory we chose ends with os.sep so that dialog
    # shows its contents right away
    if not init_dir.endswith(os.sep):
        init_dir += os.sep

    while True:
        (code, path) = d.fselect(init_dir, height=10, width=60, **kwargs)

        # Provide an easy way out...
        if code in (d.DIALOG_CANCEL, d.DIALOG_ESC):
            path = None
            break
        elif code == d.DIALOG_OK:
            # Of course, one can use os.path.isfile(path) here, but we want to
            # allow regular files *and* possibly FIFOs. Since there is no
            # os.path.is*** convenience function for FIFOs, let's go with
            # os.stat.
            try:
                mode = os.stat(path)[stat.ST_MODE]
            except os.error as e:
                d.msgbox("Error: %s" % e.strerror)
                continue

            # Accept FIFOs only if allow_FIFOs is True
            if stat.S_ISREG(mode) or (allow_FIFOs and stat.S_ISFIFO(mode)):
                break
            else:
                if allow_FIFOs:
                    help_text = """\
You are expected to select a *file* here (possibly a FIFO), or press the \
Cancel button.\n\n%s

For your convenience, I will reproduce the FIFO help text here:\n\n%s""" \
                        % (FSELECT_HELP, FIFO_HELP(widget))
                else:
                    help_text = """\
You are expected to select a regular *file* here, or press the \
Cancel button.\n\n%s""" % (FSELECT_HELP,)

                d.msgbox(help_text, width=72, height=20)
        else:
            d.msgbox("Unexpected exit status from the dialog-like program: %d"
                     % code)
    return path


def editbox_demo(d, filepath):
    if os.path.isfile(filepath):
        code, text = d.editbox(filepath, 20, 60, title="A Cheap Text Editor")

    d.scrollbox(text, title="Resulting text")


def inputmenu_demo(d):
    choices = [ ("1st_tag", "Item 1 text"),
                ("2nd_tag", "Item 2 text"),
                ("3rd_tag", "Item 3 text") ]

    for i in range(4, 21):
        choices.append(("%dth_tag" % i, "Item %d text" % i))

    exit_info, tag, new_item_text = d.inputmenu(
        "Demonstration of inputmenu. Any item can be either accepted as is, "
        "or renamed.", height=0, width=60, menu_height=10, choices=choices,
        title="Simple 'inputmenu' demo")

    if exit_info == "accepted":
        text = "The item corresponding to tag '%s' was accepted." % tag
    elif exit_info == "renamed":
        text = "The item corresponding to tag '%s' was renamed to '%s'." \
            % (tag, new_item_text)
    else:
        text = "The dialog-like program returned exit status %d." % exit_info

    d.msgbox(text, width=60, title="Outcome of the 'inputmenu' demo")


def tailbox_demo(d):
    widget = "tailbox"

    # First, ask the user for a file.
    # Strangely (dialog version 1.1-20100119 bug?), "dialog --tailbox" doesn't
    # work with FIFOs.
    path = fselect_demo(d, widget, allow_FIFOs=False,
                        title="Please choose a file to be shown as with "
                        "'tail -f'")
    # Now, the tailbox
    if path is None:
        # User chose to abort
        return
    else:
        d.tailbox(path, 20, 60, title="Tailbox example")


def progressbox_demo_with_filepath(d):
    widget = "progressbox"

    # First, ask the user for a file (possibly FIFO)
    d.msgbox(FIFO_HELP(widget), width=72, height=20)
    path = fselect_demo(d, widget, allow_FIFOs=True,
                        title="Please choose a file to be shown as with "
                        "'tail -f'")

    if path is None:
        # User chose to abort
        return
    else:
        d.progressbox(file_path=path, text="You can put some header text here",
                      title="Progressbox example with a file path")


def progressbox_demo_with_file_descriptor(d):
    func_name = "progressbox_demo_with_file_descriptor"
    text = """\
A long time ago in a galaxy far,
far away...





A NEW HOPE

It was a period of intense
sucking. Graphical toolkits for
Python were all nice and clean,
but they were, well, graphical.
And as every one knows, REAL
PROGRAMMERS ALWAYS WORK ON VT-100
TERMINALS. In text mode.

Besides, those graphical toolkits
were usually too complex for
simple programs, so most FLOSS
geeks ended up writing
command-line tools except when
they really needed the full power
of mainstream graphical toolkits,
such as Qt, GTK+ and wxWidgets.

But... thanks to people like
Thomas E. Dickey, there are now
at our disposal several free
software command-line programs,
such as dialog, that allow easy
building of graphically-oriented
interfaces in text-mode
terminals. These are good for
tasks where line-oriented
interfaces are not well suited,
as well as for the increasingly
common type who runs away as soon
as he sees something remotely
resembling a command line.

But this is not for Python! I want
my poney!

Seeing this unacceptable
situation, Robb Shecter had the
idea, back in the olden days of
Y2K (when the world was supposed
to suddenly collapse, remember?),
to wrap a dialog interface into a
Python module called dialog.py.

pythondialog was born. Florent
Rougon, who was looking for
something like that in 2002,
found the idea rather cool and
improved the module during the
following years...""" + 15*'\n'

    # Since this is just a demo, I will not try to catch os.error exceptions
    # in this function, for the sake of readability.
    read_fd, write_fd = os.pipe()

    child_pid = os.fork()
    if child_pid == 0:
        try:
            # We are in the child process. We MUST NOT raise any exception.
            # No need for this one in the child process
            os.close(read_fd)

            # Python file objects are easier to use than file descriptors. For
            # a start, you don't have to check the number of bytes actually
            # written every time...
            # "buffering = 1" means wfile is going to be line-buffered
            with os.fdopen(write_fd, mode="w", buffering=1) as wfile:
                for line in text.split('\n'):
                    wfile.write(line + '\n')
                    time.sleep(0.02 if params["fast_mode"] else 1.2)

            os._exit(0)
        except:
            os._exit(127)

    # We are in the father process. No need for write_fd anymore.
    os.close(write_fd)
    d.progressbox(fd=read_fd, title="Progressbox example with a file descriptor")

    # Now that the progressbox is over (second child process, running the
    # dialog-like program), we can wait() for the first child process.
    # Otherwise, we could have a deadlock in case the pipe gets full, since
    # dialog wouldn't be reading it.
    exit_info = os.waitpid(child_pid, 0)[1]
    if os.WIFEXITED(exit_info):
        exit_code = os.WEXITSTATUS(exit_info)
    elif os.WIFSIGNALED(exit_info):
        d.msgbox("%s(): first child process terminated by signal %d" %
                 (func_name, os.WTERMSIG(exit_info)))
    else:
        assert False, "How the hell did we manage to get here?"

    if exit_code != 0:
        d.msgbox("%s(): first child process ended with exit status %d"
                 % (func_name, exit_code))


def pause_demo(d, seconds):
    d.pause("""\
Ugh, sorry. pythondialog is still in development, and its advanced circuitry \
detected internal error number 0x666. That's a pretty nasty one, you know.

I am embarrassed. I don't know how to tell you, but we are going to have to \
reboot. In %d seconds.

Fasten your seatbelt...""" % seconds, height=18, seconds=seconds)


def clear_screen(d):
    # This program comes with ncurses
    program = "clear"

    try:
        p = subprocess.Popen([program], shell=False, stdout=None, stderr=None,
                             close_fds=True)
        retcode = p.wait()
    except os.error as e:
        d.msgbox("Unable to execute program '%s': %s." % (program,
                                                          e.strerror),
                 title="Error")
        return -1

    if retcode > 0:
        msg = "Program %s returned exit code %d." % (program, retcode)
    elif retcode < 0:
        msg = "Program %s was terminated by signal %d." % (program, -retcode)
    else:
        return 0

    d.msgbox(msg)
    return -1


def get_term_size_and_backend_version(d, min_rows, min_cols):
    backend_version = d.backend_version()
    if not backend_version:
        print(tw.fill(
                "Unable to retrieve the version of the dialog-like backend. "
                "Not running cdialog?") + "\nPress Enter to continue.",
              file=sys.stderr)
        input()

    term_rows, term_cols = d.maxsize(use_persistent_args=False)
    if term_rows < min_rows or term_cols < min_cols:
        print(tw.fill(dedent("""\
          Your terminal has less than {0} rows or less than {1} columns;
          you may experience problems with the demo. You have been warned."""
                             .format(min_rows, min_cols)))
              + "\nPress Enter to continue.")
        input()

    return (term_rows, term_cols, backend_version)


def demo(d):
    min_rows, min_cols = 24, 80
    term_rows, term_cols, backend_version = get_term_size_and_backend_version(
        d, min_rows, min_cols)

    d.msgbox("""\
Hello, and welcome to the pythondialog {pydlg_version} demonstration program.

You can scroll through this dialog box with the Up and Down arrow keys. \
Please note that some of the dialogs will not work, and cause the demo to \
stop, if your terminal is too small. The recommended size is (at least) \
{min_rows} rows by {min_cols} columns.

This script is being run by a Python interpreter identified as follows:

{py_version}

The dialog-like program displaying this message box reports version \
{backend_version} and a terminal size of {rows} rows by {cols} columns."""
             .format(
            pydlg_version=dialog.__version__, backend_version=backend_version,
            py_version=indent(sys.version, "  "),
            rows=term_rows, cols=term_cols,
            min_rows=min_rows, min_cols=min_cols),
             width=60, height=17)

    progressbox_demo_with_file_descriptor(d)
    infobox_demo(d)
    gauge_demo(d)
    answer = yesno_demo(d)
    msgbox_demo(d, answer)
    textbox_demo(d)
    name = inputbox_demo(d)
    size, weight, city, state, country, last_will1, last_will2, last_will3, \
        last_will4, secret_code = mixedform_demo(d)
    favorite_day = menu_demo(d, name, city, state, country, size, weight,
                             secret_code, last_will1, last_will2, last_will3,
                             last_will4)
    toppings = checklist_demo(d)
    sandwich = radiolist_demo(d)
    date = calendar_demo(d)
    password = passwordbox_demo(d)
    scrollbox_demo(d, name, favorite_day, toppings, sandwich, date, password)

    d.msgbox("""\
Haha. You thought it was over. Wrong. Even more fun is to come!

Now, please select a file you would like to see growing (or not...).""",
             width=75)

    tailbox_demo(d)

    timeout = 2 if params["fast_mode"] else 20
    pause_demo(d, timeout)

    clear_screen(d)
    if not params["fast_mode"]:
        # Rest assured, this is not necessary in any way: it is only a
        # psychological trick to try to give the impression of a reboot (cf.
        # pause_demo(); would be even nicer with a "visual bell")...
        time.sleep(1)


def additional_widgets(d):
    progressbox_demo_with_filepath(d)
    # This can be confusing without any pause if the user specified a regular
    # file.
    time.sleep(1 if params["fast_mode"] else 2)

    mixedgauge_demo(d)
    editbox_demo(d, "/etc/passwd")
    inputmenu_demo(d)
    form_demo(d)
    passwordform_demo(d)
    directory = dselect_demo(d)


def process_command_line():
    global params

    try:
        opts, args = getopt.getopt(sys.argv[1:], "ft",
                                   ["test-suite",
                                    "fast",
                                    "debug",
                                    "debug-file=",
                                    "help",
                                    "version"])
    except getopt.GetoptError as message:
        sys.stderr.write(usage + "\n")
        return ("exit", 1)

    # Let's start with the options that don't require any non-option argument
    # to be present
    for option, value in opts:
        if option == "--help":
            print(usage)
            return ("exit", 0)
        elif option == "--version":
            print("%s %s\n%s" % (progname, progversion, version_blurb))
            return ("exit", 0)

    # Now, require a correct invocation.
    if len(args) != 0:
        sys.stderr.write(usage + "\n")
        return ("exit", 1)

    # Default values for parameters
    params = { "fast_mode": False,
               "testsuite_mode": False,
               "debug": False,
               "debug_filename": default_debug_filename }

    # Get the home directory, if any, and store it in params (often useful).
    root_dir = os.sep           # This is OK for Unix-like systems
    params["home_dir"] = os.getenv("HOME", root_dir)

    # General option processing
    for option, value in opts:
        if option in ("-t", "--test-suite"):
            params["testsuite_mode"] = True
            # --test-suite implies --fast
            params["fast_mode"] = True
        elif option in ("-f", "--fast"):
            params["fast_mode"] = True
        elif option == "--debug":
            params["debug"] = True
        elif option == "--debug-file":
            params["debug_filename"] = value
        else:
            # The options (such as --help) that cause immediate exit
            # were already checked, and caused the function to return.
            # Therefore, if we are here, it can't be due to any of these
            # options.
            assert False, "Unexpected option received from the " \
                "getopt module: '%s'" % option

    return ("continue", None)


# Dummy context manager to make sure the debug file is closed on exit, be it
# normal or abnormal, and to avoid having two code paths, one for normal mode
# and one for debug mode.
class DummyContextManager(contextlib.ContextDecorator):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def main():
    """This demo shows the main features of the pythondialog Dialog class.

    """
    locale.setlocale(locale.LC_ALL, '')

    what_to_do, code = process_command_line()
    if what_to_do == "exit":
        sys.exit(code)

    try:
        # If you want to use Xdialog (pathnames are also OK for the 'dialog'
        # argument), you can use:
        #   d = dialog.Dialog(dialog="Xdialog", compat="Xdialog")
        d = dialog.Dialog(dialog="dialog")
        d.add_persistent_args(["--backtitle", "pythondialog demo"])

        if params["debug"]:
            debug_file = open(params["debug_filename"], "w")
            d.setup_debug(True, file=debug_file)
            demo_context = debug_file
        else:
            demo_context = DummyContextManager()

        with demo_context:
            if params["testsuite_mode"]:
                # Show the additional widgets before the "normal demo", so that
                # I can test new widgets quickly and simply hit Ctrl-C once
                # they've been shown.
                additional_widgets(d)

            # "Normal" demo
            demo(d)
    except dialog.error as exc_instance:
        # The error that causes a PythonDialogErrorBeforeExecInChildProcess to
        # be raised happens in the child process used to run the dialog-like
        # program, and the corresponding traceback is printed right away from
        # that child process when the error is encountered. Therefore, don't
        # print a second, not very useful traceback for this kind of exception.
        if not isinstance(exc_instance,
                          dialog.PythonDialogErrorBeforeExecInChildProcess):
            print(traceback.format_exc(), file=sys.stderr)

        print("Error (see above for a traceback):\n\n{0}".format(
                exc_instance), file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__": main()
