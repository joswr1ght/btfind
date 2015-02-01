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
try:
    import cairo
except ImportError:
    pass

def progress_timeout(object):
    x, y, w, h = object.allocation
    object.window.invalidate_rect((0,0,w,h),False)
    return True

class PySpeedoWidget(gtk.Widget):
    __gsignals__ = { 'realize': 'override',
                     'expose-event' : 'override',
                     'size-allocate': 'override',
                     'size-request': 'override',}

    def __init__(self):
        gtk.Widget.__init__(self)
        self.draw_gc = None

        self.siglabel = self.create_pango_layout("Signal Level")
        self.sigfont = "sans serif"

        self.timer = gobject.timeout_add (750, progress_timeout, self)

        self.min = 0
        self.max = 0
        self.pointer = 0

        self.drawbg = 0

    def set_bounds(self, minb, maxb):
        self.min = minb
        self.max = maxb

    def set_pointer(self, ptr):
        if ptr > self.max:
            ptr = self.max
        elif ptr < self.min:
            ptr = self.min
        self.pointer = ptr

    def set_label(self, label, font = "sans serif"):
        self.siglabel = self.create_pango_layout(label)
        self.sigfont = font

    def set_drawbg(self, drawbg):
        self.drawbg = drawbg

    def set_markpoints(self, values, colors):
        self.arccolors = colors
        self.arcvalues = values

        self.arcvpango = []

        self.arcvmax = 0

    def get_pointer(self):
        return self.pointer
                                           
    def do_realize(self):
        self.set_flags(self.flags() | gtk.REALIZED)
        self.window = gdk.Window(self.get_parent_window(),
                                 width=self.allocation.width,
                                 height=self.allocation.height,
                                 window_type=gdk.WINDOW_CHILD,
                                 wclass=gdk.INPUT_OUTPUT,
                                 event_mask=self.get_events() | gdk.EXPOSURE_MASK)
        if not hasattr(self.window, "cairo_create"):
            self.draw_gc = gdk.GC(self.window,
                                  line_width=5,
                                  line_style=gdk.SOLID,
                                  join_style=gdk.JOIN_ROUND)

        self.window.set_user_data(self)
        self.style.attach(self.window)
        self.style.set_background(self.window, gtk.STATE_NORMAL)
        self.window.move_resize(*self.allocation)

    def do_size_request(self, requisition):
        requisition.width = 400
        requisition.height = 300

    def do_size_allocate(self, allocation):
        self.allocation = allocation
        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)

        # Update the font description
        pxsize = min(allocation.width, allocation.height) / 10
        self.siglabel.set_font_description(pango.FontDescription("%s %dpx" % (self.sigfont, pxsize)))

        # Update the arc text size
        self.arcvpango = []
        pxsize = min(allocation.width, allocation.height) / 15
        for v in self.arcvalues:
            layout = self.create_pango_layout("%d" % v)
            layout.set_font_description(pango.FontDescription("%s %dpx" % (self.sigfont, pxsize)))
            self.arcvpango.append(layout)

            fontw, fonth = layout.get_pixel_size()
            if max(fontw, fonth) > self.arcvmax:
                self.arcvmax = max(fontw, fonth)

        self.arcvmax = self.arcvmax * 0.85

    def _expose_gdk(self, event):
        # pango_size = font_size_pix * PANGO_SCALE * 72 / fontconfig_dpi; 
        x, y, w, h = self.allocation
        self.layout = self.create_pango_layout('no cairo')
        fontw, fonth = self.layout.get_pixel_size()
        self.style.paint_layout(self.window, self.state, False,
                                event.area, self, "label",
                                (w - fontw) / 2, (h - fonth) / 2,
                                self.layout)

    def _expose_cairo(self, event, cr):
        x, y, w, h = self.allocation

        arcwidth = (min(w, h) / 10)
        r = (min(w, h) * 0.70) - (arcwidth * 1.5)

        cr.set_line_width(arcwidth)

        hofft = arcwidth * 2

        slices = len(self.arccolors)

        # Background
        if self.drawbg:
            pat = cairo.LinearGradient(0, h, w, h)
            pat.add_color_stop_rgba(0, 1.0, 0xfd / 255.0, 0x3e / 255.0, 1.0)
            pat.add_color_stop_rgba(0.33, 1.0, 0xfd / 255.0, 0xa4 / 255.0, 1.0)
            pat.add_color_stop_rgba(0.66, 1.0, 0xfd / 255.0, 0xa4 / 255.0, 1.0)
            pat.add_color_stop_rgba(1, 1.0, 0xfd / 255.0, 0x3e / 255.0, 1.0)
            cr.rectangle(0, 0, w, h)
            cr.set_source(pat)
            cr.fill()

        # dropshadow
        cr.set_source_rgba(0, 0, 0, 0.2)
        cr.arc(w/2, h - hofft, r - 8, math.pi, 2 * math.pi)
        cr.stroke()

        # Draw the colored arcs
        for l in range(0, len(self.arccolors)):
            arc_sperc = float(self.arcvalues[l] - self.min) / float(self.max - self.min)
            arc_start = (math.pi * arc_sperc) - (math.pi)
            arc_eperc = float(self.arcvalues[l + 1] - self.min) / float(self.max - self.min)
            arc_end = (math.pi * arc_eperc) - (math.pi)

            (ar, ag, ab) = self.arccolors[l]
            cr.set_source_rgb(ar, ag, ab)

            cr.arc(w/2, h - hofft, r, arc_start, arc_end)
            cr.stroke()

        # Draw the outlines
        cr.set_source_rgb(0, 0.0, 0.0)

        # Inner and outer arcs
        cr.set_line_width(2)
        cr.arc(w/2, h - hofft, r - (arcwidth / 2), math.pi, 2 * math.pi)
        cr.stroke()
        cr.set_line_width(4)
        cr.arc(w/2, h - hofft, r + (arcwidth / 2), math.pi, 2 * math.pi)
        cr.stroke()

        # Draw the radial lines and text
        cr.set_line_width(2)
        for l in range(0, len(self.arcvalues)):
            arc_sperc = float(self.arcvalues[l] - self.min) / float(self.max - self.min)
            larc = (math.pi * arc_sperc)

            x1 = w/2 + (r - (arcwidth / 2)) * math.cos(larc - math.pi)
            y1 = h - hofft + (r - (arcwidth / 2)) * math.sin(larc - math.pi)

            x2 = w/2 + (r + (arcwidth / 2)) * math.cos(larc - math.pi)
            y2 = h - hofft + (r + (arcwidth / 2)) * math.sin(larc - math.pi)

            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.stroke()

            tr = r - (arcwidth / 2) - (self.arcvmax) - 4

            xt = w/2 + (tr * math.cos(larc - math.pi))
            yt = h - hofft + (tr * math.sin(larc - math.pi))
        
            fontw, fonth = self.arcvpango[l].get_pixel_size()
            cr.move_to(xt - (fontw / 2), yt - (fonth/2))
            cr.update_layout(self.arcvpango[l])
            cr.show_layout(self.arcvpango[l])

        # Draw the arrow
        if (self.min != 0 and self.max != 0):
            ptr_perc = float(self.pointer - self.min) / float(self.max - self.min)

            # Scale the percentage to between -pi/2 and pi/2
            ptr_arc = (math.pi * ptr_perc) - (math.pi * 0.5)
            #ptr_arc = 0.25 * math.pi

            cr.save()

            offt = -4
            if ptr_arc >= 0:
                offt = 4

            cr.translate(w/2, h - hofft)
            cr.rotate(ptr_arc)
            cr.translate((w/2 * -1) + offt, (h/2 * -1) + offt)

            cr.set_line_width(1)
            cr.move_to(w/2, h/2 + (arcwidth * 0.75))
            cr.line_to(w/2 - (arcwidth / 2), h/2)
            cr.line_to(w/2, (h/2) - r)
            cr.line_to(w/2 + (arcwidth / 2), h/2)
            cr.line_to(w/2, h/2 + (arcwidth * 0.75))

            cr.set_source_rgba(0, 0, 0, 0.2)
            cr.fill()

            cr.translate(offt * -1, offt * -1)
            cr.move_to(w/2, h/2 + (arcwidth * 0.75))
            cr.line_to(w/2 - (arcwidth / 2), h/2)
            cr.line_to(w/2, (h/2) - r)
            cr.line_to(w/2 + (arcwidth / 2), h/2)
            cr.line_to(w/2, h/2 + (arcwidth * 0.75))
            cr.set_source_rgb(0.1, 0.1, 0.1) 
            cr.fill()

            cr.set_source_rgb(0.9, 0.9, 0.9)
            cr.arc(w/2, h/2, arcwidth / 15, 0, 2 * math.pi)
            cr.fill()

            cr.restore()

        # Draw the main label, fix if our best-guess ends up over
        fontw, fonth = self.siglabel.get_pixel_size()
        fy = h + fonth - hofft + (arcwidth / 2)
        if fy + fonth > h:
            fy = h - fonth
        cr.move_to((w/2) - (fontw / 2), fy)
        cr.update_layout(self.siglabel)
        cr.show_layout(self.siglabel)

    def do_expose_event(self, event):
        self.chain(event)
        try:
            cr = self.window.cairo_create()
        except AttributeError:
            return self._expose_gdk(event)
        return self._expose_cairo(event, cr)

