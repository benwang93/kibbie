"""
Servo angle commander

Setup:
- Connect Pi servo hat to DC power (9V, 4A)
- Command servo to the neutral position via this program
- Attach servo to feeder assembly such that servo neutral is when 2 paddles are perfectly vertical
- Send any integer to command that angle, "h" for help.

Angles:
- Servo door
  - Extended: 138 degrees
  - Retracted: 5 degrees

""" 

from adafruit_servokit import ServoKit
import time

# The channel the servo is plugged into
channel = 1

# Counters
current_angle = 0   # Current servo angle

def go_to_angle(target_angle):
    global current_angle

    kit.servo[0].angle = target_angle+1
    time.sleep(0.5)
    kit.servo[0].angle = target_angle-1
    time.sleep(0.3)
    kit.servo[0].angle = target_angle
    kit.servo[channel].angle = target_angle
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
        "  h        print this help\n" +\
        "  <int>    go to angle in degrees\n" +\
        "  p        print status (angle and food dispensed)\n" +\
        "  q        quit\n"
    )

def print_status():
    global current_angle, dispense_count
    print("Kibbie status:")
    print(f"  Current angle: {current_angle}")
    print("\n\n")

# Initial setup
kit = ServoKit(channels=16)

kit.servo[channel].actuation_range = 180
kit.servo[channel].set_pulse_width_range(500, 2500)

# Now dispense food once
print("Loading complete!")
print_help()

while True:
    print("\n-----------------------------------\n")
    command = input("Please enter a command: ")

    if command == "h":
        print_help()
    elif command == "p":
        print_status()
    elif command == "q":
        break
    else:
        # Attempt to decode an angle
        try:
            angle = int(command)
            print(f"Commanding angle {angle} degrees")
            go_to_angle(angle)
            print(f"...done!")
        except:
            print(f"Unrecognized command '{command}'!\n")

print(f"Kibbie shutting down!")