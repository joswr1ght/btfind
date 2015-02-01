#!/usr/bin/env python
import pdb

import pygtk
pygtk.require('2.0')

import sys
import gobject
import pango
import gtk
import math
import time
import random
import os
from threading import Thread, Event
from gtk import gdk
import cairo
import struct
import socket
import select
import datetime
import time
sys.path.append("/usr/lib/python2.6/dist-packages/bluetooth")
import _bluetooth as bluez

import speedo
import siggraph
import bthandler
import btfind_ui

if gtk.pygtk_version < (2,3,93):
    print "PyGtk 2.3.93 or later required"
    raise SystemExit

logfd = 0
scanmode = 0

class BTPoller(Thread):
    def __init__(self, ui):
        Thread.__init__(self)
        self.ui = ui

        self.devlist = []

        self.stopthread = Event()

    def run(self):
        global logfd
        global scanmode

        # Bluetooth handling
        dev_id = 0

	try:
	    if (sys.argv[1][0:3] == "hci"):
	        dev_id = int(sys.argv[1][-1])
        except:
            dev_id = 0
        
        try:
            self.sock = bluez.hci_open_dev(dev_id)
        except:
            self.ui.show_error_dlg("Error accessing bluetooth device", 1)
            self.stop()
            return
        
        try:
            self.mode = bthandler.bt_read_inquiry_mode(self.sock)
        except Exception, e:
            self.ui.show_error_dlg("Unable to read inquiry mode.  Please ensure a Bluetooth interface is available that complies with Bluetooth SIG 1.2 or later.", 1)
            self.stop()
            return
        
        if self.mode != 1:
            try:
                result = bthandler.bt_write_inquiry_mode(self.sock, 1)
            except Exception, e:
                self.ui.show_error_dlg("Error writing inquiry mode.", 1)
                self.stop()
                return
            if result != True:
                self.ui.show_error_dlg("Error setting inquiry mode.", 1)
                self.stop()
                return

        # perform a device inquiry on bluetooth device #0
        # The inquiry should last 8 * 1.28 = 10.24 seconds
        # before the inquiry is performed, bluez should flush its cache of
        # previously discovered devices
        flt = bluez.hci_filter_new()
        bluez.hci_filter_all_events(flt)
        bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
        self.sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )
        
        duration = 16
        max_responses = 255
        self.cmd_pkt = struct.pack("BBBBB", 0x33, 0x8b, 0x9e, duration, max_responses)
        
        bluez.hci_send_cmd(self.sock, bluez.OGF_LINK_CTL, bluez.OCF_INQUIRY, self.cmd_pkt)
        
        # Gtk object callback on socket data availability
        # pttimer = gobject.io_add_watch(self.sock, gobject.IO_IN, self.ptr_timeout, self.ui.speedo, self.ui.devlistview)

        while not self.stopthread.isSet():
            ready_to_read, ready_to_write, in_error = select.select([self.sock], [], [], 0.1)

            if len(ready_to_read) < 1:
                continue

            pkt = self.sock.recv(255)
            ptype, event, plen = struct.unpack("BBB", pkt[:3])
            if event == bluez.EVT_INQUIRY_RESULT_WITH_RSSI:
                pkt = pkt[3:]
                nrsp = struct.unpack("B", pkt[0])[0]
    
                for i in range(nrsp):
                    addr = bluez.ba2str( pkt[1+6*i:1+6*i+6] )
                    rssi = struct.unpack("b", pkt[1+13*nrsp+i])[0]
       
                    match = False
                    idev = None
                    details = []
    
                    for dev in self.devlist:
                        if dev[0] == addr:
                            match = True
                            idev = dev
                            details = idev[3]
			    # Update last seen detail
			    details[0][1] = "Last seen: " + str(datetime.datetime.now())
                            break
    
                    if match == False:
                        # Add this entry to the list
			nowstr = str(datetime.datetime.now())
			details = [["First seen: " + nowstr]]
			details[0].append("Last Seen: " + nowstr)
			details[0].append("OUI Vendor: " +
                                bthandler.bt_print_device_manuf(addr[0:8].replace(":","")))

			# retrieve friendly name
                        timeout = 5000 # ms
    
                        try:
                            if self.ui.scanmode == 0:
                                name = bluez.hci_read_remote_name(self.sock, addr, timeout)
                            else:
                                name = "<Not Enumerated>"

                        except bluez.error, e:
                            # Name lookup failed, timeout or I/O error
                            name = "<Unknown>"

                        devclass_raw = struct.unpack ("BBB", 
                                pkt[1+8*nrsp+3*i:1+8*nrsp+3*i+3])
                        devclass_str = bthandler.bt_devclass((int(devclass_raw[1] & 0x1f)), int(devclass_raw[0] >> 2))
    
                        idev = [addr, name, devclass_str]

#                        if (self.ui.scanmode == 0):
#                            try:
#                                s = bluez.SDPSession()
#                                s.connect(addr)
#                                # XXX replace this with brute enumeration 
#                                # (e.g. sdptool records foo)
#                                sdpmatches = s.browse()
#                                s.close()
#                            except bluez.error, e:
#                                print "Error enumerating services"
#                                print e
#                                sdpmatches = []
#                        else:
#                            sdpmatches = []
#
#                        serviceparent = []
#                        for service in sdpmatches:
#                            try:
#                                servclass = bthandler.bt_sdpclass(int("0x" + service["service-classes"][0],16))
#                            except:
#                                servclass = service["service-classes"][0]
#
#                            try:
#                                if service["protocol"] == None:
#                                    servicedet = ["Protocol: Unknown"]
#                                else:
#                                    servicedet = ["Protocol: " + service["protocol"],
#                                        "Channel/PSM: " + str(service["port"]),
#                                         "Service Class: " + servclass]
#                            # Catch exceptions where service["name"] is Null
#                            # This happens on the Wii mote
#                                try:
#                                    serviceparent.append([service["name"], servicedet])
#                                except:
#                                    serviceparent.append(["Unknown Service", servicedet])
#                            except bluez.error, e:
#                                print "Error handling service details"
#                                print e
#
#                        if serviceparent != []:
#                            details.append(["Services", serviceparent])
                        idev.append(details)
                        self.devlist.append(idev)
    
                        # name request cancels inquire, must restart
                        try:
                            bluez.hci_send_cmd(self.sock, bluez.OGF_LINK_CTL, bluez.OCF_INQUIRY, self.cmd_pkt)
                        except e:
                            print e
                            return
                        logfd.write(addr + ", \"" + name + "\", " + "\""+ devclass_str + "\", " + nowstr 
                            + ", \"" + bthandler.bt_print_device_manuf(addr[0:8].replace(":","")) + "\"\n")

                    self.ui.update_row(idev[0], idev[1], idev[2], bthandler.bt_distance(rssi), rssi, details)

                continue
        
            elif (event == bluez.EVT_CMD_STATUS or 
                    event == bluez.EVT_NUM_COMP_PKTS or
                    event == bluez.EVT_CONN_COMPLETE or
                    event == bluez.EVT_DISCONN_COMPLETE or
                    event == bluez.EVT_READ_REMOTE_FEATURES_COMPLETE or
                    event == bluez.EVT_REMOTE_NAME_REQ_COMPLETE or
                    event == bluez.EVT_CMD_COMPLETE):
                    continue
            elif event == bluez.EVT_INQUIRY_COMPLETE:
                bluez.hci_send_cmd(self.sock, bluez.OGF_LINK_CTL, bluez.OCF_INQUIRY, self.cmd_pkt)
                continue

    def stop(self):
        self.stopthread.set()
        self.sock.close()

def openlogfile():
    months=["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    now = time.localtime()
    i=1
    while(True):
        filename="BTFind-" + months[now[1]] + "-" + str(now[2]) + "-" + str(now[0]) + "-" + str(i) + ".csv"
	if not os.path.exists(filename):
            return file(filename, "w")
        else:
            i += 1

def main():
    try:
        global logfd
        gtk.gdk.threads_init()
    
        ui = btfind_ui.BTFindUI()

        logfd = openlogfile()
        logfd.write("bdaddr,\"device name\",\"device class\",discovery time,\"vendor\"\n")
    
        btpoll = BTPoller(ui)
        
        btpoll.start()
    
        gtk.main()
   
    except Exception,e:
        print e

    btpoll.stop()
    btpoll.join()
    
if __name__ == "__main__":
    main()
