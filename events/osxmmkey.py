# -*- coding: utf-8 -*-
# Copyright 2012 Martijn Pieters <mj@zopatista.com>
#
# This plugin is needed for quod libet to handle multimedia keys under Mac
# OS X.
# We run a separate process (not a fork!) so we can run a quartz event loop
# without having to bother with making that work with the GTK event loop.
# There we register a Quartz event tap to listen for the multimedia keys and
# control QL through it's const.CONTROL pipe.
#
# ------------------------------------------------------------------------
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

try:
    from quodlibet import const
    from quodlibet.plugins.events import EventPlugin
except ImportError:
    definePlugin = False
else:
    definePlugin = True

import os
import signal
import subprocess
import sys
from AppKit import NSSystemDefined, NSEvent
import Quartz


__all__ = ['OSXMMKey']


class MacKeyEventsTap(object):
    def __init__(self, control):
        self._keyControls = {
            16: 'play-pause',
            19: 'next',
            20: 'previous',
        }
        self.controlPath = control

    def eventTap(self, proxy, type_, event, refcon):
        keyEvent = NSEvent.eventWithCGEvent_(event)
        if keyEvent.subtype() is 8:
            data = keyEvent.data1()
            keyCode = (data & 0xFFFF0000) >> 16
            keyState = (data & 0xFF00) >> 8
            if keyState == 11 and keyCode in self._keyControls: # Key up
                self.sendControl(self._keyControls[keyCode])

    def sendControl(self, control):
        if not os.path.exists(self.controlPath):
            sys.exit()
        try:
            # This is a total abuse of Python! Hooray!
            # Totally copied from the quodlibet command line handler too..
            signal.signal(signal.SIGALRM, lambda: "" + 2)
            signal.alarm(1)
            f = file(self.controlPath, "w")
            signal.signal(signal.SIGALRM, signal.SIG_IGN)
            f.write(control)
            f.close()
        except (OSError, IOError, TypeError):
            sys.exit()

    @classmethod
    def runEventsCapture(cls, control):
        tapHandler = cls(control)
        tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            Quartz.CGEventMaskBit(NSSystemDefined),
            tapHandler.eventTap,
            None
        )
        runLoopSource = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetCurrent(),
            runLoopSource,
            Quartz.kCFRunLoopDefaultMode
        )
        Quartz.CGEventTapEnable(tap, True)
        Quartz.CFRunLoopRun()


if definePlugin:
    class OSXMMKey(EventPlugin):
        PLUGIN_ID = "OSXMMKey"
        PLUGIN_NAME = _("Mac OS X Multimedia Keys")
        PLUGIN_DESC = _("Enable Mac OS X Multimedia Shortcut Keys")
        PLUGIN_VERSION = "0.1"

        __eventsapp = None

        def enabled(self):
            self.__eventsapp = subprocess.Popen((sys.executable, __file__, const.CONTROL))

        def disabled(self):
            if self.__eventsapp is not None:
                self.__eventsapp.kill()

if __name__ == '__main__':
    MacKeyEventsTap.runEventsCapture(sys.argv[1])
