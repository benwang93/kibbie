# Design notes

## Servo coupler

### Servo horn

Hole pattern

- Diameter of horn is 20.6mm
- Screw holes
  - 12.80mm is closest between y-axis opposite screw holes
  - Each screw hole is 1.45-1.5mm diameter
  - Designing with 1.45mm for now (making it tighter)
- Distance from horn center to screw hole center on x/y axes must then be
    (12.80 / 2) + 1.45/2 mm = 7.125mm

- Closest measurement between the 2 outer holes in a 3-row is 5.4mm
- So the spacing between 2 holes should be: (5.4mm + 1.45) / 2 = 3.425mm

### D Shaft design & plate thickness

- D shaft is around 5.65mm from flat side of D to the opposite side of circle
  - D shaft diameter is 7.60mm

How long should the shaft be? How thick should base plate be?

- Servo:
  - From screw plate top to top of servo horn is ~16mm
- Hand turn
  - Chrome part sits flush with black plastic when fully inserted
  - Rod is around 64mm long
  - at 39mm from chrome handle, the taper happens on the D shaft

- So from servo horn face to end of rod should be around (64 - 16) = 50mm
- For v1, we can have the screws enter from the far side from the servo and then poke out of the servo horn at the servo side. This would require our base piece to be around 6.5 mm
  - Screw is 10mm long (excluding the tip, which adds around another 1 mm)

Base plate thickness: 6.5mm
Shaft length: 50mm - 6.5mm = 44.5mm

### D Shaft taper

- Last 25mm of shaft is tapered
