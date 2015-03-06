#!/usr/bin/python

import gendsession

class MySubClassExample(gendsession.GEndSessionListenerBase):
    def end_session_actions(self):
        print "Performing user specified logout actions"

example = MySubClassExample()
example.start()
