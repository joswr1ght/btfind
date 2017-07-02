import sys
import struct
import bluetooth._bluetooth as bluez
import ouilookup

def bt_print_device_manuf(oui):
    try:
        return ouilookup.ouilkp[oui]
    except Exception,e:
        print e
        return "<Unallocated>"


def bt_print_device_inquiry_list(sock):
    """ void """
    # save current filter
    old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

    # perform a device inquiry on bluetooth device #0
    # The inquiry should last 8 * 1.28 = 10.24 seconds
    # before the inquiry is performed, bluez should flush its cache of
    # previously discovered devices
    flt = bluez.hci_filter_new()
    bluez.hci_filter_all_events(flt)
    bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )

    duration = 16
    max_responses = 255
    cmd_pkt = struct.pack("BBBBB", 0x33, 0x8b, 0x9e, duration, max_responses)
    bluez.hci_send_cmd(sock, bluez.OGF_LINK_CTL, bluez.OCF_INQUIRY, cmd_pkt)

    results = []

    done = False
    while not done:
        pkt = sock.recv(255)
        ptype, event, plen = struct.unpack("BBB", pkt[:3])
        if event == bluez.EVT_INQUIRY_RESULT_WITH_RSSI:
            pkt = pkt[3:]
            nrsp = struct.unpack("B", pkt[0])[0]
            for i in range(nrsp):
                addr = bluez.ba2str( pkt[1+6*i:1+6*i+6] )
                rssi = struct.unpack("b", pkt[1+13*nrsp+i])[0]
                results.append( addr )
        elif event == bluez.EVT_INQUIRY_COMPLETE:
            done = True
        elif event == bluez.EVT_CMD_STATUS:
            status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
            if status != 0:
                done = True
        else:
            print "unrecognized packet type 0x%02x" % ptype


    # restore old filter
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )

    # Results become unique
    set = {}
    map(set.__setitem__, results, [])
    print set.keys()

def bt_read_inquiry_mode(sock):
    """returns the current mode, or -1 on failure"""
    # save current filter
    old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

    # Setup socket filter to receive only events related to the
    # read_inquiry_mode command
    flt = bluez.hci_filter_new()
    opcode = bluez.cmd_opcode_pack(bluez.OGF_HOST_CTL, 
            bluez.OCF_READ_INQUIRY_MODE)
    bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
    bluez.hci_filter_set_event(flt, bluez.EVT_CMD_COMPLETE);
    bluez.hci_filter_set_opcode(flt, opcode)
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )

    # first read the current inquiry mode.
    bluez.hci_send_cmd(sock, bluez.OGF_HOST_CTL, 
            bluez.OCF_READ_INQUIRY_MODE )

    pkt = sock.recv(255)

    status,mode = struct.unpack("xxxxxxBB", pkt)
    if status != 0: mode = -1

    # restore old filter
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
    return mode

def bt_write_inquiry_mode(sock, mode):
    """returns 0 on success, 1 on failure"""
    # save current filter
#    old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

    # Setup socket filter to receive only events related to the
    # write_inquiry_mode command
    flt = bluez.hci_filter_new()
    opcode = bluez.cmd_opcode_pack(bluez.OGF_HOST_CTL, 
            bluez.OCF_WRITE_INQUIRY_MODE)
    bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
    bluez.hci_filter_set_event(flt, bluez.EVT_CMD_COMPLETE);
    bluez.hci_filter_set_opcode(flt, opcode)
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )

    # send the command!
    bluez.hci_send_cmd(sock, bluez.OGF_HOST_CTL, 
            bluez.OCF_WRITE_INQUIRY_MODE, struct.pack("B", mode) )

    pkt = sock.recv(255)

    status = struct.unpack("xxxxxxB", pkt)[0]

#    # restore old filter
#    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
#    if status != 0: return False
    return True

def bt_start_discovery(sock):
    """ void """
    # The inquiry should last 8 * 1.28 = 10.24 seconds
    # before the inquiry is performed, bluez will flush its cache of
    # previously discovered devices
    flt = bluez.hci_filter_new()
    bluez.hci_filter_all_events(flt)
    bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )
    
    duration = 16
    max_responses = 255
    cmd_pkt = struct.pack("BBBBB", 0x33, 0x8b, 0x9e, duration, max_responses)
    bluez.hci_send_cmd(sock, bluez.OGF_LINK_CTL, bluez.OCF_INQUIRY, cmd_pkt)
    return

def bt_sdpclass(sdpclass):
    """ Returns a string describing service class """
    serviceclasses = {
        0x1000 : "SDP Server",
        0x1001 : "Browse Group",
        0x1002 : "Public Browse Group",
        0x1101 : "Serial Port",
        0x1102 : "LAN Access",
        0x1103 : "Dialup Networking",
        0x1104 : "IRMC Sync",
        0x1105 : "OBEX Object Push",
        0x1106 : "OBEX File Transfer",
        0x1107 : "IRMC Sync Command",
        0x1108 : "Ultimate Headset",
        0x1109 : "Cordless Telephone",
        0x110a : "Audio Source",
        0x110b : "Audio Sink",
        0x110c : "AV Remote Target",
        0x110d : "Advanced Audio",
        0x110e : "AV Remote",
        0x110f : "Video Conferencing",
        0x1110 : "Intercom",
        0x1111 : "Fax",
        0x1112 : "Headset Audio Gateway",
        0x1113 : "Wireless Application Protocol",
        0x1114 : "Wireless Applicatio Protocol Client",
        0x1115 : "Personal Area Networking User",
        0x1116 : "Network Application Profile",
        0x1117 : "Group Networking",
        0x1118 : "Direct Printing",
        0x1119 : "Reference Printing",
        0x111a : "Imaging",
        0x111b : "Imaging Responder",
        0x111c : "Imaging Archive",
        0x111d : "Imaging Reference Objects",
        0x111e : "Handsfree",
        0x111f : "Handsfree Audio Gateway",
        0x1120 : "Direct Print Reference Objects",
        0x1121 : "Reflected UI",
        0x1122 : "Basic Printing",
        0x1123 : "Printing Status",
        0x1124 : "Human Interface Device",
        0x1125 : "Handheld Contactless Card Terminal",
        0x1126 : "Handheld Contactless Card Terminal Print",
        0x1127 : "Handheld Contactless Card Terminal Scanning",
        0x1129 : "Video Conferencing Gateway",
        0x112a : "Unrestricted Digital Information",
        0x112b : "Unrestricted Digital Information",
        0x112c : "Audio Visual",
        0x112d : "Service Application Profile",
        0x112e : "Phone Book Access Profile",
        0x112f : "Phone Book Access Profile",
        0x1200 : "Plug-and-Play Information",
        0x1201 : "Generic Networking",
        0x1202 : "Generic File Transfer",
        0x1203 : "Generic Audio",
        0x1204 : "Generic Telephony",
        0x1205 : "Universal Plug-and-Play",
        0x1206 : "Universal Plug-and-Play IP",
        0x1300 : "Universal Plug-and-Play PAN",
        0x1301 : "Universal Plug-and-Play LAP",
        0x1302 : "Universal Plug-and-Play L2CAP",
        0x1303 : "Video Source",
        0x1304 : "Video Sink",
        0x1305 : "Video Distribution",
        0x2112 : "Apple Agent"
        }
    try:
        return serviceclasses[sdpclass]
    except:
        return "Unknown (" + str(sdpclass) + ")"


def bt_devclass(major,minor):
    """ Returns a string describing device major/minor class """
    majorlkp = {
        0 : "Miscellaneous",
        1 : "Computer",
        2 : "Phone",
        3 : "LAN Access",
        4 : "Audio/Video",
        5 : "Peripheral",
        6 : "Imaging",
        7 : "Wearable",
        8 : "Toy",
	9 : "Medical",
        31 : "Uncategorized"
    }

    majorminorlkp = {
        (0,0) : "Uncategorized",
        (0,63) : "Uncategorized",
        (1,0) : "Uncategorized",
        (1,1) : "Desktop workstation",
        (1,2) : "Server",
        (1,3) : "Laptop",
        (1,4) : "Handheld sized PC",
        (1,5) : "Palm sized PC",
        (1,6) : "Wearable",
        (2,0) : "Uncategorized",
        (2,1) : "Cellular",
        (2,2) : "Cordless",
        (2,3) : "Smart phone",
        (2,4) : "Wired modem or voice gateway",
        (2,5) : "Common ISDN Access",
        (2,6) : "Sim Card Reader",
        (3,0) : "Fully available",
        (3,8) : "1 - 17% utilized",
        (3,16) : "17 - 33% utilized",
        (3,24) : "33 - 50% utilized",
        (3,32) : "50 - 67% utilized",
        (3,40) : "67 - 83% utilized",
        (3,48) : "83 - 99% utilized",
        (3,7) : "No service available",
        (4,0) : "Uncategorized",
        (4,1) : "Wearable headset device",
        (4,2) : "Hands-free device",
        (4,3) : "Reserved",
        (4,4) : "Microphone",
        (4,5) : "Loudspeaker",
        (4,6) : "Headphones",
        (4,7) : "Portable audio",
        (4,8) : "Car audio",
        (4,9) : "Set-top box",
        (4,10) : "HiFi Audio Device",
        (4,11) : "VCR",
        (4,12) : "Video Camera",
        (4,13) : "Camcorder",
        (4,14) : "Video monitor",
        (4,15) : "Video Display and Loudspeaker",
        (4,16) : "Video Conferencing",
        (4,17) : "Reserved",
        (4,18) : "Gaming/Toy",
        (5,0) : "Not keyboard/not pointing device",
	(5,1) : "Joystick",
	(5,2) : "Gamepad",
	(5,3) : "Remote Control",
	(5,4) : "Sensing Device",
	(5,5) : "Digitizer Tablet",
	(5,6) : "Card Reader",
        (5,16) : "Keyboard",
        (5,17) : "Keyboard/Joystick",
        (5,18) : "Keyboard/Gamepad",
        (5,19) : "Keyboard/Remote Control",
        (5,20) : "Keyboard/Sensing Device",
        (5,21) : "Keyboard/Digitizer Tablet",
        (5,22) : "Keyboard/Card Reader",
        (5,32) : "Pointing Device",
        (5,33) : "Pointing Device/Joystick",
        (5,34) : "Pointing Device/Gamepad",
        (5,35) : "Pointing Device/Remote Control",
        (5,36) : "Pointing Device/Sensing Device",
        (5,37) : "Pointing Device/Digitizer Tablet",
        (5,38) : "Pointing Device/Card Reader",
        (5,48) : "Combo keyboard/pointing device",
        (5,49) : "Keyboard/Pointing Device/Joystick",
        (5,50) : "Keyboard/Pointing Device/Gamepad",
        (5,51) : "Keyboard/Pointing Device/Remote Control",
        (5,52) : "Keyboard/Pointing Device/Sensing Device",
        (5,53) : "Keyboard/Pointing Device/Digitizer Tablet",
        (5,54) : "Keyboard/Pointing Device/Card Reader",
        (6,4) : "Display",
        (6,5) : "Display",
        (6,6) : "Display",
        (6,7) : "Display",
        (6,8) : "Camera",
        (6,9) : "Camera",
        (6,10) : "Camera",
        (6,11) : "Camera",
        (6,12) : "Display/Camera",
        (6,13) : "Display/Camera",
        (6,14) : "Display/Camera",
        (6,15) : "Display/Camera",
        (6,16) : "Scanner",
        (6,17) : "Scanner",
        (6,18) : "Scanner",
        (6,19) : "Scanner",
        (6,20) : "Display/Scanner",
        (6,21) : "Display/Scanner",
        (6,22) : "Display/Scanner",
        (6,23) : "Display/Scanner",
        (6,24) : "Camera/Scanner",
        (6,25) : "Camera/Scanner",
        (6,26) : "Camera/Scanner",
        (6,27) : "Camera/Scanner",
        (6,28) : "Display/Camera/Scanner",
        (6,29) : "Display/Camera/Scanner",
        (6,30) : "Display/Camera/Scanner",
        (6,31) : "Display/Camera/Scanner",
        (6,32) : "Printer",
        (6,33) : "Printer",
        (6,34) : "Printer",
        (6,35) : "Printer",
        (6,36) : "Display/Printer",
        (6,37) : "Display/Printer",
        (6,38) : "Display/Printer",
        (6,39) : "Display/Printer",
        (6,40) : "Camera/Printer",
        (6,41) : "Camera/Printer",
        (6,42) : "Camera/Printer",
        (6,43) : "Camera/Printer",
        (6,44) : "Display/Camera/Printer",
        (6,45) : "Display/Camera/Printer",
        (6,46) : "Display/Camera/Printer",
        (6,47) : "Display/Camera/Printer",
        (6,48) : "Scanner/Printer",
        (6,49) : "Scanner/Printer",
        (6,50) : "Scanner/Printer",
        (6,51) : "Scanner/Printer",
        (6,52) : "Display/Scanner/Printer",
        (6,53) : "Display/Scanner/Printer",
        (6,54) : "Display/Scanner/Printer",
        (6,55) : "Display/Scanner/Printer",
        (6,56) : "Camera/Scanner/Printer",
        (6,57) : "Camera/Scanner/Printer",
        (6,58) : "Camera/Scanner/Printer",
        (6,59) : "Camera/Scanner/Printer",
        (6,60) : "Display/Camera/Scanner/Printer",
        (6,61) : "Display/Camera/Scanner/Printer",
        (6,62) : "Display/Camera/Scanner/Printer",
        (6,63) : "Display/Camera/Scanner/Printer",
        (7,1) : "Wrist Watch",
        (7,2) : "Pager",
        (7,3) : "Jacket",
        (7,4) : "Helmet",
        (7,5) : "Glasses",
        (8,1) : "Robot",
        (8,2) : "Vehicle",
        (8,3) : "Doll/Action Figure",
        (8,4) : "Controller",
        (8,5) : "Game",
        (9,0) : "Unidentified",
        (9,1) : "Blood Pressure Monitor",
        (9,2) : "Thermometer",
        (9,3) : "Weighing Scale",
        (9,4) : "Glucose Meter",
        (9,5) : "Pulse Oximiter",
        (9,6) : "Heart/Pulse Rate Monitor",
        (9,7) : "Medical Data Display",
        (31,0) : "Uncategorized/Unknown"
    }

    try:
        majorminor = majorminorlkp[(major,minor)]
    except:
        print "Unrecognized major minor combination: (" + str(major) + "/" + str(minor) + ")"
        return majorlkp[major]

    return majorlkp[major] + "/" + majorminorlkp[(major,minor)]

def bt_distance(rssi):
    propconst = 3 # Propagation Constant, 2-4
    refrssi = -55 # Measured RSSI 1M from transmitter (assumes 2.5 mW)
    return "%d'" % (pow(10,(refrssi-rssi)/float((10*propconst))) * 3.28)

def bt_init():
    """ returns the socket or False on error """
    dev_id = 0
    
    try:
        sock = bluez.hci_open_dev(dev_id)
    except:
        print "error accessing bluetooth device..."
        return False
    
    try:
        mode = bt_read_inquiry_mode(sock)
    except Exception, e:
        print "Error reading inquiry mode.  "
        print e
        return False
    
    if mode != 1:
        try:
            result = bt_write_inquiry_mode(sock, 1)
        except Exception, e:
            print "Error writing inquiry mode."
            print e
            return False
        if result != 0:
            print "Error setting inquiry mode, result: %d" % result
        return False

    return sock

