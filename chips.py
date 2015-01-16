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
        xs = min([x for x, y, angle, padclass in allpads])
        ys = min([y for x, y, angle, padclass in allpads])
        xe = max([x for x, y, angle, padclass in allpads])
        ye = max([y for x, y, angle, padclass in allpads])
        return Rect(xs, ys, xe, ye)

class SILGrid(PadGrid):
    def __init__(self, pins, pitch = 2.54, padclass = None, invert = False):
        self.invert = invert
        self.pitch = pitch
        self.pins = pins
        self.xoffset = -(pins - 1) * pitch / 2
        self.ycoords = [0]
        self.padclass = padclass
    def get_num_groups(self):
        return 1
    def get_pad_location_and_type(self, group, index):
        padclass = self.padclass
        if self.padclass is None:
            padclass = StdTHTPad.oval if (group + index) > 0 else StdTHTPad.rect
        return (self.xoffset + self.pitch * (self.pins - index - 1 if self.invert else index), self.ycoords[group], 0, padclass)
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
            return (self.xoffset + self.pitch * index, self.ycoords[group], 0, padclass)
        else:
            return (self.xoffset + self.pitch * (self.pins // 2 - 1 - index), self.ycoords[group], 0, padclass)
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

class QFPGrid(PadGrid):
    def __init__(self, pins, boxIn, boxOut, pitch, pad_width):
        self.boxIn = boxIn
        self.boxOut = boxOut
        self.boxMidPos = (boxIn + boxOut) / 4.0
        self.pitch = pitch
        self.pins = pins
        self.padclass = StdSMDPad(pad_width, (boxOut - boxIn) / 2)
    def get_num_groups(self):
        return 4
    def get_pad_location_and_type(self, group, index):
        pitch = self.pitch
        if group == 0:
            return (pitch * (index - (self.pins / 4 - 1) / 2.0), self.boxMidPos, 0, self.padclass)
        if group == 1:
            return (self.boxMidPos, -pitch * (index - (self.pins / 4 - 1) / 2.0), 90, self.padclass)
        if group == 2:
            return (-pitch * (index - (self.pins / 4 - 1) / 2.0), -self.boxMidPos, 0, self.padclass)
        if group == 3:
            return (-self.boxMidPos, pitch * (index - (self.pins / 4 - 1) / 2.0), 90, self.padclass)
    def get_num_items(self, group):
        return self.pins // 4

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
        return (self.hpitch * (group - (self.columns - 1) / 2.0), self.vpitch * (index - (self.rows - 1) / 2.0), 0, padtype)
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
        x, y, angle, padclass = res
        if self.is_excluded(padclass.get_bounding_rect(x, y)):
            return None
        return x, y, angle, padclass
    def is_excluded(self, rect):
        rect = rect.offset(*self.offset)
        for r in self.exclusions:
            if r.intersect(rect) is not None:
                return True
        return False

class SILTHT(FootprintGenerator):
    def __init__(self, prefix, name, padclass, pitch, pins, invert = False, use_distance_for_name = False):
        self.prefix = prefix
        self.name = name
        self.padclass = padclass
        self.pins = pins
        self.pitch = pitch
        self.use_distance_for_name = use_distance_for_name
        self.grid = SILGrid(pins, pitch, padclass = self.padclass, invert = invert)
    def get_size_name(self):
        if self.use_distance_for_name:
            return "%s%g" % (self.prefix, self.pitch / 2.54)
        else:
            return "%s%s" % (self.prefix, self.pins)
    def create_silk(self, m):
        whalf = self.grid.xoffset - self.padclass.sizex
        E = self.padclass.sizey
        m.items.append(GraphicRect(-whalf, -E / 2, whalf, E / 2, is_footprint = True))
        #m.items.append(GraphicArc(whalf, 0, whalf, -1, angle = 180, is_footprint = True))

class DILTHT(FootprintGenerator):
    def __init__(self, prefix, name, padclass, pitch, distance, pins):
        self.prefix = prefix
        self.name = name
        self.padclass = padclass
        self.pins = pins
        self.pitch = pitch
        self.distance = distance
        self.grid = DILGrid(pins, distance, pitch, padclass = self.padclass)
    def get_size_name(self):
        return "%s-%s" % (self.prefix, self.pins)
    def create_silk(self, m):
        whalf = self.grid.xoffset - self.padclass.sizex
        E = self.distance * self.pitch - self.padclass.drilly
        m.items.append(GraphicRect(-whalf, -E / 2, whalf, E / 2, is_footprint = True))
        m.items.append(GraphicArc(whalf, 0, whalf, -1, angle = 180, is_footprint = True))

class SILSMD(FootprintGenerator):
    def __init__(self, name, padwidth, padheight, pitch, pins, invert):
        self.name = name
        self.pitch = pitch
        self.padclass = StdSMDPad(padwidth, padheight)
        self.padwidth = padwidth
        self.padheight = padheight
        self.grid = SILGrid(pins, pitch, padclass = self.padclass, invert = invert)
    def create_silk(self, m):
        m.items.append(GraphicText("C****", 0, -self.padheight * 0.5 - 0.3, "F.SilkS", is_footprint = True, sizex = 0.7, sizey = 0.6, width = 0.15, footprint_text_type = "reference"))
        m.items.append(GraphicText(self.name, 0, self.padheight * 0.5 + 0.3, "F.SilkS", is_footprint = True, sizex = 0.7, sizey = 0.6, width = 0.15, footprint_text_type = "value"))
        m.items.append(GraphicRect(self.grid.xoffset - self.padwidth / 2, -self.padheight / 2, -self.grid.xoffset + self.padwidth / 2, self.padheight / 2, is_footprint = True))
    def get_size_name(self):
        return self.name

class DILSMD(FootprintGenerator):
    def __init__(self, name, padwidth, padheight, pitch, midline, pins):
        self.name = name
        self.padclass = StdSMDPad(padwidth, padheight)
        # Note: DILGrid uses spacing in pitch units
        self.grid = DILGrid(pins, midline / pitch, pitch, padclass = self.padclass)

class DILSMD2(FootprintGenerator):
    def __init__(self, prefix, name, padwidth, padheight, pitch, E, H, pins):
        self.prefix = prefix
        self.name = name
        self.padclass = StdSMDPad(padwidth, padheight)
        # Note: DILGrid uses spacing in pitch units
        self.padwidth = padwidth
        self.padheight = padheight
        self.pitch = pitch
        self.pins = pins
        self.grid = DILGrid(pins, (E + H) / (2 * pitch), pitch, padclass = self.padclass)
        self.E = E
        self.H = H
    def get_size_name(self):
        return "%s-%d-%0.2f-%0.2f" % (self.prefix, self.pins, self.pitch, self.E)
    def create_silk(self, m):
        whalf = self.grid.xoffset - self.padwidth
        m.items.append(GraphicRect(-whalf, -self.E / 2, whalf, self.E / 2, is_footprint = True))
        m.items.append(GraphicCircle(whalf + self.pitch, self.E / 2 - self.pitch, self.pitch / 4.0, is_footprint = True))

class QFPSMD(FootprintGenerator):
    def __init__(self, prefix, pins, boxIn, boxOut, pitch, pad_width):
        self.prefix = prefix
        self.pitch = pitch
        self.name = 'QFP-%d-%0.2f' % (pins, pitch)
        self.grid = QFPGrid(pins, boxIn, boxOut, pitch, pad_width)
    def get_size_name(self):
        return self.name
    def create_silk(self, m):
        m.items.append(GraphicRect(-self.grid.boxIn / 2, -self.grid.boxIn / 2, self.grid.boxIn / 2, self.grid.boxIn / 2, is_footprint = True))
        m.items.append(GraphicCircle(-self.grid.boxIn / 2 + 2, self.grid.boxIn / 2 - 2, self.pitch, is_footprint = True))

class VishaySMD(SILSMD):
    def __init__(self, name, G, Y, X, Z):
        SILSMD.__init__(self, name, padwidth = Y, padheight = X, pitch = (Z + G) / 2.0, pins = 2, invert = False)

class VishaySMD2(SILSMD):
    def __init__(self, name, a, b, l, invert = False, expand_pad = False): # pad width, pad height, pad distance
        if expand_pad:
            a *= expand_pad
        SILSMD.__init__(self, name, padwidth = a, padheight = b, pitch = l + a, pins = 2, invert = invert)

class KemetCapSMD(SILSMD):
    def __init__(self, name, S, E, A, invert = True): # pad width, pad height, pad distance
        # extra space for hand soldering
        SILSMD.__init__(self, name, padwidth = 2 * S, padheight = E, pitch = 2 * S + A, pins = 2, invert = invert)

class XBJoystick:
    name = "XBJOYSTICK"
    def create(self, layer, x, y, netfunc = None):
        m = PCBModule(self.name, layer, x, y)
        # distance between mounting holes 
        W = 13.35
        H = 16
        # XXXKF look up the NPTH type
        mount_pin = StdTHTPad("rect", sizex = 1.4, sizey = 0.5, drill = 1.4, drilly = 0.5, padtype = "thru_hole")
        m.pads.append(PCBPad("", mount_pin, -W / 2, -H / 2, None, "F.Cu"))
        m.pads.append(PCBPad("", mount_pin, W / 2, -H / 2, None, "F.Cu"))
        m.pads.append(PCBPad("", mount_pin, -W / 2, H / 2, None, "F.Cu"))
        m.pads.append(PCBPad("", mount_pin, W / 2, H / 2, None, "F.Cu"))
        for xmil, ymil, num, angle in [
            (4, -1, 4, 90), (4, 0, 5, 90), (4, 1, 6, 90),
            (-1, 4, 1, 0), (0, 4, 2, 0), (1, 4, 3, 0)]:
                m.pads.append(PCBPad(num, StdTHTPad.oval, mil2mm(100 * xmil), mil2mm(100 * ymil), None, "F.Cu", angle))
        for xmm, ymm, num in [(-8, -3.5, 7), (-8, 3.5, 8), (-12, -3.5, 9), (-12, 3.5, 10)]:
                m.pads.append(PCBPad(num, StdTHTPad(sizex = 1.5, sizey = 2.0, drill = 1.1), xmm, ymm, None, "F.Cu", 0))
        return m
    def get_size_name(self):
        return self.name
    def create_silk(self, m):
        pass

class THTFootprintGenerators:
    DIL = {}
    DILW = {}
    R = {}
    C = {}
    for pins in range(6, 29, 2):
        DIL[pins] = DILTHT("DIL", "DIL_%d" % pins, StdTHTPad(), pitch = 2.54, distance = 3, pins = pins)
    for pins in range(24, 41, 2):
        DILW[pins] = DILTHT("DILW", "DILW_%d" % pins, StdTHTPad(), pitch = 2.54, distance = 5, pins = pins)
    C[1] = SILTHT("THT-C", "C1", pitch = 2.54 * 1, pins = 2, padclass = StdTHTPad.oval, invert = False, use_distance_for_name = True)
    C[2] = SILTHT("THT-C", "C2", pitch = 2.54 * 2, pins = 2, padclass = StdTHTPad.oval, invert = False, use_distance_for_name = True)
    R[3] = SILTHT("THT-R", "R3", pitch = 2.54 * 3, pins = 2, padclass = StdTHTPad.oval, invert = False, use_distance_for_name = True)
    R[4] = SILTHT("THT-R", "R4", pitch = 2.54 * 4, pins = 2, padclass = StdTHTPad.oval, invert = False, use_distance_for_name = True)
    XBJOYSTICK = XBJoystick()
    
class SMDFootprintGenerators:
    # http://www.skyworksinc.com/uploads/documents/200123k.pdf
    # page 4
    MSOP_8 = DILSMD("MSOP_8", padwidth = 0.40, padheight = 1.70, pitch = 0.65, midline = 4.1, pins = 8)
    MSOP_10 = DILSMD("MSOP_10", padwidth = 0.25, padheight = 1.80, pitch = 0.5, midline = 4.4, pins = 10)
    # page 6
    #SC70_3 = SMDTransistor(padwidth = 0.50, padheight = 1.40, pitch = 0.65, midline = 2.20)
    SC70_6 = DILSMD("SC70_6", padwidth = 0.40, padheight = 0.75, pitch = 0.65, midline = 1.65, pins = 6)
    SC79_2 = SILSMD("SC79_2", padwidth = 0.35, padheight = 0.35, pitch = 1.35, pins = 2, invert = False)
    # page 7
    SOD323_2 = SILSMD("SOD232_2", padwidth = 0.90, padheight = 0.80, pitch = 2.40, pins = 2, invert = False)
    SOIC_N = {}
    for pins in range(6, 21, 2):
        SOIC_N[pins] = DILSMD2("SOIC", "SOIC_N%d" % pins, padwidth = 0.6, padheight = 2.2, pitch = 1.27, E = 3.90, H = 6.00, pins = pins)
    SOIC_M = {}
    for pins in range(6, 17, 2):
        SOIC_M[pins] = DILSMD2("SOIC", "SOIC_M%d" % pins, padwidth = 0.6, padheight = 2.2, pitch = 1.27, E = 5.30, H = 8.00, pins = pins)
    SOIC_W = {}
    for pins in range(14, 41, 2):
        SOIC_W[pins] = DILSMD2("SOIC", "SOIC_W%d" % pins, padwidth = 0.6, padheight = 2.2, pitch = 1.27, E = 7.50, H = 10.30, pins = pins)
    SSOP_300 = {}
    SSOP_440 = {}
    SSOP_530 = {}
    for pins in range(6, 17, 2):
        SSOP_300[pins] = DILSMD2("SSOP", 'SSOP_300_%d' % pins, padwidth = 0.25, padheight = 1.6, pitch = 0.5, E = 3.00, H = 4.90, pins = pins)
    for pins in range(6, 40, 2):
        SSOP_440[pins] = DILSMD2("SSOP", 'SSOP_440_%d' % pins, padwidth = 0.4, padheight = 2.2, pitch = 0.65, E = 4.40, H = 6.40, pins = pins)
        SSOP_530[pins] = DILSMD2("SSOP", "SSOP_530_%d" % pins, padwidth = 0.4, padheight = 2.2, pitch = 0.65, E = 5.30, H = 8.00, pins = pins)
        
    QFP_050 = {}
    QFP_080 = {}
    # pins, boxIn, boxOut, pitch, pad_width
    QFP_080[32] = QFPSMD('QFP', 32, 7.7, 9.4, 0.8, 0.54)
    
    QFP_050[48] = QFPSMD('QFP', 48, 7.3, 9.7, 0.5, 0.32)
    QFP_050[64] = QFPSMD('QFP', 64, 10.3, 12.7, 0.5, 0.32)
    QFP_050[100] = QFPSMD('QFP', 100, 14.3, 16.7, 0.5, 0.32)
    QFP_050[144] = QFPSMD('QFP', 144, 19.9, 22.6, 0.5, 0.32)
    QFP_050[176] = QFPSMD('QFP', 176, 26.7 - 2 * 1.2, 26.7, 0.5, 0.32)
    # page 8
    #SOT23_3 = SMDTransistor(padwidth = 1.00, padheight = 1.40, pitch = 0.95, midline = 2.20)
    # http://www.vishay.com/docs/28745/soldpads.pdf
    Wave1206 = VishaySMD("wave1206", G = 1.5, Y = 1.6, X = 1.9, Z = 4.7)
    Wave0805 = VishaySMD("wave0805", G = 0.65, Y = 1.4, X = 1.5, Z = 3.45)
    Wave0603 = VishaySMD("wave0603", G = 0.5, Y = 1.2, X = 1.1, Z = 2.9)
    #
    #Reflow1812 = VishaySMD2("reflow1210", G = 1.25, Y = 1.25, X = 1.75, Z = 4.0)
    #Reflow1206 = VishaySMD2("reflow1206", G = 1.25, Y = 1.25, X = 1.75, Z = 4.0)
    #Reflow0805 = VishaySMD2("reflow0805", G = 0.65, Y = 1.1, X = 1.4, Z = 2.85)
    #Reflow0603 = VishaySMD2("reflow0603", G = 0.5, Y = 0.95, X = 0.95, Z = 2.4)
    #Reflow0402 = VishaySMD2("reflow0402", G = 0.25, Y = 0.6, X = 0.55, Z = 1.45)

    # Vishay resistors
    # http://www.vishay.com/docs/20035/dcrcwe3.pdf
    # (note: 0201 footprint is from Yageo's datasheet, not Vishay's)
    r = {}
    r['0201'] = VishaySMD2("r_0201", 0.35, 0.4, 0.3)
    r['0402'] = VishaySMD2("r_0402", 0.4, 0.6, 0.5)
    r['0603'] = VishaySMD2("r_0603", 0.5, 0.9, 1.0)
    r['0805'] = VishaySMD2("r_0805", 0.7, 1.3, 1.2)
    r['1206'] = VishaySMD2("r_1206", 0.9, 1.7, 2.0)
    r['1210'] = VishaySMD2("r_1210", 0.9, 2.5, 2.0)
    r['1218'] = VishaySMD2("r_1218", 1.05, 4.9, 1.9)
    r['2010'] = VishaySMD2("r_2010", 1.0, 2.5, 3.9)
    r['2512'] = VishaySMD2("r_2512", 1.0, 3.2, 5.2)
    
    # http://www.yageo.com/exep/pages/download/literatures/UPY-C_GEN_15.pdf
    c = {}
    c['0201'] = VishaySMD2("c_0201", 0.28, 0.3, 0.25)
    c['0402'] = VishaySMD2("c_0402", 0.5, 0.5, 0.5)
    c['0603'] = VishaySMD2("c_0603", 0.8, 0.9, 0.7)
    c['0805'] = VishaySMD2("c_0805", 0.95, 1.4, 0.9)
    c['1206'] = VishaySMD2("c_1206", 1.0, 1.8, 2.0)
    c['1210'] = VishaySMD2("c_1210", 1.0, 2.7, 2.0)
    c['1808'] = VishaySMD2("c_1808", 1.05, 2.3, 3.3)
    c['1812'] = VishaySMD2("c_1812", 1.05, 3.5, 3.3)
    c['2220'] = VishaySMD2("c_2220", 1.05, 5.3, 4.5)
    
    c['xtal-5.0x3.2-2p'] = VishaySMD2("xtal-5.0x3.2-2p", 1.8, 3.2, 1.8)

    # cap-t495.pdf - S, E, A
    c['kemet_a'] = KemetCapSMD("c_kemet_a", 0.8, 1.3, 0.8)
    c['kemet_b'] = KemetCapSMD("c_kemet_b", 0.8, 2.2, 1.1)
    c['kemet_c'] = KemetCapSMD("c_kemet_c", 1.3, 2.4, 2.5)
    c['kemet_d'] = KemetCapSMD("c_kemet_d", 1.3, 3.5, 3.8)
    c['kemet_x'] = KemetCapSMD("c_kemet_x", 1.3, 3.5, 3.8) # same except for P
    c['kemet_e'] = KemetCapSMD("c_kemet_e", 1.3, 4.1, 3.8) # used F instead of E
    c['kemet_t'] = KemetCapSMD("c_kemet_t", 0.8, 2.2, 1.1) # same as B (low profile?)
    c['kemet_v'] = KemetCapSMD("c_kemet_v", 1.3, 3.5, 3.8) # same as D (low profile?)
    
    # http://www.avx.com/docs/Catalogs/techsum.pdf
    #  TAJ, TMJ, TPS, TPM, TRJ, TRM, THJ, TAW, TLJ, TCJ, TCM
    for avxtype, psl, pl, ps, pw, pww in [
        ('NPR',   2.70, 0.95, 0.80, 1.60, 0.80),
        ('AGKS',  4.00, 1.40, 1.20, 1.80, 0.90),
        ('BHLT',  4.00, 1.40, 1.20, 2.80, 1.60),
        ('CFW',   6.50, 2.00, 2.50, 2.80, 1.60),
        ('DEXY',  8.00, 2.00, 4.00, 3.00, 1.70),
        ('UVZ',   8.00, 2.00, 4.00, 3.70, 1.80)]:
        for letter in avxtype:
            c['c_avx_smdj_' + letter] = VishaySMD2('c_avx_smdj_' + letter, pl, pw, ps, invert = True, expand_pad = 1.5)
    
    for avxtype, psl, pl, ps, pw, pww in [
        ('ACSV',  4.40, 1.60, 1.20, 1.80, 0.90),
        ('BT',    4.70, 1.70, 1.30, 3.00, 1.50),
        ('HQRU',  3.20, 1.30, 0.60, 1.50, 0.075),
        ('JL',    2.80, 1.10, 0.60, 1.00, 0.50),
        ('K',     2.20, 0.90, 0.40, 0.70, 0.35),
        ('M',     3.20, 1.30, 0.60, 1.00, 0.50),
        ('Z',     2.80, 1.10, 0.60, 0.70, 0.35),
        ]:
        for letter in avxtype:
            c['c_avx_tacmicro_' + letter] = VishaySMD2('c_avx_tacmicro_' + letter, pl, pw, ps, invert = True, expand_pad = 1.5)
    

class MountingHoleGenerator(FootprintGenerator):
    def __init__(self, diameter):
        self.diameter = diameter
    def create(self, layer, x, y, netfunc = None):
        return MountingHoleModule(x, y, self.diameter, layer)
    def get_size_name(self):
        return "hole_%gmm" % self.diameter

class MountingHoleGenerators:
    metric = {}
    for size in range(6, 13):
        metric["hole_%gmm" % (size / 2.0)] = MountingHoleGenerator(size / 2.0)

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
            xyat = exmatrix.get_pad_location_and_type(x, y)
            if xyat is not None:
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
                        left_xyat = exmatrix.get_pad_location_and_type(x - 1, y)
                        if left_xyat is not None:
                            xline = (xyat[0] + left_xyat[0]) / 2 + xmid
                            pcbf.append(GraphicLine(xline, xyat[1] - pitch / 2 + ymid, xline , xyat[1] + pitch / 2 + ymid, layer = "F.SilkS", width = widthmetric(net, netl)))
                            if widthmetric2(net, netl) > 0:
                                pcbf.append(GraphicLine(xline, xyat[1] - pitch / 2 + ymid, xline , xyat[1] + pitch / 2 + ymid, layer = "B.SilkS", width = widthmetric2(net, netl)))
                        else:
                            leftbound = True
                if x < cols - 1:
                    netr = getnet(x + 1, y)
                    if netr is None:
                        rightbound = True
                    right_xyat = exmatrix.get_pad_location_and_type(x + 1, y)
                    if right_xyat is None:
                        rightbound = True
                if leftbound:
                    xline = xyat[0] - pitch / 2 + xmid
                    pcbf.append(GraphicLine(xline, xyat[1] - pitch / 2 + ymid, xline , xyat[1] + pitch / 2 + ymid, layer = "F.SilkS", width = 0.3))
                    pcbf.append(GraphicLine(xline, xyat[1] - pitch / 2 + ymid, xline , xyat[1] + pitch / 2 + ymid, layer = "B.SilkS", width = 0.3))
                if rightbound:
                    xline = xyat[0] + pitch / 2 + xmid
                    pcbf.append(GraphicLine(xline, xyat[1] - pitch / 2 + ymid, xline , xyat[1] + pitch / 2 + ymid, layer = "F.SilkS", width = 0.3))
                    pcbf.append(GraphicLine(xline, xyat[1] - pitch / 2 + ymid, xline , xyat[1] + pitch / 2 + ymid, layer = "B.SilkS", width = 0.3))
                topbound = y == 0
                bottombound = y == rows - 1
                if y > 0:
                    netu = getnet(x, y - 1)
                    if netu is None:
                        topbound = True
                    else:
                        up_xyat = exmatrix.get_pad_location_and_type(x, y - 1)
                        if up_xyat is None:
                            topbound = True
                        elif net != netu:
                            yline = (xyat[1] + up_xyat[1]) / 2 + ymid
                            pcbf.append(GraphicLine(xyat[0] - pitch / 2 + xmid, yline, xyat[0] + pitch / 2 + xmid, yline, layer = "F.SilkS", width = widthmetric(net, netu)))
                            if widthmetric2(net, netu) > 0:
                                pcbf.append(GraphicLine(xyat[0] - pitch / 2 + xmid, yline, xyat[0] + pitch / 2 + xmid, yline, layer = "B.SilkS", width = widthmetric2(net, netu)))
                if y < rows - 1:
                    netr = getnet(x, y + 1)
                    if netr is None:
                        bottombound = True
                    bottom_xyat = exmatrix.get_pad_location_and_type(x, y + 1)
                    if bottom_xyat is None:
                        bottombound = True
                if topbound:
                    yline = xyat[1] - pitch / 2 + ymid
                    pcbf.append(GraphicLine(xyat[0] - pitch / 2 + xmid, yline, xyat[0] + pitch / 2 + xmid, yline, layer = "F.SilkS", width = 0.3))
                    pcbf.append(GraphicLine(xyat[0] - pitch / 2 + xmid, yline, xyat[0] + pitch / 2 + xmid, yline, layer = "B.SilkS", width = 0.3))
                if bottombound:
                    yline = xyat[1] + pitch / 2 + ymid
                    pcbf.append(GraphicLine(xyat[0] - pitch / 2 + xmid, yline, xyat[0] + pitch / 2 + xmid, yline, layer = "F.SilkS", width = 0.3))
                    pcbf.append(GraphicLine(xyat[0] - pitch / 2 + xmid, yline, xyat[0] + pitch / 2 + xmid, yline, layer = "B.SilkS", width = 0.3))
