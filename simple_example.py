#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# simple_example.py --- Short and straightforward example using pythondialog
# Copyright (C) 2013  Florent Rougon
#
# This program is in the public domain.

import sys, locale
from dialog import Dialog

# This is almost always a good thing to do at the beginning of your programs.
locale.setlocale(locale.LC_ALL, '')

# Initialize a dialog.Dialog instance
d = Dialog(dialog="dialog")
d.set_background_title("A Simple Example")


# *****************************************************************************
# *                             'msgbox' example                              *
# *****************************************************************************
d.msgbox("""\
This is a very simple example of a program using pythondialog.

Contrary to what is done in demo.py, the Dialog exit code for the Escape key \
is not checked after every call, therefore it is not so easy to exit from \
this program as it is for the demo. The goal here is to show basic \
pythondialog usage in its simplest form.

With not too old versions of dialog, the size of dialog boxes is \
automatically computed when one passes width=0 and height=0 to the \
widget call. This is the method used here in most cases.""",
         width=0, height=0, title="'msgbox' example")


# *****************************************************************************
# *                              'yesno' example                              *
# *****************************************************************************

# The 'no_collapse=True' used in the following call tells dialog not to replace
# multiple contiguous spaces in the text string into a single space.
code = d.yesno("""\
The 'yesno' widget allows one to display a text with two buttons beneath, \
which by default are labelled "Yes" and "No".

The return value is not simply True or False: for consistency with \
dialog and the other widgets, the return code allows to distinguish \
between:

  Yes         Dialog.OK         (equal to the string "ok")
  No          Dialog.CANCEL     (equal to the string "cancel")
  <Escape>    Dialog.ESC        when the Escape key is pressed
  Help        Dialog.HELP       when help_button=True was passed and the
                                help button is pressed (only for 'menu' in
                                pythondialog 2.x)
  Extra       Dialog.EXTRA      when extra_button=True was passed and the
                                extra button is pressed

The DIALOG_ERROR exit status of dialog has no equivalent in this list, \
because pythondialog translates it into an exception.""",
               width=0, height=0, title="'yesno' example", no_collapse=True)

if code == d.OK:
    msg = "You chose the 'Yes' button in the previous dialog."
elif code == d.CANCEL:
    msg = "You chose the 'No' button in the previous dialog."
elif code == d.ESC:
    msg = "You pressed the Escape key in the previous dialog."
else:
    msg = "Unexpected exit code from d.yesno(). Please report a bug."

d.msgbox(msg, width=50, height=7)


# *****************************************************************************
# *                            'inputbox' example                             *
# *****************************************************************************
code, user_input = d.inputbox("""\
The 'inputbox' widget can be used to read input (as a string) from the user. \
You can test it now:""",
                              init="Initial contents",
                              width=0, height=0, title="'inputbox' example")

if code == d.OK:
    msg = "Your input in the previous dialog was '{0}'.".format(user_input)
elif code == d.CANCEL:
    msg = "You chose the 'Cancel' button in the previous dialog."
elif code == d.ESC:
    msg = "You pressed the Escape key in the previous dialog."
else:
    msg = "Unexpected exit code from d.inputbox(). Please report a bug."

d.msgbox("{0}\n\nThis little sample program is now finished. Bye bye!".format(
        msg), width=0, height=0, title="Bye bye!")

sys.exit(0)
