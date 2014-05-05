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

matrix = THTMatrixGrid(rows = rows, columns = cols, hpitch = pitch, vpitch = pitch)
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
exmatrix = GridWithExclusions(matrix, excl, (xmid, ymid))
mod = PCBModule('grid', 'F.Cu', xmid, ymid)
mod.create_pads(exmatrix, getnet_stm32)
pcbf.append(mod)

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

def widthmetric(net1, net2):
    if re.sub("_.*", "", net1) == re.sub("_.*", "", net2):
        return 0.2
    return 0.3
        
def widthmetric2(net1, net2):
    if re.sub("_.*", "", net1) == re.sub("_.*", "", net2):
        return 0
    return 0.2
        
for x in xrange(0, cols):
    for y in xrange(0, rows):
        xyt = exmatrix.get_pad_location_and_type(x, y)
        if xyt is not None:
            net = getnet_stm32(x, y)
            if net is None:
                continue
            leftbound = x == 0
            rightbound = x == cols - 1
            if x > 0:
                netl = getnet_stm32(x - 1, y)
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
                netr = getnet_stm32(x + 1, y)
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
                netu = getnet_stm32(x, y - 1)
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
                netr = getnet_stm32(x, y + 1)
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

file("proto5x5_2sidedsilk.kicad_pcb", "w").write(pcbf.generate())
