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

    dilmod = PCBModule('dil%d' % pins, 'F.Cu', xfp, yfp)
    dilmod.create_pads(DILGrid(pins, vspacing), pinnum)
    pcbf.append(dilmod)
    excl.append(dilmod.get_bounding_rect())

    def sgn(val):
        if val > 0:
            return 1
        if val < 0:
            return -1
        return 0
    def smart_connect(dilmod, smallmod, i, pins, pitch, width = 0.254):
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
        
        xs, ys = smallmod.pads[i].x, smallmod.pads[i].y
        xe, ye = dilmod.pads[i].x, dilmod.pads[i].y
        # Vertical line from the pad
        if ixsym > 0:
            ys += tdir * mod2.pads[i].padclass.sizey / 2
            space_per_trace = (abs(ye - ys) - dilmod.pads[i].padclass.sizey - width) / mid_pin
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
    
    mid = (pins // 2 - 1) / 2.0
    for i in xrange(pins):
        pcbf.append_all(smart_connect(dilmod, mod1, i, pins, gen.grid.pitch))
        pcbf.append_all(smart_connect(dilmod, mod2, i, pins, gen2.grid.pitch))

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
    if group >= cols - 3:
        return None
    if group == cols - 4:
        return "VCC1"
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
tracks = mod.create_pads(GridWithExclusions(matrix, excl, (xmid, ymid)), getnet_stm32, tracks_layer = "B.Cu", widthfunc = lambda net: 30 * 0.0254)
pcbf.append(mod)
pcbf.append_all(tracks)

file("output.kicad_pcb", "w").write(pcbf.generate())
