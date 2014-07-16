from pcbfile import *
from chips import *
import math
import re

pcbf = PCBFile(tracewidth = 30, clearance = 30)
pcbf.netlist.nets.append('GND')
pcbf.netlist.nets.append('VCC1')
pcbf.netlist.nets.append('VCC2')
for i in range(39):
    pcbf.netlist.nets.append('HDR1_%d' % (i + 1))
    pcbf.netlist.nets.append('HDR2_%d' % (i + 1))
    pcbf.netlist.nets.append('HDR3_%d' % (i + 1))
    pcbf.netlist.nets.append('HDR4_%d' % (i + 1))
    pcbf.netlist.nets.append('GRP1_%d' % (i + 1))
    pcbf.netlist.nets.append('GRP2_%d' % (i + 1))
    pcbf.netlist.nets.append('GRP3_%d' % (i + 1))
    
xo = 50
yo = 50
xsize = 50
ysize = 50

xmid = xo + xsize / 2
ymid = yo + ysize / 2
xe = xo + xsize
ye = yo + ysize

pcbf.append(GraphicRect(xo, yo, xo + xsize, yo + ysize, roundness = 4))
pitch = 2.54
rows = int(xsize / pitch) - 1
cols = int(ysize / pitch) - 1

print "%d rows, %d columns" % (rows, cols)

#pcbf.append(TraceSegment(60, 60, 90, 60, 'GND'))

#mod = PCBModule('dil28', 'F.Cu', 75, 75)
#mod.create_pads(DILGrid.small(28), lambda group, index: 'PIN%d' % (group * 14 + index + 1))

def getnet_stm32(group, index):
    if group == 0:
        return "GND"
    if group == cols - 1:
        return "VCC1"
    if index < 3:
        if group == 1:
            return "GND"
        if group == cols - 2:
            return "VCC1"
        return "HDR1_%d" % (group)
    if index < 6:
        return "HDR2_%d" % (group)
    if index < 10:
        return "GRP1_%d" % (group)
    if index == 10:
        return "GND"
    if index == 11:
        return "VCC1"
    if index < 16:
        return "GRP2_%d" % (group)
    if index < 20:
        return "GRP3_%d" % (group)
    return None
    
def getpadclass(group, index):
    net = getnet_stm32(group, index)
    is_vertical = group == 0 or group == cols - 1 or net not in ['VCC1', 'GND']
    if net == 'GND':
        return StdTHTPad.rect90 if not is_vertical else StdTHTPad.rect
    return StdTHTPad.oval90 if net in ['VCC1'] and not is_vertical else StdTHTPad.oval

matrix = THTMatrixGrid(rows = rows, columns = cols, hpitch = pitch, vpitch = pitch, padfunc = getpadclass)
matrix_extremes = matrix.get_extremes().offset(xmid, ymid)

excl = []

holes = [
    MountingHoleModule(xo + 4.5, yo + 4.5, 3.2),
    MountingHoleModule(xe - 4.5, yo + 4.5, 3.2),
    MountingHoleModule(xo + 4.5, ye - 4.5, 3.2),
    MountingHoleModule(xe - 4.5, ye - 4.5, 3.2),
]
for h in holes:
    pcbf.append(h)
    excl += h.get_exclusions()
    
exmatrix = GridWithExclusions(matrix, excl, (xmid, ymid))
mod = PCBModule('grid', 'F.Cu', xmid, ymid)
tracks = mod.create_pads(exmatrix, getnet_stm32, tracks_layer = "B.Cu", widthfunc = lambda net: 30 * 0.0254)
pcbf.append(mod)
for t in tracks:
    pcbf.append(t)

for i in xrange(cols):
    xyt = matrix.get_pad_location_and_type(i, 0)
    if xyt is not None:
        t = GraphicText("%c" % (65 + i), xyt[0] + xmid, xyt[1] + ymid - 2.54 + 0.3, "F.SilkS", 0, sizex = 1, sizey = 1.3)
        pcbf.append(t)
        t = GraphicText("%c" % (65 + i), xyt[0] + xmid, xyt[1] + ymid - 2.54 + 0.3, "B.SilkS", 0, sizex = 1, sizey = 1.3)
        pcbf.append(t)
    xyt = matrix.get_pad_location_and_type(i, rows - 1)
    if xyt is not None:
        t = GraphicText("%c" % (65 + i), xyt[0] + xmid, xyt[1] + ymid + 2.54 - 0.3, "F.SilkS", 0, sizex = 1, sizey = 1.3)
        pcbf.append(t)
        t = GraphicText("%c" % (65 + i), xyt[0] + xmid, xyt[1] + ymid + 2.54 - 0.3, "B.SilkS", 0, sizex = 1, sizey = 1.3)
        pcbf.append(t)

for i in xrange(rows):
    xyt = matrix.get_pad_location_and_type(0, i)
    if xyt is not None:
        t = GraphicText("%d" % (1 + i), xyt[0] + xmid - 2.54 + 0.3, xyt[1] + ymid, "F.SilkS", 0, sizex = 1, sizey = 0.9, thickness = 0.15)
        pcbf.append(t)
        t = GraphicText("%d" % (1 + i), xyt[0] + xmid - 2.54 + 0.3, xyt[1] + ymid, "B.SilkS", 0, sizex = 1, sizey = 0.9, thickness = 0.15)
        pcbf.append(t)
    xyt = matrix.get_pad_location_and_type(cols - 1, i)
    if xyt is not None:
        t = GraphicText("%d" % (1 + i), xyt[0] + xmid + 2.54 - 0.3, xyt[1] + ymid, "F.SilkS", 0, sizex = 1, sizey = 0.9, thickness = 0.15)
        pcbf.append(t)
        t = GraphicText("%d" % (1 + i), xyt[0] + xmid + 2.54 - 0.3, xyt[1] + ymid, "B.SilkS", 0, sizex = 1, sizey = 0.9, thickness = 0.15)
        pcbf.append(t)

make_silkscreen(cols, rows, exmatrix, pcbf, getnet_stm32, 2.54, xmid, ymid)

file("proto5x5_2sidedsilk.kicad_pcb", "w").write(pcbf.generate())
