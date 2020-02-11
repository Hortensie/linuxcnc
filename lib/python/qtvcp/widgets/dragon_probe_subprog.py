#!/usr/bin/env python
import sys
from PyQt5.QtCore import QObject
from qtvcp.core import Action

# Instantiate the libraries with global reference
# STATUS gives us status messages from linuxcnc
# LOG is for running code logging
ACTION = Action()

class Probe_Subprog(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.process()

    def process(self):
        while 1:
            try:
                line = sys.stdin.readline()
            except KeyboardInterrupt:
                break
            if line:
                cmd = line.rstrip().split(' ')
                line = None
                try:
                    error = self.process_command(cmd)
# a successfully completed command will return 1 - None means ignore - anything else is an error
                    if error is not None:
                        if error != 1:
                            ACTION.CALL_MDI("G90")
                            sys.stdout.write("[ERROR] Probe routine returned with error\n")
                        else:
                            sys.stdout.write("COMPLETE\n")
                        sys.stdout.flush()
                except Exception as e:
                    sys.stdout.write("[ERROR] Command Error: {}\n".format(e))
                    sys.stdout.flush()

    def process_command(self, cmd):
        if cmd[0] == 'PROBE':
            command = "o< {} > call {}".format(cmd[1], cmd[2])
            if ACTION.CALL_OWORD(command, 60) == -1:
                return -1
            return 1

####################################
# Testing
####################################
if __name__ == "__main__":
    w = Probe_Subprog()

