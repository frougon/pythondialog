#! /usr/bin/env python

# demo.py --- A simple demonstration program for pythondialog
# Copyright (C) 2000  Robb Shecter, Sultanbek Tezadov
# Copyright (C) 2002, 2004  Florent Rougon
#
# This program is in the public domain.

"""Demonstration program for pythondialog.

This is a simple program demonstrating the possibilities offered by
the pythondialog module (which is itself a Python interface to the
well-known dialog utility, or any other program compatible with
dialog).

Please have a look at the documentation for the `handle_exit_code'
function in order to understand the somewhat relaxed error checking
policy for pythondialog calls in this demo.

"""

import sys, os, os.path, time, string, dialog

FAST_DEMO = 0


# XXX We should handle the new DIALOG_HELP and DIALOG_EXTRA return codes here.
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
        return 0
    else:
        return 1                        # code is d.DIALOG_OK
        

def infobox_demo(d):
    # Exit code thrown away to keey this demo code simple (however, real
    # errors are propagated by an exception)
    d.infobox("One moment, please. Just wasting some time here to "
              "show you the infobox...")
    
    if FAST_DEMO:
        time.sleep(0.5)
    else:
        time.sleep(3)


def gauge_demo(d):
    d.gauge_start("Progress: 0%", title="Still testing your patience...")
    for i in range(1, 101):
	if i < 50:
	    d.gauge_update(i, "Progress: %d%%" % i, update_text=1)
	elif i == 50:
	    d.gauge_update(i, "Over %d%%. Good." % i, update_text=1)
	elif i == 80:
	    d.gauge_update(i, "Yeah, this boring crap will be over Really "
                           "Soon Now.", update_text=1)
	else:
            d.gauge_update(i)

        if FAST_DEMO:
            time.sleep(0.01)
        else:
            time.sleep(0.1)
    d.gauge_stop()
    

def yesno_demo(d):
    # Return the answer given to the question (also specifies if ESC was
    # pressed)
    return d.yesno("Do you like this demo?")
    

def msgbox_demo(d, answer):
    if answer == d.DIALOG_OK:
        d.msgbox("Excellent! Press OK to see the source code.")
    else:
        d.msgbox("Well, feel free to send your complaints to /dev/null!")


def textbox_demo(d):
    d.textbox("demo.py", width=76)


def inputbox_demo(d):
    # If the user presses Cancel, he is asked (by handle_exit_code) if he
    # wants to exit the demo. We loop as long as he tells us he doesn't want
    # to do so.
    while 1:
        (code, answer) = d.inputbox("What's your name?", init="Snow White")
        if handle_exit_code(d, code):
            break
    return answer


def menu_demo(d):
    while 1:
        (code, tag) = d.menu(
            "What's your favorite day of the week?",
            width=60,
            choices=[("Monday", "Being the first day of the week..."),
                     ("Tuesday", "Comes after Monday"),
                     ("Wednesday", "Before Thursday day"),
                     ("Thursday", "Itself after Wednesday"),
                     ("Friday", "The best day of all"),
                     ("Saturday", "Well, I've had enough, thanks"),
                     ("Sunday", "Let's rest a little bit")])
        if handle_exit_code(d, code):
            break
    return tag


def checklist_demo(d):
    while 1:
        # We could put non-empty items here (not only the tag for each entry)
        (code, tag) = d.checklist(text="What sandwich toppings do you like?",
                                  height=15, width=54, list_height=7, 
                                  choices=[("Catsup", "",             0),
                                           ("Mustard", "",            0),
                                           ("Pesto", "",              0),
                                           ("Mayonaise", "",          1),
                                           ("Horse radish","",        1),
                                           ("Sun-dried tomatoes", "", 1)],
                                  title="Do you prefer ham or spam?",
                                  backtitle="And now, for something "
                                  "completely different...")
        if handle_exit_code(d, code):
            break
    return tag


def radiolist_demo(d):    
    while 1:
        (code, tag) = d.radiolist(
            "What's your favorite kind of sandwich?", 
            width=65,
            choices=[("Hamburger", "2 slices of bread, a steak...", 0),
                     ("Hotdog", "doesn't bite any more", 0),
                     ("Burrito", "no se lo que es", 0),
                     ("Doener", "Huh?", 0),
                     ("Falafel", "Erm...", 0),
                     ("Bagel", "Of course!", 0),
                     ("Big Mac", "Ah, that's easy!", 1),
                     ("Whopper", "Erm, sorry", 0),
                     ("Quarter Pounder", 'called "le Big Mac" in France', 0),
                     ("Peanut Butter and Jelly", "Well, that's your own "
                      "business...", 0),
                     ("Grilled cheese", "And nothing more?", 0)])
        if handle_exit_code(d, code):
            break
    return tag
    

def calendar_demo(d):
    while 1:
        (code, date) = d.calendar("When do you think Debian sarge will be "
                                  "released?", year=0)
        if handle_exit_code(d, code):
            break
    return date


def passwordbox_demo(d):
    while 1:
        (code, password) = d.passwordbox("What is your root password, "
                                         "so that I can crack your system "
                                         "right now?")
        if handle_exit_code(d, code):
            break
    return password


def comment_on_sarge_release_date(day, month, year):
    if year < 2004 or (year == 2004 and month <= 3):
        return "Mmm... what about a little tour on http://www.debian.org/?"
    elif year == 2004 and month <= 4:
        return """\
Damn, how optimistic! You don't know much about Debian, do you?"""
    elif year == 2004 and month <= 7:
        return """\
Well, good guess. But who knows what the future reserves to us? ;-)"""
    elif year == 2004:
        return """\
Oh, well. That's plausible. But please, please don't depress
other people with your pronostics... ;-)"""
    else:
        return "Hey, you're a troll! (or do you know Debian *so* well? ;-)"


def scrollbox_demo(d, name, favorite_day, toppings, sandwich, date,
                   password):
    day, month, year = date
    msg = """\
Here are some vital statistics about you:

Name: %s
Favorite day of the week: %s
Favorite sandwich toppings:%s
Favorite sandwich: %s

You estimate Debian sarge's release to happen around %04u-%02u-%02u.
%s

Your root password is: ************************** (looks good!)""" \
     % (name, favorite_day,
        string.join([''] + toppings, "\n    "),
        sandwich, year, month, day,
        comment_on_sarge_release_date(day, month, year))
    d.scrollbox(msg, height=20, width=75, title="Great Report of the Year")


def fselect_demo(d):
    while 1:
        root_dir = os.sep               # This is OK for UNIX systems
        dir = os.getenv("HOME", root_dir)
        # Make sure the directory we chose ends with os.sep() so that dialog
        # shows its contents right away
        if dir and dir[-1] != os.sep:
            dir = dir + os.sep

        (code, path) = d.fselect(dir, 10, 50,
                                 title="Cute little file to show as "
                                 "in a `tail -f'")
        if handle_exit_code(d, code):
            if not os.path.isfile(path):
                d.scrollbox("Hmm. Didn't I ask you to select a *file*?",
                            width=50, height=10)
            else:
                break
    return path


def tailbox_demo(d, file):
    d.tailbox(file, 20, 60, title="You are brave. You deserve the "
              "right to rest, now." )


def demo():
#   If you want to use Xdialog (pathnames are also OK for the 'dialog'
#   argument)
#   d = dialog.Dialog(dialog="Xdialog", compat="Xdialog")
    d = dialog.Dialog(dialog="dialog")

    d.add_persistent_args(["--backtitle", "pythondialog demo"])

    infobox_demo(d)
    gauge_demo(d)
    answer = yesno_demo(d)
    msgbox_demo(d, answer)
    textbox_demo(d)
    name = inputbox_demo(d)
    favorite_day = menu_demo(d)
    toppings = checklist_demo(d)
    sandwich = radiolist_demo(d)
    date = calendar_demo(d)
    password = passwordbox_demo(d)
    scrollbox_demo(d, name, favorite_day, toppings, sandwich, date, password)

    d.scrollbox("""\
Haha. You thought it was over. Wrong. Even More fun is to come!
(well, depending on your definition on "fun")

Now, please select a file you would like to see growing (or not...).""",
                width=75)

    file = fselect_demo(d)
    tailbox_demo(d, file)

    d.scrollbox("""\
Now, you're done. No, I'm not kidding.

So, why the hell are you sitting here instead of rushing on that EXIT
button? Ah, you did like the demo. Hmm... are you feeling OK? ;-)""",
                width=75)


def main():
    """This demo shows the main features of the pythondialog Dialog class.

    """
    try:
        demo()
    except dialog.error, exc_instance:
        sys.stderr.write("Error:\n\n%s\n" % exc_instance.complete_message())
        sys.exit(1)
        
    sys.exit(0)


if __name__ == "__main__": main()
