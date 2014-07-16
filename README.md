protogen
========

This is a set of protoboard generators. Included is a set of Python classes
and functions to generate KiCAD PCB files, and two generators to create example
protoboard layouts.

Examples
========

The first example is a 5x5 protoboard for simple circuits. It includes dedicated
area for a chip (or, depending on the size, more chips) in a DIL package, some
easy to use power routes and some pre-routed areas arranged in columns.

The second board has been designed for use with the STM32F4DISCOVERY development 
board, but can be used for other things too. Like the first board, it has connected
groups as columns and some dedicated power traces. However, it also has a set
of breakouts for ICs in 1.27mm SOIC and 0.65mm (T)SSOP packages, which may be useful
for things like ADCs or NOR flash or port expanders. I've even built a small
microcontroller board with it, using one of the STM32F030 chips in TSSOP20
package.
