from pcbfile import *
import re

class PadGrid:
    def get_pad_location_and_type(self, group, index):
        return None
    def get_num_groups(self):
        return 0
    def get_num_items(self, group):
        return 0
    def for_all(self, func):
        res = []
        for g in xrange(self.get_num_groups()):
            for i in xrange(self.get_num_items(g)):
                res.append(func(g, i))
        return res
    def get_all_pads(self):
        return filter(lambda x: x is not None, self.for_all(self.get_pad_location_and_type))
    def get_extremes(self):
        # doesn't include pad size, only centres
        allpads = self.get_all_pads()
        xs = min([x for x, y, padclass in allpads])
        ys = min([y for x, y, padclass in allpads])
        xe = max([x for x, y, padclass in allpads])
        ye = max([y for x, y, padclass in allpads])
        return Rect(xs, ys, xe, ye)

class SILGrid(PadGrid):
    def __init__(self, pins, pitch = 2.54, padclass = None):
        self.pitch = pitch
        self.pins = pins
        self.xoffset = -pins * pitch / 2
        self.padclass = padclass
    def get_num_groups(self):
        return 1
    def get_pad_location_and_type(self, group, index):
        padclass = self.padclass
        if self.padclass is None:
            padclass = StdTHTPad.oval if (group + index) > 0 else StdTHTPad.rect
        return (self.xoffset + self.pitch * index, self.ycoords[group], padclass)
    def get_num_items(self, group):
        return self.pins

class DILGrid(PadGrid):
    def __init__(self, pins, vspacing, pitch = 2.54, cols = 2, padclass = None):
        self.pitch = pitch
        self.pins = pins
        self.cols = cols
        self.ycoords = [vspacing * pitch / 2, -vspacing * pitch / 2]
        self.xoffset = (-pins // cols + 1) * pitch / 2
        self.padclass = padclass
    def get_num_groups(self):
        return 2
    def get_pad_location_and_type(self, group, index):
        padclass = self.padclass
        if padclass is None:
            padclass = StdTHTPad.oval if (group + index) > 0 else StdTHTPad.rect
        if group == 0:
            return (self.xoffset + self.pitch * index, self.ycoords[group], padclass)
        else:
            return (self.xoffset + self.pitch * (self.pins // 2 - 1 - index), self.ycoords[group], padclass)
    def get_num_items(self, group):
        return self.pins // 2
    @staticmethod
    def connector(pins):
        return DILGrid(pins, 1, 2.54)
    @staticmethod
    def small(pins):
        return DILGrid(pins, 3, 2.54)
    @staticmethod
    def large(pins):
        return DILGrid(pins, 5, 2.54)

class THTMatrixGrid(PadGrid):
    def __init__(self, rows, columns, hpitch = 2.54, vpitch = 2.54, padtype = StdTHTPad.oval, padfunc = None):
        self.hpitch = hpitch
        self.vpitch = vpitch
        self.rows = rows
        self.columns = columns
        self.padtype = padtype
        self.padfunc = padfunc
    def get_num_groups(self):
        return self.columns
    def get_pad_location_and_type(self, group, index):
        padtype = self.padtype
        if self.padfunc is not None:
            padtype = self.padfunc(group, index)
        if padtype is None:
            return None
        return (self.hpitch * (group - (self.columns - 1) / 2.0), self.vpitch * (index - (self.rows - 1) / 2.0), padtype)
    def get_num_items(self, group):
        return self.rows
    @staticmethod
    def dil_small(pins):
        return DILGrid(2.54, pins, 3)

class GridWithExclusions:
    def __init__(self, grid, exclusions, offset):
        self.grid = grid
        self.exclusions = exclusions
        self.offset = offset
    def get_num_groups(self):
        return self.grid.get_num_groups()
    def get_num_items(self, group):
        return self.grid.get_num_items(group)
    def get_pad_location_and_type(self, group, index):
        res = self.grid.get_pad_location_and_type(group, index)
        if res is None:
            return None
        x, y, padclass = res
        if self.is_excluded(padclass.get_bounding_rect(x, y)):
            return None
        return x, y, padclass
    def is_excluded(self, rect):
        rect = rect.offset(*self.offset)
        for r in self.exclusions:
            if r.intersect(rect) is not None:
                return True
        return False
class SILSMD(SMDGenerator):
    def __init__(self, name, padwidth, padheight, pitch, pins):
        self.name = name
        self.padclass = StdSMDPad(padwidth, padheight)
        self.grid = SILGrid(pins, pitch, padclass = self.padclass)

class DILSMD(SMDGenerator):
    def __init__(self, name, padwidth, padheight, pitch, midline, pins):
        self.name = name
        self.padclass = StdSMDPad(padwidth, padheight)
        # Note: DILGrid uses spacing in pitch units
        self.grid = DILGrid(pins, midline / pitch, pitch, padclass = self.padclass)

class VishaySMD(SILSMD):
    def __init__(self, name, G, Y, X, Z):
        SILSMD.__init__(self, name, padwidth = Y, padheight = X, pitch = (Z + G) / 2.0, pins = 2)

class SMDFootprintGenerators:
    # http://www.skyworksinc.com/uploads/documents/200123k.pdf
    # page 4
    MSOP_8 = DILSMD("MSOP_8", padwidth = 0.40, padheight = 1.70, pitch = 0.65, midline = 4.1, pins = 8)
    MSOP_10 = DILSMD("MSOP_10", padwidth = 0.25, padheight = 1.80, pitch = 0.5, midline = 4.4, pins = 10)
    # page 6
    #SC70_3 = SMDTransistor(padwidth = 0.50, padheight = 1.40, pitch = 0.65, midline = 2.20)
    SC70_6 = DILSMD("SC70_6", padwidth = 0.40, padheight = 0.75, pitch = 0.65, midline = 1.65, pins = 6)
    SC79_2 = SILSMD("SC79_2", padwidth = 0.35, padheight = 0.35, pitch = 1.35, pins = 2)
    # page 7
    SOD323_2 = SILSMD("SOD232_2", padwidth = 0.90, padheight = 0.80, pitch = 2.40, pins = 2)
    SOIC_N = {}
    for pins in range(6, 21, 2):
        SOIC_N[pins] = DILSMD("SOIC_N%d" % pins, padwidth = 0.6, padheight = 2.2, pitch = 1.27, midline = 5.2, pins = pins)
    SOIC_W = {}
    for pins in range(14, 41, 2):
        SOIC_W[pins] = DILSMD("SOIC_W%d" % pins, padwidth = 0.6, padheight = 2.2, pitch = 1.27, midline = 9.2, pins = pins)
    SSOP_440 = {}
    SSOP_530 = {}
    for pins in range(6, 40, 2):
        SSOP_440[pins] = DILSMD('SSOP_440_%d' % pins, padwidth = 0.4, padheight = 2.2, pitch = 0.65, midline = 5.4, pins = pins)
        SSOP_530[pins] = DILSMD("SSOP_530_%d" % pins, padwidth = 0.4, padheight = 2.2, pitch = 0.65, midline = 7.2, pins = pins)
    # page 8
    #SOT23_3 = SMDTransistor(padwidth = 1.00, padheight = 1.40, pitch = 0.95, midline = 2.20)
    # http://www.vishay.com/docs/28745/soldpads.pdf
    Wave1206 = VishaySMD("wave1206", G = 1.5, Y = 1.6, X = 1.9, Z = 4.7)
    Wave0805 = VishaySMD("wave0805", G = 0.65, Y = 1.4, X = 1.5, Z = 3.45)
    Wave0603 = VishaySMD("wave0603", G = 0.5, Y = 1.2, X = 1.1, Z = 2.9)
    
    Reflow1206 = VishaySMD("reflow1206", G = 1.25, Y = 1.25, X = 1.75, Z = 4.0)
    Reflow0805 = VishaySMD("reflow0805", G = 0.65, Y = 1.1, X = 1.4, Z = 2.85)
    Reflow0603 = VishaySMD("reflow0603", G = 0.5, Y = 0.95, X = 0.95, Z = 2.4)
    Reflow0402 = VishaySMD("reflow0402", G = 0.25, Y = 0.6, X = 0.55, Z = 1.45)

def sgn(val):
    if val > 0:
        return 1
    if val < 0:
        return -1
    return 0

# Note: this is very limited
def smart_connect(dilmod, smallmod, i, pins, pitch, width = 0.254, smd = True):
    # pins per side
    pins_side = pins // 2
    mid_pin = (pins_side - 1) / 2
    traces = []
    if i < pins_side:
        ix = i
        tdir = 1
    else:
        ix = pins - 1 - i
        tdir = -1
    if ix <= mid_pin:
        ixsym = ix
    else:
        ixsym = pins_side - 1 - ix
    
    xfp, yfp = smallmod.x, smallmod.y
    xs, ys = smallmod.pads[i].x, smallmod.pads[i].y
    xe, ye = dilmod.pads[i].x, dilmod.pads[i].y
    # Vertical line from the pad
    if ixsym > 0:
        if smd:
            ys += tdir * smallmod.pads[i].padclass.sizey / 2
        space_per_trace = (abs(ye - ys) - dilmod.pads[i].padclass.sizey - width) / (mid_pin - 1)
        straightv = max(space_per_trace, 2 * width) * ixsym + 0.5 * width
        corner = ixsym * pitch / 2 + width
        if ixsym == mid_pin:
            corner = 0
        if corner > straightv:
            corner = straightv
        mind = min(abs(xe - xs), abs(ye - ys))
        if corner > mind / 2:
            corner = mind / 2
        
        ys2 = ys + tdir * (straightv - corner)
        xs3 = xs + corner * sgn(xe - xs)
        ys3 = ys + tdir * straightv
        traces.append(TraceSegment(xfp + xs, yfp + ys, xfp + xs, yfp + ys2, smallmod.pads[i].netname, width, smallmod.layer))
        if corner > 0:
            traces.append(TraceSegment(xfp + xs, yfp + ys2, xfp + xs3, yfp + ys3, smallmod.pads[i].netname, width, smallmod.layer))
        xs, ys = xs3, ys3
    
    if abs(xe - xs) > abs(ye - ys):
        xs2 = xs + sgn(xe - xs) * (abs(xe - xs) - abs(ye - ys))
        traces.append(TraceSegment(xfp + xs, yfp + ys, xfp + xs2, yfp + ys, smallmod.pads[i].netname, width, smallmod.layer))
        xs = xs2
    elif abs(xe - xs) < abs(ye - ys):
        ys2 = ys + sgn(ye - ys) * (abs(ye - ys) - abs(xe - xs))
        traces.append(TraceSegment(xfp + xs, yfp + ys, xfp + xs, yfp + ys2, smallmod.pads[i].netname, width, smallmod.layer))
        ys = ys2
    traces.append(TraceSegment(xfp + xs, yfp + ys, xfp + xe, yfp + ye, smallmod.pads[i].netname, width, smallmod.layer))
    return traces

def widthmetric(net1, net2):
    if re.sub("_.*", "", net1) == re.sub("_.*", "", net2):
        return 0.2
    return 0.3
        
def widthmetric2(net1, net2):
    if re.sub("_.*", "", net1) == re.sub("_.*", "", net2):
        return 0
    return 0.2
        
def make_silkscreen(cols, rows, exmatrix, pcbf, getnet, pitch, xmid, ymid):
    for x in xrange(0, cols):
        for y in xrange(0, rows):
            xyt = exmatrix.get_pad_location_and_type(x, y)
            if xyt is not None:
                net = getnet(x, y)
                if net is None:
                    continue
                leftbound = x == 0
                rightbound = x == cols - 1
                if x > 0:
                    netl = getnet(x - 1, y)
                    if netl is None:
                        leftbound = True
                    if net != netl and netl is not None:
                        left_xyt = exmatrix.get_pad_location_and_type(x - 1, y)
                        if left_xyt is not None:
                            xline = (xyt[0] + left_xyt[0]) / 2 + xmid
                            pcbf.append(GraphicLine(xline, xyt[1] - pitch / 2 + ymid, xline , xyt[1] + pitch / 2 + ymid, layer = "F.SilkS", width = widthmetric(net, netl)))
                            if widthmetric2(net, netl) > 0:
                                pcbf.append(GraphicLine(xline, xyt[1] - pitch / 2 + ymid, xline , xyt[1] + pitch / 2 + ymid, layer = "B.SilkS", width = widthmetric2(net, netl)))
                        else:
                            leftbound = True
                if x < cols - 1:
                    netr = getnet(x + 1, y)
                    if netr is None:
                        rightbound = True
                    right_xyt = exmatrix.get_pad_location_and_type(x + 1, y)
                    if right_xyt is None:
                        rightbound = True
                if leftbound:
                    xline = xyt[0] - pitch / 2 + xmid
                    pcbf.append(GraphicLine(xline, xyt[1] - pitch / 2 + ymid, xline , xyt[1] + pitch / 2 + ymid, layer = "F.SilkS", width = 0.3))
                    pcbf.append(GraphicLine(xline, xyt[1] - pitch / 2 + ymid, xline , xyt[1] + pitch / 2 + ymid, layer = "B.SilkS", width = 0.3))
                if rightbound:
                    xline = xyt[0] + pitch / 2 + xmid
                    pcbf.append(GraphicLine(xline, xyt[1] - pitch / 2 + ymid, xline , xyt[1] + pitch / 2 + ymid, layer = "F.SilkS", width = 0.3))
                    pcbf.append(GraphicLine(xline, xyt[1] - pitch / 2 + ymid, xline , xyt[1] + pitch / 2 + ymid, layer = "B.SilkS", width = 0.3))
                topbound = y == 0
                bottombound = y == rows - 1
                if y > 0:
                    netu = getnet(x, y - 1)
                    if netu is None:
                        topbound = True
                    else:
                        up_xyt = exmatrix.get_pad_location_and_type(x, y - 1)
                        if up_xyt is None:
                            topbound = True
                        elif net != netu:
                            yline = (xyt[1] + up_xyt[1]) / 2 + ymid
                            pcbf.append(GraphicLine(xyt[0] - pitch / 2 + xmid, yline, xyt[0] + pitch / 2 + xmid, yline, layer = "F.SilkS", width = widthmetric(net, netu)))
                            if widthmetric2(net, netu) > 0:
                                pcbf.append(GraphicLine(xyt[0] - pitch / 2 + xmid, yline, xyt[0] + pitch / 2 + xmid, yline, layer = "B.SilkS", width = widthmetric2(net, netu)))
                if y < rows - 1:
                    netr = getnet(x, y + 1)
                    if netr is None:
                        bottombound = True
                    bottom_xyt = exmatrix.get_pad_location_and_type(x, y + 1)
                    if bottom_xyt is None:
                        bottombound = True
                if topbound:
                    yline = xyt[1] - pitch / 2 + ymid
                    pcbf.append(GraphicLine(xyt[0] - pitch / 2 + xmid, yline, xyt[0] + pitch / 2 + xmid, yline, layer = "F.SilkS", width = 0.3))
                    pcbf.append(GraphicLine(xyt[0] - pitch / 2 + xmid, yline, xyt[0] + pitch / 2 + xmid, yline, layer = "B.SilkS", width = 0.3))
                if bottombound:
                    yline = xyt[1] + pitch / 2 + ymid
                    pcbf.append(GraphicLine(xyt[0] - pitch / 2 + xmid, yline, xyt[0] + pitch / 2 + xmid, yline, layer = "F.SilkS", width = 0.3))
                    pcbf.append(GraphicLine(xyt[0] - pitch / 2 + xmid, yline, xyt[0] + pitch / 2 + xmid, yline, layer = "B.SilkS", width = 0.3))
