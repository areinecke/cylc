#!/usr/bin/env python

from SuiteControl import ControlAppBase
import gtk
import os, re
import gobject
import helpwindow
from xstateview import xupdater
#from warning_dialog import warning_dialog, info_dialog
import cycle_time
from cylc_xdot import xdot_widgets

class ControlGraph(ControlAppBase):
    """
Dependency graph based GUI suite control interface.
    """
    def __init__(self, suite, owner, host, port, suite_dir, logging_dir,
            imagedir, readonly=False ):

        ControlAppBase.__init__(self, suite, owner, host, port,
                suite_dir, logging_dir, imagedir, readonly=False )

        self.userguide_item.connect( 'activate', helpwindow.userguide, True )

        self.x = xupdater( self.suite, self.owner, self.host, self.port,
                self.label_mode, self.label_status, self.label_time, self.xdot )
        self.x.start()

    def get_control_widgets(self ):
        self.xdot = xdot_widgets()
        self.xdot.widget.connect( 'clicked', self.on_url_clicked )
        self.xdot.graph_disconnect_button.connect( 'toggled', self.toggle_graph_disconnect )
        return self.xdot.get()

    def toggle_graph_disconnect( self, w ):
        if w.get_active():
            self.x.graph_disconnect = True
            w.set_label( 'REconnect' )
        else:
            self.x.graph_disconnect = False
            w.set_label( 'DISconnect' )
        return True

    def on_url_clicked( self, widget, url, event ):
        if event.button != 3:
            return False
        if url == 'KEY':
            # graph key node
            return

        m = re.match( 'base:SUBTREE:(.*)', url )
        if m:
            #print 'SUBTREE'
            task_id = m.groups()[0]
            self.right_click_menu( event, task_id, type='collapsed subtree' )
            return

        m = re.match( 'base:(.*)', url )
        if m:
            #print 'BASE GRAPH'
            task_id = m.groups()[0]
            #warning_dialog( 
            #        task_id + "\n"
            #        "This task is part of the base graph, taken from the\n"
            #        "suite config file (suite.rc) dependencies section, \n" 
            #        "but it does not currently exist in the running suite." ).warn()
            self.right_click_menu( event, task_id, type='base graph task' )
            return

        # URL is task ID
        #print 'LIVE TASK'
        self.right_click_menu( event, url, type='live task' )

    def delete_event(self, widget, event, data=None):
        self.x.quit = True
        return ControlAppBase.delete_event(self, widget, event, data )

    def click_exit( self, foo ):
        self.x.quit = True
        return ControlAppBase.click_exit(self, foo )

    def right_click_menu( self, event, task_id, type='live task' ):
        print '------------>', type
        name, ctime = task_id.split('%')

        menu = gtk.Menu()
        menu_root = gtk.MenuItem( task_id )
        menu_root.set_submenu( menu )

        timezoom_item_direct = gtk.MenuItem( 'Cycle-Time Zoom to ' + ctime )
        timezoom_item_direct.connect( 'activate', self.focused_timezoom_direct, ctime )

        timezoom_item = gtk.MenuItem( 'Cycle-Time Zoom to Range' )
        timezoom_item.connect( 'activate', self.focused_timezoom_popup, task_id )

        if type == 'collapsed subtree':
            title_item = gtk.MenuItem( 'Subtree: ' + task_id )
            title_item.set_sensitive(False)
            menu.append( title_item )
            menu.append( gtk.SeparatorMenuItem() )

            expand_item = gtk.MenuItem( 'Expand Subtree' )
            menu.append( expand_item )
            expand_item.connect( 'activate', self.expand_subtree, task_id )
    
            menu.append( timezoom_item_direct )
            menu.append( timezoom_item )

        else:

            title_item = gtk.MenuItem( 'Task: ' + task_id )
            title_item.set_sensitive(False)
            menu.append( title_item )

            menu.append( gtk.SeparatorMenuItem() )

            collapse_item = gtk.MenuItem( 'Collapse Subtree' )
            menu.append( collapse_item )
            collapse_item.connect( 'activate', self.collapse_subtree, task_id )

            menu.append( timezoom_item_direct )
            menu.append( timezoom_item )

        if type == 'live task':
            menu.append( gtk.SeparatorMenuItem() )

            menu_items = self.get_right_click_menu_items( task_id )
            for item in menu_items:
                menu.append( item )

        menu.show_all()
        menu.popup( None, None, None, event.button, event.time )

        # TO DO: popup menus are not automatically destroyed and can be
        # reused if saved; however, we need to reconstruct or at least
        # alter ours dynamically => should destroy after each use to
        # prevent a memory leak? But I'm not sure how to do this as yet.)

        return True

    def collapse_subtree( self, w, id ):
        self.x.collapse.append(id)
        self.x.action_required = True

    def expand_subtree( self, w, id ):
        self.x.collapse.remove(id)
        self.x.action_required = True

    def expand_all_subtrees( self, w ):
        del self.x.collapse[:]
        self.x.action_required = True

    def rearrange( self, col, n ):
        cols = self.ttreeview.get_columns()
        for i_n in range(0,len(cols)):
            if i_n == n: 
                cols[i_n].set_sort_indicator(True)
            else:
                cols[i_n].set_sort_indicator(False)
        # col is cols[n]
        if col.get_sort_order() == gtk.SORT_ASCENDING:
            col.set_sort_order(gtk.SORT_DESCENDING)
        else:
            col.set_sort_order(gtk.SORT_ASCENDING)
        self.ttreestore.set_sort_column_id(n, col.get_sort_order()) 

    def create_main_menu( self ):
        ControlAppBase.create_main_menu(self)

        expand_item = gtk.MenuItem( '_Expand All Subtrees' )
        self.view_menu.append( expand_item )
        expand_item.connect( 'activate', self.expand_all_subtrees )

        graph_range_item = gtk.MenuItem( 'Cycle-Time _Zoom' )
        self.view_menu.append( graph_range_item )
        graph_range_item.connect( 'activate', self.graph_time_zoom_popup )

        key_item = gtk.MenuItem( 'Toggle Graph _Key' )
        self.view_menu.append( key_item )
        key_item.connect( 'activate', self.toggle_key )


    def toggle_key( self, w ):
        self.x.show_key = not self.x.show_key
        self.x.action_required = True

    def focused_timezoom_popup( self, w, id ):

        window = gtk.Window()
        window.modify_bg( gtk.STATE_NORMAL, 
                gtk.gdk.color_parse( self.log_colors.get_color()))
        window.set_border_width(5)
        window.set_title( "Cycle-Time Zoom")

        vbox = gtk.VBox()

        name, ctime = id.split('%')
        # TO DO: do we need to check that oldeset_ctime is defined yet?
        diff_pre = cycle_time.diff_hours( ctime, self.x.oldest_ctime )
        diff_post = cycle_time.diff_hours( self.x.newest_ctime, ctime )

        # TO DO: error checking on date range given
        box = gtk.HBox()
        label = gtk.Label( 'Pre (hours)' )
        box.pack_start( label, True )
        start_entry = gtk.Entry()
        start_entry.set_text(str(diff_pre))
        box.pack_start (start_entry, True)
        vbox.pack_start( box )

        box = gtk.HBox()
        label = gtk.Label( 'Post (hours)' )
        box.pack_start( label, True )
        stop_entry = gtk.Entry()
        stop_entry.set_text(str(diff_post))
        box.pack_start (stop_entry, True)
        vbox.pack_start( box )

        cancel_button = gtk.Button( "_Cancel" )
        cancel_button.connect("clicked", lambda x: window.destroy() )

        stop_button = gtk.Button( "_Apply" )
        stop_button.connect("clicked", self.focused_timezoom, 
               ctime, start_entry, stop_entry )

        #help_button = gtk.Button( "_Help" )
        #help_button.connect("clicked", helpwindow.stop_guide )

        hbox = gtk.HBox()
        hbox.pack_start( stop_button, False )
        hbox.pack_end( cancel_button, False )
        #hbox.pack_end( help_button, False )
        vbox.pack_start( hbox )

        window.add( vbox )
        window.show_all()

    def focused_timezoom_direct( self, w, ctime ):
        self.x.start_ctime = ctime
        self.x.stop_ctime = ctime
        self.x.action_required = True
        self.x.best_fit = True

    def graph_time_zoom_popup( self, w ):
        window = gtk.Window()
        window.modify_bg( gtk.STATE_NORMAL, 
                gtk.gdk.color_parse( self.log_colors.get_color()))
        window.set_border_width(5)
        window.set_title( "Time Zoom")

        vbox = gtk.VBox()

        # TO DO: error checking on date range given
        box = gtk.HBox()
        label = gtk.Label( 'Start (YYYYMMDDHH)' )
        box.pack_start( label, True )
        start_entry = gtk.Entry()
        start_entry.set_max_length(10)
        if self.x.oldest_ctime:
            start_entry.set_text(self.x.oldest_ctime)
        box.pack_start (start_entry, True)
        vbox.pack_start( box )

        box = gtk.HBox()
        label = gtk.Label( 'Stop (YYYYMMDDHH)' )
        box.pack_start( label, True )
        stop_entry = gtk.Entry()
        stop_entry.set_max_length(10)
        if self.x.newest_ctime:
            stop_entry.set_text(self.x.newest_ctime)
        box.pack_start (stop_entry, True)
        vbox.pack_start( box )

        cancel_button = gtk.Button( "_Cancel" )
        cancel_button.connect("clicked", lambda x: window.destroy() )

        stop_button = gtk.Button( "_Apply" )
        stop_button.connect("clicked", self.graph_time_zoom, 
                start_entry, stop_entry )

        #help_button = gtk.Button( "_Help" )
        #help_button.connect("clicked", helpwindow.stop_guide )

        hbox = gtk.HBox()
        hbox.pack_start( stop_button, False )
        hbox.pack_end( cancel_button, False )
        #hbox.pack_end( help_button, False )
        vbox.pack_start( hbox )

        window.add( vbox )
        window.show_all()

    def graph_time_zoom(self, w, start_e, stop_e):
        self.x.start_ctime = start_e.get_text()
        self.x.stop_ctime = stop_e.get_text()
        self.x.action_required = True

    def focused_timezoom(self, w, focus_ctime, start_e, stop_e):
        pre_hours = start_e.get_text()
        post_hours = stop_e.get_text()
        self.x.start_ctime = cycle_time.decrement( focus_ctime, pre_hours )
        self.x.stop_ctime = cycle_time.increment( focus_ctime, post_hours )
        self.x.action_required = True

class StandaloneControlGraphApp( ControlGraph ):
    # For a ControlApp not launched by the gcylc main app: 
    # 1/ call gobject.threads_init() on startup
    # 2/ call gtk.main_quit() on exit

    def __init__(self, suite, owner, host, port, suite_dir, logging_dir, imagedir, readonly=False ):
        gobject.threads_init()
        ControlGraph.__init__(self, suite, owner, host, port, suite_dir, logging_dir, imagedir, readonly )
 
    def delete_event(self, widget, event, data=None):
        ControlGraph.delete_event( self, widget, event, data )
        gtk.main_quit()

    def click_exit( self, foo ):
        ControlGraph.click_exit( self, foo )
        gtk.main_quit()