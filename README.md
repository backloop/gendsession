# gendsession
Automatically trigger execution of a script during user logout on Gnome based systems using Gnome Session Manager's EndSession DBus interface.

##Description
Triggering a script for execution at login on Gnome based systems is a trivial task, just add the script in the *Startup Applications* dialog and everthing is taken automatically care of.

Triggering a script for execution at logout on Gnome based systems is on the contrary not at all trivial. This script aims to remedy that by taking care of the messy details of the Gnome Session Manager's EndSession DBus signalling.

##Example Use-Case
Automatically unmounting of user-specific encrypted filesystems when the user logs out. This applies to other mounts than /home/$USER as there are already existing tools for auto-mounting private home directories in most distros.

##Usage
`$ ./gendsession.py <path-to-logout-actions-script>`

##Typical Usage: Run both login and logout actions
1. Create a script that performs the login actions, e.g. `login-actions.sh`
2. Create a script that performs the logout actions, e.g. `logout-actions.sh`
3. Create a wrapper script that is added to the *Startup Applications* dialog
```
#!/bin/sh

# Assume that all scripts are located in the same directory as this script
path=$(dirname $(readlink -f $0))

# These actions will be executed during login
$path/login-actions.sh

# This starts a listener for logout signalling and executes the actions during logout
$path/gendsession.py $path/logout-actions.sh
```

##Other Usage: Subclassing
It is also possible to subclass the functionality from within Python scripts if this is desired
```
#!/usr/bin/python

import gendsession

class MySubClassExample(gendsession.GEndSessionListenerBase):
    def end_session_actions(self):
        print "Performing user specified logout actions"

example = MySubClassExample()
example.start()
```

##SUpported Platforms
All Gnome based systems should be supported. Verified on:
* Ubuntu 14.10

##Background
To trigger a script for execution during a logout on Gnome based systems one can register for the Gnome Session Manager's DBus EndSession signals. The main problem is that the Gnome Session Manager DBus interface is largely under-documented and therefore not trivial to understand how to use.

##References
* [Gnome Session Manager DBus interface documentation](https://people.gnome.org/~mccann/gnome-session/docs/gnome-session.html)
* [DBus Python tutorial](http://dbus.freedesktop.org/doc/dbus-python/doc/tutorial.html)
* [DBus Python API](http://dbus.freedesktop.org/doc/dbus-python/api/)
* [DBus Python Examples #1](https://wiki.python.org/moin/DbusExamples)
* [DBus Python Examples #2](http://en.wikibooks.org/wiki/Python_Programming/Dbus)
* [DBus Python glib main loop API](https://developer.gnome.org/pygobject/2.26/class-glibmainloop.html)
* [dbus-monitor - DBus debugging tool](http://dbus.freedesktop.org/doc/dbus-monitor.1.html)
* [d-feet - DBus debugging tool](https://launchpad.net/ubuntu/+source/d-feet)
