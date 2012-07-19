#!/usr/bin/env python

#C: THIS FILE IS PART OF THE CYLC FORECAST SUITE METASCHEDULER.
#C: Copyright (C) 2008-2012 Hilary Oliver, NIWA
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

import subprocess
import os, sys, re
#from port_scan import SuiteIdentificationError
from cylc_pyro_client import client
from Jinja2Support import Jinja2Process, TemplateSyntaxError, TemplateError
from version import cylc_version, cylc_dir
from registration import dbgetter, RegistrationError
from hostname import hostname, is_remote_host
from owner import is_remote_user

# To ensure that users are aware of this compat processing info is 
# always printed for suites that use it, but to stderr so as not to
# interfere with results.

class compat( object ):
    def __init__( self, suite, suiterc, verbose, debug ):
        self.verbose = verbose
        self.debug = debug
        self.suite = suite
        self.suiterc = suiterc
        self.required_version = None
        self.explicit = False

        self.cylc_top_dir = os.path.dirname( cylc_dir )

        self.messages = [ 'Cylc version reinvocation on ' + hostname ]

    def get_suite( self ):
        return self.suite, self.suiterc

    def get_version( self ):
        if self.required_version:
            return self.required_version
        else:
            return "version not specified"

    def is_compatible( self ):
        if not self.required_version or self.required_version == cylc_version:
            return True
        else:
            return False

    def available( self ):
        # (print to stderr so user can just parse cylc versions)
        print >> sys.stderr, "Cylc versions installed under", self.cylc_top_dir + ':'
        for entry in os.listdir( self.cylc_top_dir ):
            if not entry.startswith( 'cylc-' ):
                continue
            if os.path.exists( os.path.join( self.cylc_top_dir, entry, 'bin', 'cylc' )):
                print entry

    def execute( self ):
        if self.is_compatible():
            return

        self.messages.append( '  Invoked:  cylc-' + cylc_version + ' (' + cylc_dir + ')')
        self.messages.append( '  Required: cylc-' + self.required_version )

        # re-invoke the command (sys.argv) using the required cylc version

        # guess location of the required cylc
        new_cylc_dir = os.path.join( self.cylc_top_dir, 'cylc-' + self.required_version )
        self.messages.append( 'Assuming parallel cylc installations,' )

        self.messages.append( '  reinvoking command with ' + new_cylc_dir )

        # full path to new cylc command
        new_cylc = os.path.join( new_cylc_dir, 'bin', 'cylc')

        if not self.explicit:
            # construct the command to re-invoke
            command_path = sys.argv[0]     # /path/to/this/cylc/bin/cylc-validate
            command_name = os.path.basename( command_path ) # cylc-validate
            # strip off initial 'cylc-' if it exists (may not be, e.g. gcylc SUITE) 
            command_name = re.sub( '^cylc-', '', command_name ) # validate
            command = [new_cylc, command_name] + sys.argv[1:] 
        else:
            command = [new_cylc] + sys.argv

        maxlen = 0
        for item in self.messages:
            if len(item) > maxlen:
                maxlen = len(item)
        border = '-' * maxlen 
        print >> sys.stderr, border
        for item in self.messages:
            print >> sys.stderr, item
        print >> sys.stderr, border

        try:
            # this blocks until the command completes
            retcode = subprocess.call( command )
            sys.exit(retcode)
        except OSError, x:
            sys.exit( 'ERROR: Unable to invoke ' + new_cylc )

class compat_explicit( compat ):
    def __init__( self, required_version ):
        compat.__init__(self, None, None, False, False )
        self.required_version = required_version
        self.explicit = True

class compat_file( compat ):
    """Determine version compatibility given a suite.rc file"""

    def __init__( self, suite, suiterc, verbose, debug ):
        # (suite arg required by derived class compat_reg)

        compat.__init__( self, suite, suiterc, verbose, debug )

        try:
            f = open( suiterc, 'r' )
        except IOError, x:
            if self.debug:
                raise
            sys.exit( "ERROR: unable to open the suite.rc file." )
        flines = f.readlines()
        f.close()

        # Here we must process with Jinja2 before checking the first two
        # lines, to allow use of the cylc version number as a Jinja2
        # variable (for use in multiple places):
        #====
        # #!Jinja2
        # {% set CYLC_VERSION=4.2.2 %}
        # #!{{CYLC_VERSION}}
        # # ...
        #----
        # This will be processed to:
        #====
        # #!Jinja2
        # #!cylc-4.2.2
        # # ...
        #----

        try:
            # (this will do nothing for non Jinja2 suites)
            suiterclines = Jinja2Process( flines, os.path.dirname(suiterc), False )
            # if this fails due to a Jinja2 error, carry on in order to
            # prevent commands such as edit from working...
        except TemplateSyntaxError, x:
            lineno = x.lineno + 1  # (flines array starts from 0)
            print >> sys.stderr, 'Jinja2 Template Syntax Error, line', lineno
            print >> sys.stderr, flines[x.lineno]
            print >> sys.stderr, 'Continuing cylc version check without Jinja2'
            suiterclines = flines
            #if debug:
            #    raise
            #raise SystemExit(str(x))
        except TemplateError, x:
            print >> sys.stderr, 'Jinja2 Template Error'
            print >> sys.stderr, 'Continuing cylc version check without Jinja2'
            suiterclines = flines
            #if debug:
            #    raise
            #raise SystemExit(x)

        line0 = suiterclines[0]
        line1 = suiterclines[1]

        # check for "#!cylc-x.y.z" (not being strict about the form of
        # x.y.z because of unofficial releases):
        m = re.match( '^#!(cylc-.*)$', line0 )
        if m:
            # first line specifies cylc version
            z = m
        elif re.match( '^#![jJ]inja2\s*', line0 ):
            # First line specified Jinja2
            # Try second line for cylc version.
            z = re.match( '^#!(cylc-.*)$', line1 )
        else:
            z = None
        if z:
            self.required_version = re.sub( '^.*cylc-', '', z.groups()[0] )  # e.g. 4.1.1


class compat_reg( compat_file ):
    """Determine version compatibility given a registered suite name"""

    def __init__( self, reg, db, verbose, debug ):
        dbg = dbgetter( db )
        self.db = dbg.db
        try:
            # this will also de-reference a suite name alias 
            suite, suiterc = dbg.get_suite( reg )
        except RegistrationError, x:
            if debug:
                raise
            raise SystemExit(x)
        compat_file.__init__( self, suite, suiterc, verbose, debug )

    def get_rcfiles( self ):
        return self.db.get_rcfiles( self.suite )

class compat_pyro( compat ):
    """Determine version compatibility given a running suite name"""

    def __init__( self, suite, owner, host, pfile, verbose, debug ):
        compat.__init__( self, suite, None, verbose, debug )

        # de-alias the suite name, for local suites
        if not is_remote_host( host ) and \
                not is_remote_user( owner ):
            dbg = dbgetter()
            try:
                self.suite, junk = dbg.get_suite( suite )
            except RegistrationError, x:
                if debug:
                    raise
                raise SystemExit(x)

        try:
            proxy = client( self.suite, owner=owner, \
                    host=host, pfile=pfile ).get_proxy( 'remote' )
        except Exception, x:
            if debug:
                raise
            raise SystemExit(x)
        self.required_version = proxy.get_cylc_version()


