"""
Feeder demo

Setup:
- Connect Pi servo hat to DC power (9V, 4A)
- Command servo to the neutral position via this program
- Attach servo to feeder assembly such that servo neutral is when 2 paddles are perfectly vertical
- Send "d" command to dispense food, "h" for help.

""" 

from adafruit_servokit import ServoKit
import time

# Angle definitions
ANGLE_NEUTRAL = 90
NUM_PADDLES = 5
ANGLE_DISPENSE_1 = ANGLE_NEUTRAL - 360 / NUM_PADDLES
ANGLE_DISPENSE_2 = ANGLE_NEUTRAL + 360 / NUM_PADDLES

# Counters
current_angle = 0   # Current servo angle
dispense_count = 0  # Total number of dispenses

def go_to_angle(target_angle):
    global current_angle

    kit.servo[0].angle = target_angle+1
    time.sleep(1)
    kit.servo[0].angle = target_angle-1
    time.sleep(1)
    kit.servo[0].angle = target_angle
    current_angle = target_angle

def print_help():
    print(
        "\n" + \
        "==============\n" + \
        "Kibbie console\n" + \
        "==============\n" + \
        "\n" +\
        "Commands:\n" +\
        "\n" +
        "  d    dispense\n" +\
        "  h    print this help\n" +\
        "  n    go to neutral\n" +\
        "  1    go to dispense 1 position\n" +\
        "  2    go to dispense 2 position\n" +\
        "  p    print status (angle and food dispensed)\n" +\
        "  q    quit\n"
    )

def print_status():
    global current_angle, dispense_count
    print("Kibbie status:")
    print(f"  Current angle: {current_angle}")
    print(f"  Total dispenses: {dispense_count}")
    print("\n\n")

def dispense_food():
    global current_angle, dispense_count
    if current_angle == ANGLE_DISPENSE_1:
        go_to_angle(ANGLE_DISPENSE_2)
    else:
        go_to_angle(ANGLE_DISPENSE_1)
    
    # Track number of dispenses
    dispense_count += 1

    print("Food dispensed!\n")

# Initial setup
kit = ServoKit(channels=16)

kit.servo[0].actuation_range = 180
kit.servo[0].set_pulse_width_range(500, 2500)

# We need authority in both directions, so 90 degrees is neutral
print("Setting angle to neutral (90 degrees)")

# In order to reduce motor chatter, we need to always overshoot the angle, wait a bit, then go to the desired angle
go_to_angle(ANGLE_NEUTRAL)

# Wait for food to be loaded
print("90 degrees achieved! Please pour food in")
_ = input("Hit enter to continue")

# Now we need to load food into the feeder. Do this by turning in either direction enough to load the paddles, but not enough to dispense
print("Loading side 1...")
go_to_angle(ANGLE_DISPENSE_1)

time.sleep(1.5)

# Now dispense food once
print("Loading complete!")
print_help()

while True:
    print("\n-----------------------------------\n")
    command = input("Please enter a command: ")

    if command == "d":
        dispense_food()
    elif command == "h":
        print_help()
    elif command == "n":
        go_to_angle(ANGLE_NEUTRAL)
    elif command == "1":
        go_to_angle(ANGLE_DISPENSE_1)
    elif command == "2":
        go_to_angle(ANGLE_DISPENSE_2)
    elif command == "p":
        print_status()
    elif command == "q":
        break
    else:
        print("Unrecognized command!\n")

print(f"Kibbie shutting down after {dispense_count} dispenses!")