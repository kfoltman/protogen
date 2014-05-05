from pcbfile import *

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

