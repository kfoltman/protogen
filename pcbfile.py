import Image

def kcquote(s):
    return '"%s"' % s

def mil2mm(mil):
    return 0.0254 * mil

class Rect:
    def __init__(self, sx, sy, ex, ey):
        self.sx = sx
        self.sy = sy
        self.ex = ex
        self.ey = ey
    def __str__(self):
        return "(%f,%f)-(%f,%f)" % (self.sx, self.sy, self.ex, self.ey)
    def offset(self, x, y):
        return Rect(self.sx + x, self.sy + y, self.ex + x, self.ey + y)
    def union(self, r2):
        return Rect(min(self.sx, r2.sx), min(self.sy, r2.sy), max(self.ex, r2.ex), max(self.ey, r2.ey))
    def intersect(self, r2):
        # Fully to the right or below
        if self.sx > r2.ex or self.sy > r2.ey:
            return None
        # Fully to the left or above
        if self.ex < r2.sx or self.ey < r2.sy:
            return None
        return Rect(max(self.sx, r2.sx), max(self.sy, r2.sy), min(self.ex, r2.ex), min(self.ey, r2.ey))

class PCBPadClass:
    def __init__(self, shape, sizex, sizey, drill, padtype, boundmargin = 0.254, boundx = 0, boundy = 0, drilly = None):
        self.shape = shape
        self.sizex = sizex
        self.sizey = sizey
        if drilly is not None:
            self.drillx = drill
            self.drilly = drilly
        else:
            self.drillx = drill
            self.drilly = drill
        self.padtype = padtype
        self.boundmargin = boundmargin
        self.boundx = boundx
        self.boundy = boundy
    def get_bounding_rect(self, x, y):
        hsx = max(self.sizex, self.drillx, self.boundx) / 2 + self.boundmargin
        hsy = max(self.sizey, self.drilly, self.boundy) / 2 + self.boundmargin
        return Rect(x - hsx, y - hsy, x + hsx, y + hsy)
    def get_pad_layers(self, layer):
        if self.padtype != "smd":
            return "*.Cu *.Mask " + layer.replace(".Cu", ".SilkS")
        else:
            return layer + " " + layer.replace(".Cu", ".Mask") + " " + layer.replace(".Cu", ".SilkS")

class StdTHTPad(PCBPadClass):
    def __init__(self, shape = "oval", sizex = 1.4, sizey = 2.0, drill = 0.9, boundmargin = 0.254, boundx = 0, boundy = 0, drilly = None, padtype = "thru_hole"):
        PCBPadClass.__init__(self, shape = shape, sizex = sizex, sizey = sizey, drill = drill, padtype = padtype, boundmargin = boundmargin, boundx = boundx, boundy = boundy, drilly = drilly)
        
StdTHTPad.oval = StdTHTPad("oval")
StdTHTPad.rect = StdTHTPad("rect")
StdTHTPad.oval90 = StdTHTPad("oval", sizex = 2.0, sizey = 1.4)
StdTHTPad.rect90 = StdTHTPad("rect", sizex = 2.0, sizey = 1.4)

class StdSMDPad(PCBPadClass):
    def __init__(self, sizex, sizey, boundmargin = 0.254, boundx = 0, boundy = 0, padtype = "smd", shape = "rect"):
        PCBPadClass.__init__(self, shape = shape, sizex = sizex, sizey = sizey, drill = 0, padtype = padtype, boundmargin = boundmargin, boundx = boundx, boundy = boundy)
        
StdSMDPad.SOIC_430 = StdSMDPad(0.55, 0.95)


class MountingHolePad(StdTHTPad):
    def __init__(self, diameter):
        StdTHTPad.__init__(self, "oval", diameter, diameter, diameter, padtype = "thru_hole")

class PCBPad:
    def __init__(self, index, padclass, x, y, netname, layer, angle = 0):
        self.index = index
        self.padclass = padclass
        self.layers = padclass.get_pad_layers(layer)
        self.x = x
        self.y = y
        self.netname = netname
        self.angle = angle
    def generate(self, netlist):
        return """    (pad "%s" %s %s (at %s %s %s) (size %0.4f %0.4f) (drill oval %0.3f %0.3f)
      (layers %s)
      (net %d %s)
    )
""" % (self.index, self.padclass.padtype, self.padclass.shape, self.x, self.y, self.angle, self.padclass.sizex, self.padclass.sizey, self.padclass.drillx, self.padclass.drilly, self.layers, netlist.get_net_id(self.netname), kcquote(self.netname))
    def get_bounding_rect(self):
        return self.padclass.get_bounding_rect(self.x, self.y)

class PCBModule:
    def __init__(self, name, layer, x, y, description = "", tags = ""):
        self.name = name
        self.description = description
        self.tags = tags
        self.layer = layer
        self.x = x
        self.y = y
        self.pads = []
        self.items = []
        
    def append(self, item):
        self.items.append(item)
    def append_all(self, items):
        self.items += items

    def create_pads(self, pad_grid, netfunc = None, tracks_layer = None, widthfunc = None):
        padid = 1
        ngroups = pad_grid.get_num_groups()
        maxitems = max([pad_grid.get_num_items(g) for g in xrange(ngroups)])
        last_in_row = [None] * maxitems
        tracks = []
        for g in xrange(ngroups):
            last_in_col = None
            for i in xrange(pad_grid.get_num_items(g)):
                res = pad_grid.get_pad_location_and_type(g, i)
                if res is not None:
                    x, y, angle, padclass = res
                    net = ''
                    if netfunc is not None:
                        net = netfunc(g, i)
                    if net is not None:
                        self.pads.append(PCBPad(padid, padclass, x, y, net, self.layer, angle = angle))
                        padid += 1
                        if tracks_layer is not None and last_in_col is not None and last_in_col[0] == net:
                            tracks.append(TraceSegment(x + self.x, last_in_col[1] + self.y, x + self.x, y + self.y, net, widthfunc(net), tracks_layer))
                        last_in_col = (net, y)
                        
                        if tracks_layer is not None and last_in_row[i] is not None and last_in_row[i][0] == net:
                            tracks.append(TraceSegment(last_in_row[i][1] + self.x, y + self.y, x + self.x, y + self.y, net, widthfunc(net), tracks_layer))
                        last_in_row[i] = (net, x)
        return tracks

    def get_exclusions(self):
        return [p.get_bounding_rect().offset(self.x, self.y) for p in self.pads]

    def get_bounding_rect(self):
        bb = None
        for p in self.pads:
            br = p.get_bounding_rect().offset(self.x, self.y)
            if bb is None:
                bb = br
            else:
                bb = bb.union(br)
        print bb
        return bb

    def generate(self, netlist):
        return """
  (module %s (layer %s)
    (at %0.2f %0.2f)
    (descr %s)
    (tags %s)
%s
  )
""" % (self.name, self.layer, self.x, self.y, kcquote(self.description), kcquote(self.tags), "".join([pad.generate(netlist) for pad in self.pads] + [item.generate(netlist) for item in self.items]))
        
class MountingHoleModule(PCBModule):
    def __init__(self, x, y, diameter, layer = "F.Cu", crosshair = False):
        PCBModule.__init__(self, "hole", layer, x, y)
        self.pads.append(PCBPad(1, MountingHolePad(diameter), 0, 0, '', layer))

class FootprintGenerator:
    def create(self, layer, x, y, netfunc = None):
        m = PCBModule(self.name, layer, x, y)
        m.create_pads(self.get_pad_grid(), netfunc)
        self.create_silk(m)
        return m
    def get_pad_grid(self):
        return self.grid
    def create_silk(self, m):
        pass

class PCBNetlist:
    def __init__(self):
        self.nets = ['']
    def get_net_id(self, name):
        return self.nets.index(name)
    def generate(self):
        return "".join(["  (net %d %s)\n" % (i, kcquote(self.nets[i])) for i in xrange(len(self.nets))])

class GraphicObject:
    def __init__(self, layer, width, angle = None, is_footprint = False):
        self.layer = layer or ("F.SilkS" if is_footprint else "Edge.Cuts")
        self.width = width
        self.angle = angle
        self.angle_text = "(angle %d)" % angle if angle is not None else ""
        self.is_footprint = is_footprint

class GraphicText(GraphicObject):
    def __init__(self, text, x, y, layer, angle = 0, width = 0.3, sizex = 1.5, sizey = 1.5, reversed = None, is_footprint = False, footprint_text_type = None):
        self.text = text
        self.x = x
        self.y = y
        GraphicObject.__init__(self, layer, width, angle, is_footprint)
        self.sizex = sizex
        self.sizey = sizey
        self.footprint_text_type = footprint_text_type
        if reversed is None:
            self.reversed = layer.startswith("B.")
        else:
            self.reversed = reversed
    def generate(self, netlist):
        if self.is_footprint:
            return '  (fp_text %s %s (at %0.3f %0.3f %0.1f) (layer %s) (effects (font (size %f %f) (thickness %f))%s))\n' % (self.footprint_text_type, kcquote(self.text), self.x, self.y, self.angle, self.layer, self.sizex, self.sizey, self.width, " (justify mirror)" if self.reversed else "")
        else:
            return '  (gr_text %s (at %0.3f %0.3f %0.1f) (layer %s) (effects (font (size %f %f) (thickness %f))%s))\n' % (kcquote(self.text), self.x, self.y, self.angle, self.layer, self.sizex, self.sizey, self.width, " (justify mirror)" if self.reversed else "")

class GraphicLine(GraphicObject):
    def __init__(self, startx, starty, endx, endy, layer = None, width = 0.1, is_footprint = False):
        self.startx = startx
        self.starty = starty
        self.endx = endx
        self.endy = endy
        GraphicObject.__init__(self, layer, width, None, is_footprint)
    def generate(self, netlist):
        return '  (%s_line (start %0.3f %0.3f) (end %0.3f %0.3f) (layer %s) (width %f))\n' % ("fp" if self.is_footprint else "gr", self.startx, self.starty, self.endx, self.endy, self.layer, self.width)

class GraphicArc(GraphicObject):
    def __init__(self, startx, starty, endx, endy, angle = 90, layer = None, width = 0.1, is_footprint = False):
        self.startx = startx
        self.starty = starty
        self.endx = endx
        self.endy = endy
        self.angle = angle
        GraphicObject.__init__(self, layer, width, angle, is_footprint)
    def generate(self, netlist):
        return '  (%s_arc (start %0.3f %0.3f) (end %0.3f %0.3f) %s (layer %s) (width %f))\n' % ("fp" if self.is_footprint else "gr", self.startx, self.starty, self.endx, self.endy, self.angle_text, self.layer, self.width)

class GraphicCircle(GraphicObject):
    def __init__(self, centerx, centery, radius, angle = 90, layer = None, width = 0.1, is_footprint = False):
        self.centerx = centerx
        self.centery = centery
        self.endx = centerx + radius
        self.endy = centery
        self.angle = angle
        GraphicObject.__init__(self, layer, width, angle, is_footprint)
    def generate(self, netlist):
        return '  (%s_circle (center %0.3f %0.3f) (end %0.3f %0.3f) (layer %s) (width %f))\n' % ("fp" if self.is_footprint else "gr", self.centerx, self.centery, self.endx, self.endy, self.layer, self.width)

class GraphicRect(GraphicObject):
    def __init__(self, startx, starty, endx, endy, roundness = 0, layer = None, width = 0.1, is_footprint = False):
        self.startx = startx
        self.starty = starty
        self.endx = endx
        self.endy = endy
        self.roundness = roundness
        GraphicObject.__init__(self, layer, width, None, is_footprint)
    def generate(self, netlist):
        startx, starty, endx, endy = self.startx, self.starty, self.endx, self.endy
        layer, width = self.layer, self.width
        arcs = ''
        r = self.roundness
        if self.roundness > 0:
            arcs = GraphicArc(startx + r, starty + r, startx, starty + r, 90, layer, width, is_footprint = self.is_footprint).generate(netlist) + \
                GraphicArc(endx - r, starty + r, endx, starty + r, -90, layer, width, is_footprint = self.is_footprint).generate(netlist) + \
                GraphicArc(startx + r, endy - r, startx, endy - r, -90, layer, width, is_footprint = self.is_footprint).generate(netlist) + \
                GraphicArc(endx - r, endy - r, endx, endy - r, 90, layer, width, is_footprint = self.is_footprint).generate(netlist)
        return arcs + GraphicLine(startx + r, starty, endx - r, starty, layer, width, is_footprint = self.is_footprint).generate(netlist) + \
            GraphicLine(endx, starty + r, endx, endy - r, layer, width, is_footprint = self.is_footprint).generate(netlist) + \
            GraphicLine(endx - r, endy, startx + r, endy, layer, width, is_footprint = self.is_footprint).generate(netlist) + \
            GraphicLine(startx, endy - r, startx, starty + r, layer, width, is_footprint = self.is_footprint).generate(netlist)

class TraceSegment:
    def __init__(self, sx, sy, ex, ey, net, width = 0.254, layer = 'B.Cu'):
        self.sx = sx
        self.sy = sy
        self.ex = ex
        self.ey = ey
        self.net = net
        self.width = width
        self.layer = layer
    def generate(self, netlist):
        return '(segment (start %0.3f %0.3f) (end %0.3f %0.3f) (width %f) (layer %s) (net %d))' % (self.sx, self.sy, self.ex, self.ey, self.width, self.layer, netlist.get_net_id(self.net))
    
def bmp_to_silk(sx, sy, name, is_lit, scale, layer = "F.SilkS", center = False):
    im = Image.open(name)
    cx, cy = im.size
    if center:
        sx -= cx * scale / 2
        sy -= cy * scale / 2
    segments = []
    for y in range(cy):
        last_pixel = None
        for x in range(cx):
            if is_lit(*im.getpixel((x, y))):
                if last_pixel is None:
                    last_pixel = x
            else:
                if last_pixel is not None:
                    segments.append(GraphicLine(sx + last_pixel * scale, sy + y * scale, sx + (x - 1) * scale, sy + y * scale, layer = layer, width = scale))
                    last_pixel = None
        if last_pixel is not None:
            segments.append(GraphicLine(sx + last_pixel * scale, sy + y * scale, sx + (cx - 1) * scale, sy + y * scale, layer = layer, width = scale))
    return segments

def bmp_to_silk2(sx, sy, name, is_lit, scale, layer = "F.SilkS", center = False):
    im = Image.open(name)
    cx, cy = im.size
    if center:
        sx -= cx * scale / 2
        sy -= cy * scale / 2
    segments = []
    for x in range(cx):
        last_pixel = None
        for y in range(cy):
            if is_lit(*im.getpixel((x, y))):
                if last_pixel is None:
                    last_pixel = y
            else:
                if last_pixel is not None:
                    segments.append(GraphicLine(sx + x * scale, sy + last_pixel * scale, sx + x * scale, sy + (y - 1) * scale, layer = layer, width = scale))
                    last_pixel = None
        if last_pixel is not None:
            segments.append(GraphicLine(sx + x * scale, sy + last_pixel * scale, sx + x * scale, sy + (cy - 1) * scale, layer = layer, width = scale))
    return segments

class PCBFile:
    def __init__(self, thickness = 1.6, tracewidth = 6, clearance = 6, gerberdir = "gerbers"):
        self.pagetype = "A4"
        self.thickness = thickness
        self.tracewidth = tracewidth
        self.clearance = clearance
        self.gerberdir = gerberdir
        self.layers = [
            (15, "F.Cu", "signal"),
            (0 , "B.Cu", "signal"),
            (16, "B.Adhes", "user"),
            (17, "F.Adhes", "user"),
            (18, "B.Paste", "user"),
            (19, "F.Paste", "user"),
            (20, "B.SilkS", "user"),
            (21, "F.SilkS", "user"),
            (22, "B.Mask", "user"),
            (23, "F.Mask", "user"),
            (24, "Dwgs.User", "user"),
            (25, "Cmts.User", "user"),
            (26, "Eco1.User", "user"),
            (27, "Eco2.User", "user"),
            (28, "Edge.Cuts", "user")
        ]
        self.netlist = PCBNetlist()
        self.items = []
    def append(self, item):
        self.items.append(item)
    def append_all(self, items):
        self.items += items
    def get_layerstr(self):
        return "".join(["    (%s %s %s)\n" % (l[0], l[1], l[2]) for l in self.layers])
    def generate(self):
        skeleton = """(kicad_pcb (version 3) (host pcbnew "(2013-mar-13)-testing")

  (general
    (thickness {thickness})
    (nets {nets})
  )

  (page {pagetype})
  (layers
{layers}
  )

  (setup
    (last_trace_width 0.254)
    (trace_clearance {clearance})
    (zone_clearance 0.508)
    (zone_45_only no)
    (trace_min {tracewidth})
    (segment_width 0.2)
    (edge_width 0.1)
    (via_size 0.889)
    (via_drill 0.635)
    (via_min_size 0.889)
    (via_min_drill 0.508)
    (uvia_size 0.508)
    (uvia_drill 0.127)
    (uvias_allowed no)
    (uvia_min_size 0.508)
    (uvia_min_drill 0.127)
    (pcb_text_width 0.3)
    (pcb_text_size 1.5 1.5)
    (mod_edge_width 0.15)
    (mod_text_size 1 1)
    (mod_text_width 0.15)
    (pad_size 1.524 2.19964)
    (pad_drill 1.00076)
    (pad_to_mask_clearance 0)
    (aux_axis_origin 50 50)
    (grid_origin 50 50)
    (visible_elements 7FFFFFFF)
    (pcbplotparams
      (layerselection 0x000f0_80000001)
      (usegerberextensions true)
      (excludeedgelayer true)
      (linewidth 0.150000)
      (plotframeref false)
      (viasonmask false)
      (mode 1)
      (useauxorigin false)
      (hpglpennumber 1)
      (hpglpenspeed 20)
      (hpglpendiameter 15)
      (hpglpenoverlay 2)
      (psnegative false)
      (psa4output false)
      (plotreference true)
      (plotvalue true)
      (plotothertext true)
      (plotinvisibletext false)
      (padsonsilk false)
      (subtractmaskfromsilk false)
      (outputformat 1)
      (mirror false)
      (drillshape 1)
      (scaleselection 1)
      (outputdirectory "{gerberdir}"))
  )

{netlist}
{items}
)
""".format(pagetype = self.pagetype, thickness = self.thickness, layers = self.get_layerstr(), netlist = self.netlist.generate(), items = "".join([item.generate(self.netlist) for item in self.items]),
        tracewidth = 0.0254 * self.tracewidth, clearance = 0.0254 * self.clearance, gerberdir = self.gerberdir, nets = len(self.netlist.nets))
        return skeleton
