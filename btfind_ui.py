#!/usr/bin/env python

import pygtk
pygtk.require('2.0')

import gobject
import pango
import gtk
import math
import time
import random
from gtk import gdk
from types import *

import speedo
import siggraph

def update_timeout(object):
    object.complete_update()
    return True

class BTFindUI:
    def __init__(self):
        global actiongroup

        self.scanmode = 0
        self.target = None

        # Set an update timer for pushing data to the UI
        self.timer = gobject.timeout_add(1000, update_timeout, self)

        # Minimum value we'll see (used as "no update" event on graphs too
        self.mingraphval = -80
        self.minspeedval = -100

        self.win = gtk.Window()
        self.win.set_title('BTFind')
        self.win.connect('delete-event', gtk.main_quit)

        # Overall vbox holds the menu and other panels
        bigvbox = gtk.VBox(homogeneous = False, spacing = 1)
        bigvbox.set_border_width(1)

        self.win.add(bigvbox)

        # Menus
        self.menu_ui = '''
            <ui>
            <menubar name="MenuBar">
              <menu action="File">
                <menuitem action="Quit"/>
              </menu>
              <menu action="Mode">
                <menuitem action="ScanDevices"/>
                <menuitem action="TrackDevices"/>
              </menu>
            </menubar>
            </ui>
        '''

        uimanager = gtk.UIManager()
        accelgroup = uimanager.get_accel_group()
        self.win.add_accel_group(accelgroup)

        actiongroup = gtk.ActionGroup('btfind')
        self.actiongroup = actiongroup

        actiongroup.add_actions([('Quit', gtk.STOCK_QUIT, '_Quit', None,
                                  'Quit btfind', gtk.main_quit),
                                 ('File', None, '_File'),
                                 ('Mode', None, '_Mode')])
        actiongroup.get_action('Quit').set_property('short-label', '_Quit')

        actiongroup.add_radio_actions([('ScanDevices', None, '_Scan Devices',
                                        '<Control>s','Scan Devices', 0),
                                       ('TrackDevices', None, '_Track Devices',
                                        '<Control>t','Track Devices', 1),
                                      ], 0, self.moderadio_cb)

        uimanager.insert_action_group(actiongroup, 0)

        uimanager.add_ui_from_string(self.menu_ui)

        menubar = uimanager.get_widget('/MenuBar')

        # VPane box holds the device list and the graphics
        pvbox = gtk.VPaned()
        self.vpane_button_state = 0
        self.vpane_size = -1
        pvbox.connect('button-press-event', self.vpane_buttonpress)
        pvbox.connect('button-release-event', self.vpane_buttonrelease)
        pvbox.connect('motion-notify-event', self.vpane_motion)

        bigvbox.pack_start(menubar, expand = False, fill = False, padding = 0)
        bigvbox.pack_end(pvbox, expand = True, fill = True, padding = 0)

        # Make the speedo and graph widgets
        self.speedo = speedo.PySpeedoWidget()
        self.speedo.set_drawbg(0)
        self.speedo.set_bounds(self.minspeedval, -10)
        self.speedo.set_pointer(-100)
        self.speedo.set_markpoints(
            [-100, -90, -80, -70, -60, -50, -40, -30, -20, -10],
            [ (1, 0, 0), (1, 0, 0), (1, 0, 0),
              (1, 1, 0), (1, 1, 0), (1, 1, 0),
              (0, 1, 0), (0, 1, 0), (0, 1, 0) ] )

        self.graph = siggraph.PyGrapherWidget()
        self.graph.set_drawbg(0)
        self.graph.set_maxsamples(200)
        self.graph.set_initrange(self.mingraphval, -40)

        # Pack the speedo and graph into their own vbox
        graphvbox = gtk.VBox(homogeneous = False, spacing = 0)

        graphvbox.pack_start(self.speedo, expand = True, fill = True, padding = 0)
        graphvbox.pack_end(self.graph, expand = True, fill = True, padding = 0)

        # Build the devlist tree store
        self.devliststore = gtk.ListStore(str, str, str, str, int, int)
        self.devlistview = gtk.TreeView(model = self.devliststore)

        # Build the cell renderers
        cell = gtk.CellRendererText()
        bacolumn = gtk.TreeViewColumn('Device Address', cell)
        bacolumn.set_cell_data_func(cell, self.table_bacolumn)
        self.devlistview.append_column(bacolumn)
        
        cell = gtk.CellRendererText()
        nmcolumn = gtk.TreeViewColumn('Friendly Name', cell)
        nmcolumn.set_cell_data_func(cell, self.table_nmcolumn)
        self.devlistview.append_column(nmcolumn)
        
        cell = gtk.CellRendererText()
        tpcolumn = gtk.TreeViewColumn('Type', cell)
        tpcolumn.set_cell_data_func(cell, self.table_tpcolumn)
        self.devlistview.append_column(tpcolumn)
        
        cell = gtk.CellRendererText()
        dscolumn = gtk.TreeViewColumn('Distance', cell)
        dscolumn.set_cell_data_func(cell, self.table_dscolumn)
        dscolumn.set_sort_column_id(3)
        self.devlistview.append_column(dscolumn)
        
        cell = gtk.CellRendererText()
        smcolumn = gtk.TreeViewColumn('Samples', cell)
        smcolumn.set_cell_data_func(cell, self.table_smcolumn)
        smcolumn.set_sort_column_id(4)
        self.devlistview.append_column(smcolumn)
        
        cell = gtk.CellRendererText()
        sgcolumn = gtk.TreeViewColumn('Signal', cell)
        sgcolumn.set_cell_data_func(cell, self.table_sgcolumn)
        sgcolumn.set_sort_column_id(5)
        self.devlistview.append_column(sgcolumn)
        
        self.devlistview.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.devlistview.connect('cursor-changed', self.devlistselect)

        # Put it in a scrolling pane
        scrollwin = gtk.ScrolledWindow()
        scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        scrollwin.add_with_viewport(self.devlistview)
        
        scrollwin.set_size_request(-1, 250)

        # Pack the device list into the upper half of the pane
        pvbox.pack1(scrollwin, resize = True, shrink = True)

        # Make the details store, tree, and window
        self.detailstore = gtk.TreeStore(str)
        self.detailview = gtk.TreeView(self.detailstore)
        self.detailcolumn = gtk.TreeViewColumn()
        self.detailcolumn.set_title("Device Details")
        self.detailview.append_column(self.detailcolumn)
        cell = gtk.CellRendererText()
        self.detailcolumn.pack_start(cell, True)
        self.detailcolumn.add_attribute(cell, 'text', 0)

        scrollwin = gtk.ScrolledWindow()
        scrollwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        scrollwin.add_with_viewport(self.detailview)
        scrollwin.set_size_request(500, -1)

        # Pack the lower half of the window in a hbox
        hbox = gtk.HBox(homogeneous = False, spacing = 0)
        hbox.pack_start(graphvbox, expand = True, fill = True, padding = 0)
        hbox.pack_end(scrollwin, expand = True, fill = True, padding = 0)

        # Pack the lower half into the adjustable vbox
        pvbox.pack2(hbox, resize = True, shrink = True)

        self.win.set_gravity(gtk.gdk.GRAVITY_SOUTH_WEST)
        self.win.move(0, 0)
        self.win.set_geometry_hints(min_width = 800, min_height = 460, max_width = 800, max_height = 480)
        self.win.show_all()

        self.dev_id = 0

        self.details = { }

        self.updatelist = [ ]

    def vpane_buttonpress(self, widget, data = None):
        self.vpane_button_state = 1

    def vpane_buttonrelease(self, widget, data = None):
        if self.vpane_button_state == 1:
            if self.vpane_size == -1:
                self.vpane_size = widget.get_position()
                x, y, w, h = widget.get_allocation()
                widget.set_position(h)
            else:
                widget.set_position(self.vpane_size)
                self.vpane_size = -1
    
    def vpane_motion(self, widget, data = None):
        self.vpane_button_state = 2

    def complete_update(self):
        gtk.gdk.threads_enter()

        update_target = 0

        for udev in self.updatelist:
            if udev[0] == self.target:
                self.speedo.set_pointer(udev[5])
                self.graph.add_sample(udev[5])
                update_target = 1

            match = False
            for dev in self.devliststore:
                if dev[0] == udev[0]:
                    dev[3] = udev[3]
                    dev[4] = dev[4] + udev[4]
                    dev[5] = udev[5]
                    match = True
                    break
        
            if match == False:
                self.devliststore.append(udev[0:6])
        
            self.details[udev[0]] = udev[6]

        self.updatelist = [ ]

        # Update the graph and speedo if the selected device has
        # gone inactive
        if not self.target == None and not update_target:
            self.speedo.set_pointer(self.speedo.get_pointer())
            self.graph.add_sample(self.speedo.get_pointer())

        gtk.gdk.threads_leave()

    def update_row(self, addr, name, devclass, distance, rssi, details):
        # Queue an update in the update list, the timer will apply it to the
        # dev list later
        match = False
        for dev in self.updatelist:
            if dev[0] == addr:
                dev[3] = distance
                dev[4] = 1 + dev[4]
                dev[5] = rssi
                dev[6] = details
                match = True
                break

        if match == False:
            self.updatelist.append([addr, name, devclass, distance, 1, rssi, details])

    def moderadio_cb(self, action, current):
        self.scanmode = action.get_current_value()
        print "Changing scan mode to " + str(self.scanmode)

    def getscanmode(self):
        return self.scanmode

    def devlistselect(self, widget):
        #get data from highlighted selection
        treeselection = self.devlistview.get_selection()
        (model, iter) = treeselection.get_selected()
    
        if iter:
            self.target = self.devliststore.get_value(iter, 0)

            # Switch the details over
            self.detailstore.clear()
            self.detailcolumn.set_title("Device Details: %s" % self.target)
            self.populate_details(self.details[self.target])

    def populate_details(self, tree, iter = None):
        if tree == None:
            return

        i = iter
        for x in tree:
            if len(x) <= 1 or not isinstance(x, ListType):
                i = self.detailstore.append(iter, [x])
            else:
                self.populate_details(x, i)

        return i

    # BDADDR
    def table_bacolumn(self, column, cell, model, iter):
        cell.set_property('text', model.get_value(iter, 0))
        return
    
    # Device Name
    def table_nmcolumn(self, column, cell, model, iter):
        cell.set_property('text', model.get_value(iter, 1))
        return
    
    # Device Type (Major/Minor)
    def table_tpcolumn(self, column, cell, model, iter):
        cell.set_property('text', model.get_value(iter, 2))
        return
    
    # Distance
    def table_dscolumn(self, column, cell, model, iter):
        cell.set_property('text', model.get_value(iter, 3))
        return
    
    # Age
    def table_smcolumn(self, column, cell, model, iter):
        cell.set_property('text', "%d" % model.get_value(iter, 4))
        return
    
    # Signal
    def table_sgcolumn(self, column, cell, model, iter):
        cell.set_property('text', "%d" % model.get_value(iter, 5))
        return

    def show_error_dlg(self, error_string, exit = 0):
        gtk.gdk.threads_enter()
        error_dlg = gtk.MessageDialog(type = gtk.MESSAGE_ERROR, message_format = error_string, buttons = gtk.BUTTONS_OK)
        error_dlg.run()
        error_dlg.destroy()
        if exit:
            gtk.main_quit()
        gtk.gdk.threads_leave()

