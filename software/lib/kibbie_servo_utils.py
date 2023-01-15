"""
Library to provide Kibbie servo functions

For desktop development, set IS_RASPBERRY_PI to False
"""

# IS_RASPBERRY_PI = True # Raspberry Pi
IS_RASPBERRY_PI = False # Desktop

DEV_VIDEO_PROCESSING = True # Set to True to skip servo motor init

SKIP_SERVO_WAIT = not IS_RASPBERRY_PI and DEV_VIDEO_PROCESSING

import time

if IS_RASPBERRY_PI:
    from adafruit_servokit import ServoKit
else:
    # Stub out ServoKit for desktop development
    class Motor:
        def __init__(self):
            self.angle = 0.0
            self.actuation_range = 180
        
        def set_pulse_width_range(self, min, max):
            print(f"Set pulse width range to ({min}, {max})")
    class ServoKit:
        def __init__(self, channels):
            self.servo = [Motor() for _ in range(channels)]
            print(f"Initialized ServoKit instance with {channels} channels")


########################
# Constants
########################

# Servo channel definitions
NUM_CHANNELS = 16
NUM_CHANNELS_USED = 16
CHANNEL_DOOR_LEFT = 0
CHANNEL_DISPENSER_LEFT = 4
CHANNEL_DOOR_RIGHT = 8
CHANNEL_DISPENSER_RIGHT = 12

# Dispenser angle definitions
ANGLE_NEUTRAL = 90
NUM_PADDLES = 5
ANGLE_DISPENSE_1 = ANGLE_NEUTRAL - 360 / NUM_PADDLES
ANGLE_DISPENSE_2 = ANGLE_NEUTRAL + 360 / NUM_PADDLES

# Door angle definitions
ANGLE_DOOR_LEFT_OPEN = 40       # Calibrated offset angle for fully retracted (open) door
ANGLE_DOOR_LEFT_CLOSED = 162    # Calibrated offset angle for fully extended (closed) door

ANGLE_DOOR_RIGHT_OPEN = 162     # Calibrated offset angle for fully retracted (open) door
ANGLE_DOOR_RIGHT_CLOSED = 32    # Calibrated offset angle for fully extended (closed) door

class kibbie_servo_utils:
    def __init__(self):
        # Counters
        self.current_angles = []   # Current servo angle
        self.dispense_count = 0  # Total number of dispenses

        # Insatnce of ServoKit to perform controls
        self.kit = ServoKit(channels=NUM_CHANNELS)

    # Return true if the servo moved
    def go_to_angle(self, channel, target_angle):
        # Check if no movement was needed
        if target_angle == self.current_angles[channel]:
            return False
        
        # For development only, to speed up program
        if not SKIP_SERVO_WAIT:
            self.kit.servo[channel].angle = target_angle+1
            time.sleep(1)
            self.kit.servo[channel].angle = target_angle-1
            time.sleep(1)
            self.kit.servo[channel].angle = target_angle

            self.current_angles[channel] = target_angle

        print(f"Moved servo channel {channel} to {target_angle}")
        return True
    

    def print_help(self):
        print(
            "\n" + \
            "==============\n" + \
            "Kibbie\n" + \
            "==============\n" + \
            "\n" +\
            "Commands:\n" +\
            "\n" +
            "  d    dispense\n" +\
            "  h    print this help\n" +\
            "  c    close door\n" +\
            "  o    open door\n" +\
            "  n    go to neutral\n" +\
            "  1    go to dispense 1 position\n" +\
            "  2    go to dispense 2 position\n" +\
            "  p    print status (angle and food dispensed)\n" +\
            "  q    quit\n"
        )

    def print_status(self):
        print("Kibbie status:")
        for channel in range(NUM_CHANNELS_USED):
            print(f"  Current angle[{channel}]: {self.current_angles[channel]}")
        print(f"  Total dispenses: {self.dispense_count}")

    def dispense_food(self, channel):
        if self.current_angles[channel] == ANGLE_DISPENSE_1:
            self.go_to_angle(channel, ANGLE_DISPENSE_2)
        else:
            self.go_to_angle(channel, ANGLE_DISPENSE_1)
        
        # Track number of dispenses
        self.dispense_count += 1

        print("Food dispensed!\n")

    # Initial setup
    def init_servos(self):
        for channel_num in range(NUM_CHANNELS_USED):
            self.kit.servo[channel_num].actuation_range = 180
            self.kit.servo[channel_num].set_pulse_width_range(500, 2500)

            # Track per-servo angles
            self.current_angles.append(0)

        # For development only, to speed up program
        if SKIP_SERVO_WAIT:
            return
        
        # Start with door open (in case food falls as servos initialize)
        self.go_to_angle(CHANNEL_DOOR_LEFT, ANGLE_DOOR_LEFT_OPEN)
        self.go_to_angle(CHANNEL_DOOR_RIGHT, ANGLE_DOOR_RIGHT_OPEN)

        # Initial prompt for whether the initialization sequence should be run
        init_cmd = input("\nInitializing servos. Does food need to be loaded into the dispenser? (Y/n): ")
        if init_cmd == "Y":
            # We need authority in both directions, so 90 degrees is neutral
            print("Setting angle to neutral (90 degrees)")
            self.go_to_angle(CHANNEL_DISPENSER_LEFT, ANGLE_NEUTRAL)
            self.go_to_angle(CHANNEL_DISPENSER_RIGHT, ANGLE_NEUTRAL)

            # Wait for food to be loaded
            print("90 degrees achieved! Please pour food in")
            _ = input("\nHit enter to continue")

            # Load food into side 2 by moving paddles to side 1
            print("Loading side 2...")
            self.go_to_angle(CHANNEL_DISPENSER_LEFT, ANGLE_DISPENSE_1)
            self.go_to_angle(CHANNEL_DISPENSER_RIGHT, ANGLE_DISPENSE_1)
            time.sleep(1.5)

        # Now turn to side 2 to load side 1 with food
        print("Loading side 1...")
        self.go_to_angle(CHANNEL_DISPENSER_LEFT, ANGLE_DISPENSE_2)
        self.go_to_angle(CHANNEL_DISPENSER_RIGHT, ANGLE_DISPENSE_2)
        time.sleep(1.5)

        # Now give operator a chance to empty the tray back into the hopper
        _ = input("\nDispenser loaded. Please empty the food tray back into the hopper and hit Enter to continue.")

        # Close the door
        print("Closing the door in 5 seconds...")
        time.sleep(5.0)
        print("Closing the door...")
        self.go_to_angle(CHANNEL_DOOR_LEFT, ANGLE_DOOR_LEFT_CLOSED)
        self.go_to_angle(CHANNEL_DOOR_RIGHT, ANGLE_DOOR_RIGHT_CLOSED)
