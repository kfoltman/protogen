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
    pcbf.netlist.nets.append('HDR5_%d' % (i + 1))
    pcbf.netlist.nets.append('HDR6_%d' % (i + 1))
    
def getnet_stm32(group, index):
    if group == 0:
        return "GND"
    if group == cols - 5:
        return "VCC1"
    if (group == cols - 4 or group == cols - 3) and index > 3 and index < 28:
        return "HDR5_%d" % (index + 1)
    if (group == cols - 2 or group == cols - 1) and index > 3 and index < 28:
        return "HDR6_%d" % (index + 1)
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
    
def getpadclass(group, index):
    net = getnet_stm32(group, index)
    is_vertical = group == 0 or group == cols - 5 or net not in ['VCC1', 'VCC2', 'GND']
    if net == 'GND':
        return StdTHTPad.rect90 if not is_vertical else StdTHTPad.rect
    return StdTHTPad.oval90 if net in ['VCC1', 'VCC2'] and not is_vertical else StdTHTPad.oval

xo = 50
yo = 50
xsize = 100
ysize = 100

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

matrix = THTMatrixGrid(rows = rows, columns = cols, hpitch = pitch, vpitch = pitch, padfunc = getpadclass)
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
    vspacing2 = 9
    if bo == 2:
        vspacing = 7
        gen = SMDFootprintGenerators.SOIC_W[pins]
        gen2 = SMDFootprintGenerators.SSOP_440[pins]
    elif bo == 1:
        vspacing = 7
        gen = SMDFootprintGenerators.SOIC_W[pins]
        gen2 = SMDFootprintGenerators.SSOP_530[pins]
    else:
        vspacing = 7
        gen = SMDFootprintGenerators.SOIC_N[pins]
        gen2 = SMDFootprintGenerators.SSOP_440[pins]
    yfp = matrix_extremes.ey - vspacing2 / 2.0 * pitch

    mod1 = gen.create("F.Cu", xfp, yfp, pinnum)
    pcbf.append(mod1)
    excl.append(mod1.get_bounding_rect())

    mod2 = gen2.create("B.Cu", xfp, yfp, pinnum)
    pcbf.append(mod2)
    excl.append(mod2.get_bounding_rect())
    
    if bo == 1:
        pcbf.append(GraphicText("http://thisisnotrocketscience.nl/", xfp, yfp, "F.SilkS", 0, sizex = 1.1, sizey = 1.2, thickness = 0.15))

    dilmod = PCBModule('dil%d' % pins, 'F.Cu', xfp, yfp)
    dilmod.create_pads(DILGrid(pins, vspacing), pinnum)
    pcbf.append(dilmod)
    
    has_discretes = bo == 0
    
    if vspacing < vspacing2:
        dilmod2 = PCBModule('dil%d' % pins, 'F.Cu', xfp, yfp)
        dilmod2.create_pads(DILGrid(pins, vspacing2), pinnum)
        pcbf.append(dilmod2)
        excl.append(dilmod2.get_bounding_rect())
        if has_discretes:
            mod3 = DILSMD("discretes", padwidth = 1.6, padheight = 1.9, pitch = 2.54, midline = pitch * (vspacing - 2), pins = pins).create("F.Cu", xfp, yfp, pinnum)
            pcbf.append(mod3)
            
    else:
        excl.append(dilmod.get_bounding_rect())
    
    mid = (pins // 2 - 1) / 2.0
    for i in xrange(pins):
        if has_discretes:
            pcbf.append_all(smart_connect(mod3, mod1, i, pins, gen.grid.pitch))
            pcbf.append_all(smart_connect(dilmod, mod3, i, pins, gen.grid.pitch, smd = False))
        else:
            pcbf.append_all(smart_connect(dilmod, mod1, i, pins, gen.grid.pitch))
        pcbf.append_all(smart_connect(dilmod, mod2, i, pins, gen2.grid.pitch))
        if vspacing2 > vspacing:
            pcbf.append_all(smart_connect(dilmod2, dilmod, i, pins, gen2.grid.pitch, smd = False))
    if bo == 0:
        xline = xfp - 1.27 * pins / 2
        pcbf.append(GraphicLine(xline, yfp - (vspacing2 + 1) / 2 * pitch + 0.4, xline, yfp + (vspacing2 + 1) / 2 * pitch, layer = "F.SilkS", width = 0.4))
        pcbf.append(GraphicLine(xline, yfp - (vspacing2 + 1) / 2 * pitch + 0.4, xline, yfp + (vspacing2 + 1) / 2 * pitch, layer = "B.SilkS", width = 0.4))
    xline = xfp + 1.27 * pins / 2
    pcbf.append(GraphicLine(xline, yfp - (vspacing2 + 1) / 2 * pitch + 0.4, xline, yfp + (vspacing2 + 1) / 2 * pitch, layer = "F.SilkS", width = 0.4))
    pcbf.append(GraphicLine(xline, yfp - (vspacing2 + 1) / 2 * pitch + 0.4, xline, yfp + (vspacing2 + 1) / 2 * pitch, layer = "B.SilkS", width = 0.4))

holes = [
    MountingHoleModule(xo + 4.5, yo + 4.5, 3.2),
    MountingHoleModule(xe - 4.5, yo + 4.5, 3.2),
    MountingHoleModule(xo + 4.5, ye - 4.5, 3.2),
    MountingHoleModule(xe - 4.5, ye - 4.5, 3.2),
]
for h in holes:
    pcbf.append(h)
    excl += h.get_exclusions()
    
mod = PCBModule('grid', 'F.Cu', xmid, ymid)
exmatrix = GridWithExclusions(matrix, excl, (xmid, ymid))
tracks = mod.create_pads(exmatrix, getnet_stm32, tracks_layer = "B.Cu", widthfunc = lambda net: 30 * 0.0254)
pcbf.append(mod)
pcbf.append_all(tracks)
pcbf.append_all(bmp_to_silk((xo + xe) / 2, ymid - 6 * pitch, "rocket1.png", is_lit = lambda r, g, b, a: a > 0 and r > 0, scale = 0.25, center = True))
pcbf.append_all(bmp_to_silk2((xo + xe) / 2, ymid - 6 * pitch, "rocket1.png", is_lit = lambda r, g, b, a: a > 0 and r > 0, scale = 0.25, center = True))
make_silkscreen(cols, rows, exmatrix, pcbf, getnet_stm32, 2.54, xmid, ymid)

file("output.kicad_pcb", "w").write(pcbf.generate())
