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

class PyGrapherWidget(gtk.Widget):
    __gsignals__ = { 'realize': 'override',
                     'expose-event' : 'override',
                     'size-allocate': 'override',
                     'size-request': 'override',}

    def __init__(self):
        gtk.Widget.__init__(self)
        self.draw_gc = None

        self.linecolor = None
        self.linethickness = None

        self.drawbg = 0
        self.bgcolor = None

        self.font = "sans serif"

        self.maxsamples = 50
        
        self.linecolor = (1, 0, 0)
        
        self.samples = []

        self.minval = None
        self.maxval = None

        self.linescale = 10

    def set_drawbg(self, drawbg, bgcolor = None):
        self.drawbg = drawbg
        self.bgcolor = bgcolor

    def set_font(self, font):
        self.font = font

    def set_maxsamples(self, maxsamples):
        self.samples = []
        self.maxsamples = maxsamples

        for i in range(0, maxsamples):
            self.samples.append(None)

        self.minval = None
        self.maxval = None

    def set_initrange(self, minval, maxval):
        self.minval = minval
        self.maxval = maxval

    def set_linescale(self, scale):
        self.linescale = scale

    def add_sample(self, sample):
        self.samples.append(sample)
        self.samples = self.samples[(self.maxsamples * -1):]

        if self.minval == None:
            self.minval = sample
        if self.maxval == None:
            self.maxval = sample

        self.minval = int(min(self.minval, sample))
        self.maxval = int(max(self.maxval, sample))

        if self.window != None:
            x, y, w, h = self.allocation
            self.window.invalidate_rect((0,0,w,h), False)

    def reset(self):
        self.samples = []
        self.minval = None
        self.maxval = None

    def set_line(self, linecolor, linethickness):
        self.linecolor = linecolor
        self.linethickness = linethickness
                                           
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
        requisition.width = 100
        requisition.height = 200

    def do_size_allocate(self, allocation):
        self.allocation = allocation
        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)

    def _expose_gdk(self, event):
        x, y, w, h = self.allocation
        self.layout = self.create_pango_layout('no cairo')
        fontw, fonth = self.layout.get_pixel_size()
        self.style.paint_layout(self.window, self.state, False,
                                event.area, self, "label",
                                (w - fontw) / 2, (h - fonth) / 2,
                                self.layout)

    def _expose_cairo(self, event, cr):
        x, y, w, h = self.allocation

        # To leave room for the ltext top and bottom
        graphh = h - 15
        graphy = 5
        # derived after the labels
        graphw = 0
        graphx = 0

        if self.drawbg:
            cr.save()
            cr.set_source_rgb(self.bgcolor[0], self.bgcolor[1], self.bgcolor[2])
            cr.rectangle(0, 0, w, h)
            cr.fill()
            cr.restore()

        if self.minval == None or self.maxval == None:
            return

        # Background - figure out the steps and labels
        start_val = 0
        for x in range(self.minval, self.minval - self.linescale, -1):
            if (x % self.linescale) == 0:
                start_val = x
                break

        num_rows = 0

        # Calculate the number of rows, the text, and the size of the text elements
        # so we can figure out how much space we need on the top and bottom
        # of the bounding box
        last_val = start_val
        while (last_val < self.maxval):
            num_rows = num_rows + 1
            last_val = last_val + self.linescale

        num_rows = max(1, num_rows)

        labelhpix = (graphh / 1.1) / num_rows
        rowpix = (graphh / float(num_rows))

        row_labels = []

        lmaxw = 0
        for i in range(num_rows + 1):
            layout = self.create_pango_layout("%d" % (start_val + (i * self.linescale)))
            layout.set_font_description(pango.FontDescription("%s %dpx" % (self.font, labelhpix)))
            row_labels.append(layout)
            fw, fh = layout.get_pixel_size()
            lmaxw = max(lmaxw, fw)

        # Fill in the width
        graphx = lmaxw + 3
        graphw = w - graphx - 2

        cr.save()
        cr.set_line_width(1.5)
        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(graphx, graphy, graphw, graphh)
        cr.fill()
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(graphx, graphy, graphw, graphh)
        cr.stroke()
        cr.restore()

        for i in range(len(row_labels)):
            cr.save()

            fontw, fonth = row_labels[i].get_pixel_size()

            yline = (graphh + graphy) - ((i) * rowpix) + 0.5

            cr.move_to(1, yline - (fonth / 2))
            cr.update_layout(row_labels[i])
            cr.show_layout(row_labels[i])

            cr.set_line_width(1)
            cr.set_source_rgb(0, 0, 0)
            cr.move_to(graphx - 2, yline)
            cr.line_to(graphx, yline)
            cr.stroke()
    
            cr.move_to(graphx, yline)
            cr.line_to(graphx + graphw, yline)
            cr.stroke()

            cr.restore()

        # Do an inefficient multi-draw line because we don't complete it back to 0
        cr.save()
        cr.set_line_width(0.5)
        cr.set_source_rgb(self.linecolor[0], self.linecolor[1], self.linecolor[2])
        for i in range(len(self.samples) - 1):
            if self.samples[i] == None or self.samples[i+1] == None:
                continue

            px1 = (graphw / float(self.maxsamples)) * i
            px2 = (graphw / float(self.maxsamples)) * (i + 1)

            py1 = graphh * (float(abs(self.samples[i]) + start_val) / float(abs(last_val) + start_val))
            py2 = graphh * (float(abs(self.samples[i+1]) + start_val) / float(abs(last_val) + start_val))

            cr.move_to(graphx + px1, (graphy + graphh) - py1)
            cr.line_to(graphx + px2, (graphy + graphh) - py2)
            cr.stroke()

        cr.restore()

    def do_expose_event(self, event):
        self.chain(event)
        try:
            cr = self.window.cairo_create()
        except AttributeError:
            return self._expose_gdk(event)
        return self._expose_cairo(event, cr)

