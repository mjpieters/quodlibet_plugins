# -*- coding: utf-8 -*-
# Copyright 2012 Martijn Pieters <mj@zopatista.com>
#
# This plugin is needed for quod libet to handle multimedia keys under Mac
# OS X.
# We run a separate process (not a fork!) so we can run a Quartz event loop
# without having to bother with making that work with the GTK event loop.
# There we register a Quartz event tap to listen for the multimedia keys and
# control QL through it's const.CONTROL pipe.
#
# ------------------------------------------------------------------------
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import subprocess
import sys
try:
    from quodlibet.plugins.events import EventPlugin
except ImportError:
    # When executing the event tap process, we may not be able to import
    # quodlibet libraries, which is fine.
    pass
else:
    __all__ = ['OSXMMKey']

    class OSXMMKey(EventPlugin):
        PLUGIN_ID = "OSXMMKey"
        PLUGIN_NAME = _("Mac OS X Multimedia Keys")
        PLUGIN_DESC = _("Enable Mac OS X Multimedia Shortcut Keys.\n\n"
            "Requires the PyObjC bindings (with both the Cocoa and Quartz "
            "framework bridges), and that access for assistive devices "
            "is enabled (see the Universal Access preference pane).")
        PLUGIN_VERSION = "0.1"

        __eventsapp = None

        def enabled(self):
            # Start the event capturing process
            self.__eventsapp = subprocess.Popen((sys.executable, __file__))

        def disabled(self):
            if self.__eventsapp is not None:
                self.__eventsapp.kill()
                self.__eventsapp = None


#
# Quartz event tap, listens for media key events and translates these to 
# control messages for quodlibet.
#


from quodlibet.remote import Remote, RemoteError
from AppKit import NSKeyUp, NSSystemDefined, NSEvent
import Quartz

class MacKeyEventsTap(object):
    def __init__(self):
        self._keyControls = {
            16: 'play-pause',
            19: 'next',
            20: 'previous',
        }

    def eventTap(self, proxy, type_, event, refcon):
        # Convert the Quartz CGEvent into something more useful
        keyEvent = NSEvent.eventWithCGEvent_(event)
        if keyEvent.subtype() is 8: # subtype 8 is media keys
            data = keyEvent.data1()
            keyCode = (data & 0xFFFF0000) >> 16
            keyState = (data & 0xFF00) >> 8
            if keyState == NSKeyUp and keyCode in self._keyControls:
                self.sendControl(self._keyControls[keyCode])

    def sendControl(self, control):
        # Send our control message to QL.
        if not Remote.remote_exists():
            sys.exit()
        try:
            Remote.send_message(control)
        except RemoteError:
            sys.exit()

    @classmethod
    def runEventsCapture(cls):
        tapHandler = cls()
        tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap, # Session level is enough for our needs
            Quartz.kCGHeadInsertEventTap, # Insert wherever, we do not filter
            Quartz.kCGEventTapOptionListenOnly, # Listening is enough
            Quartz.CGEventMaskBit(NSSystemDefined), # NSSystemDefined for media keys
            tapHandler.eventTap,
            None
        )
        # Create a runloop source and add it to the current loop
        runLoopSource = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetCurrent(),
            runLoopSource,
            Quartz.kCFRunLoopDefaultMode
        )
        # Enable the tap
        Quartz.CGEventTapEnable(tap, True)
        # and run! This won't return until we exit or are terminated.
        Quartz.CFRunLoopRun()


if __name__ == '__main__':
    # In the subprocess, capture media key events
    MacKeyEventsTap.runEventsCapture()
