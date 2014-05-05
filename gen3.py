from pcbfile import *
from chips import *
import math

pcbf = PCBFile()
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
xsize = 100
ysize = 100

xmid = xo + xsize / 2
ymid = yo + ysize / 2
xe = xo + xsize
ye = yo + ysize

pcbf.append(GraphicRect(xo, yo, xo + xsize, yo + ysize))
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

for bo in range(3):
    xofs = 6.5
    pins = 16
    if bo == 1:
        xofs += 11
        pins = 28
    if bo == 2:
        xofs += 23
        pins = 20
    for i in range(pins):
        pcbf.netlist.nets.append('BRK%d_%d' % (bo, i + 1))

    xfp = matrix_extremes.sx + xofs * pitch
    pinnum = lambda group, index: 'BRK%d_%d' % (bo, group * pins // 2 + index + 1)
    if bo == 2:
        vspacing = 7
        gen = SMDFootprintGenerators.SOIC_W[pins]
        gen2 = SMDFootprintGenerators.SSOP_440[pins]
    elif bo == 1:
        vspacing = 7
        gen = SMDFootprintGenerators.SOIC_W[pins]
        gen2 = SMDFootprintGenerators.SSOP_530[pins]
    else:
        vspacing = 5
        gen = SMDFootprintGenerators.SOIC_N[pins]
        gen2 = SMDFootprintGenerators.SSOP_440[pins]
    yfp = matrix_extremes.ey - vspacing / 2.0 * pitch

    mod1 = gen.create("F.Cu", xfp, yfp, pinnum)
    pcbf.append(mod1)
    excl.append(mod1.get_bounding_rect())

    mod2 = gen2.create("B.Cu", xfp, yfp, pinnum)
    pcbf.append(mod2)
    excl.append(mod2.get_bounding_rect())

    mod3 = PCBModule('dil%d' % pins, 'F.Cu', xfp, yfp)
    mod3.create_pads(DILGrid(pins, vspacing), pinnum)
    pcbf.append(mod3)
    excl.append(mod3.get_bounding_rect())
    
    mid = (pins // 2 - 1) / 2.0
    for i in xrange(pins):
        if i == 0 or i == pins-1 or i == pins // 2 or i == pins // 2 - 1:
            yshift = 0
        elif i < pins // 2:
            yshift = mod1.pads[i].padclass.sizey / 2
        else:
            yshift = -mod1.pads[i].padclass.sizey / 2
        pcbf.append(TraceSegment(xfp + mod1.pads[i].x, yfp + mod1.pads[i].y + yshift, xfp + mod3.pads[i].x, yfp + mod3.pads[i].y, mod1.pads[i].netname, 0.254, "F.Cu"))
        if i == 0 or i == pins-1 or i == pins // 2 or i == pins // 2 - 1:
            yshift = 0
        elif i < pins // 2:
            yshift = mod2.pads[i].padclass.sizey / 2
        else:
            yshift = -mod2.pads[i].padclass.sizey / 2
        ix = i % (pins // 2) - mid
        ix = ix * 1.0 / (mid - 1)
        yshift *= (1 + 1.5 * math.cos(ix * 3.14 / 2));
        if yshift != 0:
            pcbf.append(TraceSegment(xfp + mod2.pads[i].x, yfp + mod2.pads[i].y + yshift, xfp + mod2.pads[i].x, yfp + mod2.pads[i].y, mod2.pads[i].netname, 0.254, "B.Cu"))
        pcbf.append(TraceSegment(xfp + mod2.pads[i].x, yfp + mod2.pads[i].y + yshift, xfp + mod3.pads[i].x, yfp + mod3.pads[i].y, mod2.pads[i].netname, 0.254, "B.Cu"))

holes = [
    MountingHoleModule(xo + 5, yo + 5, 4),
    MountingHoleModule(xe - 5, yo + 5, 4),
    MountingHoleModule(xo + 5, ye - 5, 4),
    MountingHoleModule(xe - 5, ye - 5, 4),
]
for h in holes:
    pcbf.append(h)
    excl += h.get_exclusions()
    
def getnet_stm32(group, index):
    if group == 0:
        return "GND"
    if index < 3:
        return "HDR1_%d" % (group)
    if index < 6:
        return "HDR2_%d" % (group)
    if index < 10:
        return "GRP1_%d" % (group)
    if index == 10:
        return "GND"
    if index == 11:
        return "VCC1"
    if index < 17:
        return "GRP2_%d" % (group)
    if index < 20:
        return "GRP3_%d" % (group)
    if index < 23:
        return "HDR3_%d" % (group)
    if index < 26:
        return "HDR4_%d" % (group)
    if index == 26:
        return "GND"
    if index == 27:
        return "VCC2"
    return None
mod = PCBModule('grid', 'F.Cu', xmid, ymid)
mod.create_pads(GridWithExclusions(matrix, excl, (xmid, ymid)), getnet_stm32)
pcbf.append(mod)

file("output.kicad_pcb", "w").write(pcbf.generate())
