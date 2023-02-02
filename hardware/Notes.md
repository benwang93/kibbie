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

## Kibbie Monitor Circuit Design

### Design requirements:
- P1: Monitor each dispenser's servo motor current (3 servos per corral, 2 corrals total)
- P1: Communicate overcurrent per-side to Raspberry Pi for shutting down bad side and falling back to single side operation
- P1: Ability to shut off servos on overcurrent. This might be doable via thee Raspberry Pi though?
- P1: Run off of 5V power from PSU
- P2: Watchdog via GPIO, where Raspberry Pi toggles a GPIO while Kibbie program is alive
- P2: Ability to cut power to Raspberry Pi if watchdog sees failure (5V relay, but to Kibbie)

### Components:
- USB A Breakout: https://www.sparkfun.com/products/12700
- Arduino Uno breadboard shield: https://www.sparkfun.com/products/13819
- Current sensor: https://www.sparkfun.com/products/12040
- Current sensor resistor:
  - 0.1 Ohm 5W 10 pcs: https://smile.amazon.com/HUABAN-10PCS-Watts-Metal-Resistor/dp/B08LW2THTJ

### Current monitoring:

#### Selecting R_S
Stall current of each servo is around 3A (https://smile.amazon.com/dp/B07MFK266B). 2 servos active at once (door + door lock) would be 6A.

From the Sparkfun hookup guide:

          V_OUT * 1kOhm
  I_S = ----------------
          R_S * R_L

To not consume too much power on the current sense resistor (so it's not terribly big), we could do:

P = I^2 * R

Let I = 6A. For a max power of 1.5W (so that we could use a 3W resistor), we would need around R = 1.5 W / 6A ^ 2 = 0.0417 Ohms. Can probably round up and use a **0.05 Ohm resistor, 3W**.

#### Selecting R_L

Next is to select a R_L. To get a reasonable voltage reading, let's say max current of 8A (which is what our power supply can do):

            I_S * 1kOhm
  V_OUT = ----------------
            R_S * R_L
            
            I_S * 1kOhm
  R_L = ----------------
            R_S * V_OUT

So at max current:

          8A * 1kOhm
  R_L = ---------------- = 32 kOhm, and a larger R_L would give a lower V_max. So we should be no less than 32 kOhm on R_L
          0.05Ohm * 5V

**Either 33k or 39k Ohm should work.**

#### Final voltages

Using:
            I_S * 1kOhm
  V_OUT = ----------------
            R_S * R_L

and R_S = 0.05 Ohm, R_L = 33 kOhm:

I_S   V_OUT         P_R (W)
0.1	  0.060606061	  0.0005
0.5	  0.303030303	  0.0125
1	    0.606060606	  0.05
1.5	  0.909090909	  0.1125
2	    1.212121212	  0.2
3	    1.818181818	  0.45
4	    2.424242424	  0.8
5	    3.03030303	  1.25
6	    3.636363636	  1.8
7	    4.242424242	  2.45
8	    4.848484848	  3.2

(See hardware/Electrical/Current_sense_calculations.xlsx)

### Reference:
- Current sensor hookup guide: https://learn.sparkfun.com/tutorials/ina169-breakout-board-hookup-guide
