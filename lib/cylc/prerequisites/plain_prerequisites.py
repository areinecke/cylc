#!/usr/bin/env python

#C: THIS FILE IS PART OF THE CYLC SUITE ENGINE.
#C: Copyright (C) 2008-2013 Hilary Oliver, NIWA
#C:
#C: This program is free software: you can redistribute it and/or modify
#C: it under the terms of the GNU General Public License as published by
#C: the Free Software Foundation, either version 3 of the License, or
#C: (at your option) any later version.
#C:
#C: This program is distributed in the hope that it will be useful,
#C: but WITHOUT ANY WARRANTY; without even the implied warranty of
#C: MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#C: GNU General Public License for more details.
#C:
#C: You should have received a copy of the GNU General Public License
#C: along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re, sys

# PREREQUISITES: A collection of messages representing the prerequisite
# conditions for a task, each of which can be "satisfied" or not.  An
# unsatisfied prerequisite becomes satisfied if it matches a satisfied
# output message from another task (via the cylc requisite broker).

class plain_prerequisites(object):

    TAG_RE = re.compile( '^\w+\.(\d+).*$' ) # to extract T from "foo.T succeeded" etc.

    def __init__( self, owner_id, ict=None ):
        self.labels = {}   # labels[ message ] = label
        self.messages = {}   # messages[ label ] = message 
        self.satisfied = {}    # satisfied[ label ] = True/False
        self.satisfied_by = {}   # self.satisfied_by[ label ] = task_id
        self.auto_label = 0
        self.owner_id = owner_id
        self.ict = ict

    def add( self, message, label = None ):
        # Add a new prerequisite message in an UNSATISFIED state.
        if self.ict:
            task = re.search( r'(.*).(.*) ', message)
            if task.group:
                try:
                    if (int(task.group().split(".")[1]) < int(self.ict) and 
                        int(task.group().split(".")[1]) != 1):
                        return 
                except IndexError:
                    pass
        if label:
            pass
        else:
            self.auto_label += 1
            label = str( self.auto_label )

        if message in self.labels:
            # IGNORE A DUPLICATE PREREQUISITE (the same trigger must
            # occur in multiple non-conditional graph string sections).
            # Warnings disabled pending a global check across all
            # prerequisites held by a task.
            ##print >> sys.stderr, "WARNING, " + self.owner_id + ": duplicate prerequisite: " + message
            return

        self.messages[ label ] = message
        self.labels[ message ] = label
        self.satisfied[label] = False
        self.satisfied_by[label] = None

    def remove( self, message ):
        lbl = self.labels[message]
        del self.labels[message]
        del self.messages[lbl]
        del self.satisfied[lbl]
        del self.satisfied_by[lbl]

    def all_satisfied( self ):
        return not ( False in self.satisfied.values() ) 
            
    def satisfy_me( self, outputs ):
        # Can any completed outputs satisfy any of my prerequisites?
        for label, message in self.messages.items():
            if label in self.satisfied and message in outputs:
                self.satisfied[ label ] = True
                self.satisfied_by[ label ] = outputs[message] # owner_id

    def get_satisfied_by( self ):
        return self.satisfied_by

    def count( self ):
        # how many messages are stored
        return len( self.satisfied.keys() )

    def dump( self ):
        # return an array of strings representing each message and its state
        res = []
        for key in self.satisfied:
            res.append( [ self.messages[key], self.satisfied[ key ] ]  )
        return res

    def set_all_satisfied( self ):
        for label in self.messages:
            self.satisfied[ label ] = True

    def set_all_unsatisfied( self ):
        for label in self.messages:
            self.satisfied[ label ] = False

    def get_target_tags( self ):
        """Return a list of cycle times target by each prerequisite,
        including each component of conditionals."""
        tags = []
        for label, msg in self.messages.items():
            m = re.match( self.__class__.TAG_RE, msg )
            if m:
                tags.append( m.groups()[0] )
        return tags 

