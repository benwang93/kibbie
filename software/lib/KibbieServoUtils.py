"""
Library to provide Kibbie servo functions

For desktop development, set IS_RASPBERRY_PI to False
"""

IS_RASPBERRY_PI = True # Raspberry Pi
# IS_RASPBERRY_PI = False # Desktop

DEV_VIDEO_PROCESSING = True # Set to True to skip servo motor init
DEBUG_SERVO_QUEUE = False # Set to True to print per-channel servo queue information

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
            if DEBUG_SERVO_QUEUE:
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
CHANNEL_DISPENSER_LEFT = 11
CHANNEL_DOOR_RIGHT = 8
CHANNEL_DISPENSER_RIGHT = 12

# Dispenser angle definitions
ANGLE_NEUTRAL = 90
NUM_PADDLES = 5
ANGLE_DISPENSE_1 = ANGLE_NEUTRAL - 360 / NUM_PADDLES
ANGLE_DISPENSE_2 = ANGLE_NEUTRAL + 360 / NUM_PADDLES

# Door angle definitions
ANGLE_DOOR_LEFT_OPEN = 10       # Calibrated offset angle for fully retracted (open) door
ANGLE_DOOR_LEFT_CLOSED = 140    # Calibrated offset angle for fully extended (closed) door

ANGLE_DOOR_RIGHT_OPEN = 162     # Calibrated offset angle for fully retracted (open) door
ANGLE_DOOR_RIGHT_CLOSED = 32    # Calibrated offset angle for fully extended (closed) door

# Door lock servo angle definitions

# Build procedure:
# 1. Set servo to 90 degrees while unattached
# Attach lock arm, pointing slightly downwards from horizontal (first spline mesh angle)
# Use servo angle comander to lower the arm until it's parallel with the track.
# Increase angle by 20 degrees
# Slide lock assembly down until snug with closed door
# Tighten servo lock assembly screws and note the angles below
ANGLE_DOOR_LOCK_LEFT_UNLOCKED = 110
ANGLE_DOOR_LOCK_LEFT_LOCKED = 130

# Timing calibration
# A typical servo actuation consists of 3 separate movements:
#  1. Target the angle + 1 degree
#  2. Wait 1s
#  3. Target the angle - 1 degree
#  4. Wait 1s
#  5. Target the actual target angle
# This results in a total actuation time of over 2 seconds.
# Thus, any consecutive actions should (eg., door open -> dispense food) should wait ~3s in between when queueing
NUM_SERVO_STEPS = 10 # Number of steps to open the door in 
DELAY_SERVO_WAIT = 1 # second
DELAY_SERVO_WAIT_STEPS = 0.3 # seconds; Special case for stepped servo operation (eg., time between door movements)

DELAY_CONSECUTIVE_SERVO_WAIT = 3 * DELAY_SERVO_WAIT # seconds
DELAY_CONSECUTIVE_SERVO_STEP_WAIT = (NUM_SERVO_STEPS * DELAY_SERVO_WAIT_STEPS) + (2 * DELAY_SERVO_WAIT) # seconds

from numpy import arange

# Class to represent a servo queue item
# Each item contains a `timestamp` at which the servo `angle` should be commanded
class servo_queue_item:
    def __init__(self, time, angle):
        self.time = time
        self.angle = angle
    
    def __str__(self):
        return f"(t={self.time}, a={self.angle})"
    
    def __repr__(self):
        return self.__str__()

class KibbieServoUtils:
    def __init__(self, logfile):
        # Logging
        self.logfile = logfile

        # Save startup time to track uptime
        self.init_time = time.time()

        # Counters
        self.current_angles = []   # Current servo angle
        self.dispense_count = {}   # Total number of dispenses per channel

        # Insatnce of ServoKit to perform controls
        self.kit = ServoKit(channels=NUM_CHANNELS)

        # Queue for servo actions to check via run_loop()
        # `channel_queue`` is indexed by servo channel
        # Each element within channel_queue is a per-channel queue containing `servo_queue_item` objects.
        self.channel_queue = []


    def log(self, s):
        output = f"[{time.asctime()}][KibbieServoUtils] {s}"
        self.logfile.write(f"{output}\n")
        self.logfile.flush()
        print(output)


    def run_loop(self):
        current_time = time.time()
        for channel,queue in enumerate(self.channel_queue):
            # Check for actions to perform
            if len(queue) > 0 and queue[0].time <= current_time:
                start_angle = self.kit.servo[channel].angle
                new_angle = self.channel_queue[channel].pop(0).angle

                # Pop the head of queue
                self.kit.servo[channel].angle = new_angle
                if DEBUG_SERVO_QUEUE:
                    self.log(f"[Ch {channel}]: Angle before: {start_angle} \tAngle now: {new_angle} \tQueue after run_loop: {self.channel_queue[channel]}")


    def queue_angle(self, channel, target_angle, offset_seconds=0):
        # Check if no movement was needed
        if target_angle == self.current_angles[channel]:
            return False

        current_time = time.time()

        # Clear the queue for the current motor
        self.channel_queue[channel] = []

        # Queue servo movement for 1 s (with overshoot)
        self.channel_queue[channel].append(servo_queue_item(current_time + 0 * DELAY_SERVO_WAIT + offset_seconds, target_angle + 1))
        self.channel_queue[channel].append(servo_queue_item(current_time + 1 * DELAY_SERVO_WAIT + offset_seconds, target_angle - 1))
        self.channel_queue[channel].append(servo_queue_item(current_time + 2 * DELAY_SERVO_WAIT + offset_seconds, target_angle))

        # Set the angle ahead of time so that we don't double queue if we try to go to this angle again
        # Opportunity to do a "smart queue" above to only move the motor in one direction and to cancel existing movements if going the other way.
        self.current_angles[channel] = target_angle

        return True


    # Performs operation in 3 distinct steps. Intended for door operation
    # Goal is to give the cat a warning, then move most of the way (but not pinch paws), then fully open/close
    def queue_angle_stepped(self, channel, target_angle, offset_seconds=0):
        # Check if no movement was needed
        if target_angle == self.current_angles[channel]:
            return False

        current_time = time.time()

        # Clear the queue for the current motor
        self.channel_queue[channel] = []
        
        # Additional steps
        total_movement_angle = target_angle - self.current_angles[channel]
        start_angle = self.current_angles[channel]

        # Define the proportion of the way to move at each step
        # angle_proportions = [
        #     0.1,
        #     0.75,
        #     1.0,
        # ]
        angle_proportions = list(arange(0.0, 1.001, 1.0 / NUM_SERVO_STEPS))

        # Compute actual angles
        angles = [int(proportion * total_movement_angle + start_angle) for proportion in angle_proportions]

        # Queue servo movement for 1 s (with overshoot)
        delta_t = current_time + offset_seconds
        for angle in angles:
            # Always target +1 degrees to help prevent chatter
            self.channel_queue[channel].append(servo_queue_item(delta_t, angle + 1))
            delta_t += DELAY_SERVO_WAIT_STEPS
        self.channel_queue[channel].append(servo_queue_item(delta_t, target_angle - 1))
        delta_t += DELAY_SERVO_WAIT
        self.channel_queue[channel].append(servo_queue_item(delta_t, target_angle))

        # Set the angle ahead of time so that we don't double queue if we try to go to this angle again
        # Opportunity to do a "smart queue" above to only move the motor in one direction and to cancel existing movements if going the other way.
        self.current_angles[channel] = target_angle

        return True


    # Return true if the servo moved
    def go_to_angle(self, channel, target_angle):
        # Check if no movement was needed
        if target_angle == self.current_angles[channel]:
            return False
        
        # For development only, to speed up program
        if not SKIP_SERVO_WAIT:
            self.kit.servo[channel].angle = target_angle+1
            time.sleep(DELAY_SERVO_WAIT)
            self.kit.servo[channel].angle = target_angle-1
            time.sleep(DELAY_SERVO_WAIT)
            self.kit.servo[channel].angle = target_angle

            self.current_angles[channel] = target_angle

        self.log(f"Moved servo channel {channel} to {target_angle}")
        return True


    def print_status(self):
        self.log("--------------")
        self.log("Servo status:")
        for channel in range(NUM_CHANNELS_USED):
            if self.current_angles[channel] != 0:
                self.log(f"    Current angle[{channel}]: {self.current_angles[channel]}")
        self.log(f"  Total dispenses:")
        for channel in self.dispense_count:
            self.log(f"    Ch {channel} : {self.dispense_count[channel]}")
        self.log(f"  Uptime: {(time.time() - self.init_time):.0f} seconds")
        self.log("--------------")


    def dispense_food(self, dispenser_channel):
        if self.current_angles[dispenser_channel] == ANGLE_DISPENSE_1:
            self.queue_angle(dispenser_channel, ANGLE_DISPENSE_2)
        else:
            self.queue_angle(dispenser_channel, ANGLE_DISPENSE_1)
        
        # Track number of dispenses
        if dispenser_channel in self.dispense_count:
            self.dispense_count[dispenser_channel] += 1
        else:
            self.dispense_count[dispenser_channel] = 1

        self.log(f"Food dispensed for channel {dispenser_channel}")
    

    # Helper function to block main thread until all servos have emptied their queues
    def block_until_servos_done(self):
        while True:
            # Check/update servos
            self.run_loop()

            # Check for completion
            queues_empty = True
            for queue in self.channel_queue:
                if len(queue) > 0:
                    queues_empty = False
                    break
            
            if queues_empty:
                return
            
            # Check again after some time
            time.sleep(0.1)
        

    # Initial setup
    def init_servos(self):
        for channel_num in range(NUM_CHANNELS_USED):
            self.kit.servo[channel_num].actuation_range = 180
            self.kit.servo[channel_num].set_pulse_width_range(500, 2500)

            # Track per-servo angles
            self.current_angles.append(0)

            # Create queue for each servo
            self.channel_queue.append([])

        # For development only, to speed up program
        if SKIP_SERVO_WAIT:
            return
        
        # Start with door open (in case food falls as servos initialize)
        # Note that we do not use stepped commands here, because we may command too extreme of an angle initially
        # and a human is likely present to operate the machine.
        self.queue_angle(CHANNEL_DOOR_LEFT, ANGLE_DOOR_LEFT_OPEN)
        self.queue_angle(CHANNEL_DOOR_RIGHT, ANGLE_DOOR_RIGHT_OPEN)
        self.block_until_servos_done()

        # Initial prompt for whether the initialization sequence should be run
        init_cmd = input("\nInitializing servos. Does food need to be loaded into the dispenser? (Y/n): ")
        if init_cmd == "Y":
            # We need authority in both directions, so 90 degrees is neutral
            print("Setting angle to neutral (90 degrees)")
            self.queue_angle(CHANNEL_DISPENSER_LEFT, ANGLE_NEUTRAL)
            self.queue_angle(CHANNEL_DISPENSER_RIGHT, ANGLE_NEUTRAL)
            self.block_until_servos_done()

            # Wait for food to be loaded
            print("90 degrees achieved! Please pour food in")
            _ = input("\nHit enter to continue")

            # Load food into side 2 by moving paddles to side 1
            print("Loading side 2...")
            self.queue_angle(CHANNEL_DISPENSER_LEFT, ANGLE_DISPENSE_1)
            self.queue_angle(CHANNEL_DISPENSER_RIGHT, ANGLE_DISPENSE_1)
            self.block_until_servos_done()
            time.sleep(1.5)

        # Now turn to side 2 to load side 1 with food
        print("Loading side 1...")
        self.queue_angle(CHANNEL_DISPENSER_LEFT, ANGLE_DISPENSE_2)
        self.queue_angle(CHANNEL_DISPENSER_RIGHT, ANGLE_DISPENSE_2)
        self.block_until_servos_done()
        time.sleep(1.5)

        # Now give operator a chance to empty the tray back into the hopper
        _ = input("\nDispenser loaded. Please empty the food tray back into the hopper and hit Enter to continue.")

        # Close the door
        print("Closing the door in 5 seconds...")
        time.sleep(5.0)
        print("Closing the door...")
        self.queue_angle_stepped(CHANNEL_DOOR_LEFT, ANGLE_DOOR_LEFT_CLOSED)
        self.queue_angle_stepped(CHANNEL_DOOR_RIGHT, ANGLE_DOOR_RIGHT_CLOSED)
        self.block_until_servos_done()
