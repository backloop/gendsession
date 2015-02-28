#!/usr/bin/python

# 
# Copyright (c) 2015 Pablo Cases, 
# Distributed under the MIT License.
# (See accompanying file LICENSE file or 
# copy at http://opensource.org/licenses/MIT)
# 

import sys
import os
from dbus.mainloop.glib import DBusGMainLoop
import dbus
import gobject
import datetime
import signal
import subprocess
import logging
import logging.handlers
import inspect

class GEndSessionListenerBase(object):

    # override this method when subclassing
    # this method contains the actions performed during logout/"Gnome EndSession"
    def end_session_actions(self):
        # According to Gnome Session Manager docs:
        # "The client must not attempt to interact with the user [...]. 
        # The application will be given a maxium of ten seconds to perform 
        # any actions required for a clean shutdown."
        raise NotImplementedError()
    
    # start() is a blocking method and returns only
    # during logout or if interrupted by a Unix signal
    def start(self):
	# signals can only be received while the event loop is running
        self.__loop = gobject.MainLoop()
        self.__loop.run()
        
        # run actions when interrupted by a Unix signal
        if self.interrupted:
            self.end_session_actions()
   
        self.logger.info("Terminated")
 
    def __init__(self):
        # will be set to True if a Unix signal is caught and handled
        self.interrupted = False
	
        # handle Unix signals
        #  (SIGKILL and SIGSTOP cannot be caught, blocked, or ignored)
        signal.signal(signal.SIGHUP, self.__signal_handler)
        signal.signal(signal.SIGINT, self.__signal_handler) # ctrl-c
        signal.signal(signal.SIGQUIT, self.__signal_handler) # ctrl-\
        signal.signal(signal.SIGTERM, self.__signal_handler)
        signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        signal.signal(signal.SIGUSR2, signal.SIG_IGN)
        signal.signal(signal.SIGTSTP, self.__signal_handler) # ctrl-z
        # the remaining signals are considered fatal and are left unhandled

        # create the logger object
        FORMAT = os.path.basename(inspect.getfile(self.__class__)) + ": %(message)s"
        self.logger = logging.getLogger()
        formatter = logging.Formatter(FORMAT)
        handler = logging.handlers.SysLogHandler(address = "/dev/log")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        
        # must be setup to receive signals
        DBusGMainLoop(set_as_default=True)
        
        # connect to the appropriate bus
        session_bus = dbus.SessionBus()
        
        # create the proxy session manager objects for calling methods
        session_manager = session_bus.get_object("org.gnome.SessionManager",
        					 "/org/gnome/SessionManager")
        self.__session_manager_iface = dbus.Interface(session_manager,
            dbus_interface="org.gnome.SessionManager")
        
        # example: diplays the logout dialog
        #session_manager_iface.Logout(0)
        
        # registers a client with the session manager
        self.__client_id = self.__session_manager_iface.RegisterClient("", "")
        #self.logger.debug("Gnome Session Manager Client ID = %s" % self.__client_id)
        
        # create the proxy session manager client objects for calling methods
        session_client = session_bus.get_object("org.gnome.SessionManager", 
                                                self.__client_id)
        self.__session_client_private_iface = dbus.Interface(session_client, 
                    dbus_interface="org.gnome.SessionManager.ClientPrivate")
        
        # Introspectable interfaces define a property 'Introspect' that
        # will return an XML string that describes the object's interface
        #introspection_iface = dbus.Interface(
        #    session_client,
        #    dbus.INTROSPECTABLE_IFACE,
        #)
        #self.logger.debug(introspection_iface.Introspect())
        # NOTE: The org.gnome.SessionManager.ClientPrivate is not displayed for Introspect() calls
       
        session_bus.add_signal_receiver(self.__query_end_session_handler,
        	signal_name = "QueryEndSession",
        	dbus_interface = "org.gnome.SessionManager.ClientPrivate",
        	bus_name = "org.gnome.SessionManager")
        
        session_bus.add_signal_receiver(self.__end_session_handler,
        	signal_name = "EndSession",
        	dbus_interface = "org.gnome.SessionManager.ClientPrivate",
        	bus_name = "org.gnome.SessionManager")
        
        session_bus.add_signal_receiver(self.__cancel_end_session_handler,
        	signal_name = "CancelEndSession",
        	dbus_interface = "org.gnome.SessionManager.ClientPrivate",
        	bus_name = "org.gnome.SessionManager")
        
        session_bus.add_signal_receiver(self.__stop_handler,
        	signal_name = "Stop",
        	dbus_interface = "org.gnome.SessionManager.ClientPrivate",
        	bus_name = "org.gnome.SessionManager")

        self.logger.info("Initialized")

        
    def __teardown(self):
        self.__loop.quit()
        self.__session_manager_iface.UnregisterClient(self.__client_id)
        self.logger.info("Terminated DBus connections")
    
    #
    # Handle Unix signals
    #
    def __signal_handler(self, signum, stack):
        self.logger.info("Received shell signal: %s" % signum)
	# cannot call end_session_actions here as this may include
        # subprocess.call() or equivalent that is not permitted during signal handling
        # delay execution of the actions until executing the main thread
        self.interrupted = True
        self.__teardown()

    #
    # Methods defined in org.gnome.SessionManager.ClientPrivate
    #
    def __end_session_response(self, ok=True):
        if ok:
            self.logger.info("Calling DBus method:  EndSessionResponse(True, \"\")")
            self.__session_client_private_iface.EndSessionResponse(True, "")
        else:
            # NOTE: calling EndSessionResponse(False) does not inhibit logout on Ubuntu 14.10...
            self.logger.info("Calling DBus method:  EndSessionResponse(False, \"Not ready\")")
            self.__session_client_private_iface.EndSessionResponse(False, "Not ready")
    
    #
    # Signals defined in org.gnome.SessionManager.ClientPrivate
    # flags defined in GsmClientEndSessionFlag
    #       https://git.gnome.org/browse/gnome-session/tree/gnome-session/gsm-client.h
    # flags == 0: normal logout
    # flags == 1: Forced logout and content of EndSessionResponse will be ignored
    #
    def __query_end_session_handler(self, flags):
        self.logger.info("Received DBus signal: QueryEndSession(%d)" % flags)
        # ignore flags, always agree on the QueryEndSesion
        self.__end_session_response(True)
    
    def __end_session_handler(self, flags):
        self.logger.info("Received DBus signal: EndSession(%d)" % flags)
        self.end_session_actions()
        self.__end_session_response(True)
    
    def __cancel_end_session_handler(self):
        self.logger.info("Received DBus signal: CancelEndSession")
        #NOTE: ignored for now, i.e. known limitation
    
    def __stop_handler(self):
        self.logger.info("Received DBus signal: Stop")
        self.__teardown()
    
#
# Gnome End Session Listener 
#
class GEndSessionListener(GEndSessionListenerBase):
    
    def __init__(self, cmdline):
        self.cmdline = cmdline
        super(GEndSessionListener, self).__init__()

    def end_session_actions(self):
        self.logger.debug("Performing user specified logout actions (%s)" % self.cmdline)

	cmd = self.cmdline[0]
        if not os.path.isabs(cmd):
            self.cmdline.pop(0)
            self.cmdline.insert(0, "./%s" % cmd)

        # NOTE: returncode is not checked as EndSessionResponse(False) does not
        # appear to abort the logout process.
        subprocess.call(self.cmdline)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: %s <end-session-script> [end-session-script-args]" % sys.argv[0]
        print
        print "          end-session-script refers to the path to the executable script "
        print "          to be run when the Gnome Session ends."
        print 
        exit(1)        
        
    cmdline = sys.argv[1:]
    #if not (os.path.isfile(end_session_script) and os.access(end_session_script, os.X_OK)):
    if not (os.access(cmdline[0], os.F_OK) and os.access(cmdline[0], os.X_OK)):
        print "The file '%s'  does not exist or is not an executable. Abort." % cmdline[0]
        exit(1)

    listener = GEndSessionListener(cmdline)
    listener.start()
