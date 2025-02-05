"""
Class to operate each dispenser on kibbie

Takes in per-cat state as input, runs the dispenser state machine logic, and commands dispensers as-needed

Dispenser state machine:

  init  ┌──────┐                      ┌───────────────┐
 ──────►│      │  on scheduled time   │               │
        │ Idle ├─────────────────────►│ Searching     │
   ┌───►│      │  Schedule next       │               │
   │    └──────┘  dispense            │ Wait for      │
   │                                  │ opportunity   │
   │                                  │               │
   │                                  └─────────┬─────┘
   │                                       ▲    │
   │                               on cat  │    │on no cats
   │                               detected│    │detected
   │                                       │    │
   │                                       │    ▼
   │  ┌──────────────────┐            ┌────┴──────────┐
   │  │                  │ on no cats │               │
   │  │ Dispensing       │ detected   │ Opening       │
   └──┤                  │◄───────────┤               │
      │ Command dispense │            │ Command door  │
      │ and close door   │            │ open          │
      │                  │            │               │
      └──────────────────┘            └───────────────┘

"""

from enum import Enum
import time

import lib.KibbieServoUtils as Servo
from lib.Persistence import Persistence

DEBUG_DISPENSER_STATE_MACHINE = False # Set to True to schedule first dispense at time of init

# class syntax
class DispenserState(Enum):
    IDLE = 1
    SEARCHING = 2
    OPENING = 3
    DISPENSING = 4

SECONDS_PER_DAY = 60 * 60 * 24 # s/min * min/hr * hr/day

class Dispenser:
    def __init__(self, dispenses_per_day, dispenser_name, logfile):
        # Logging
        self.name = dispenser_name
        self.logfile = logfile

        self.persistence = Persistence(f"dispenser-{self.name}")

        self.state = DispenserState.IDLE
        self.dispenses_per_day = dispenses_per_day

        # Initialize dispense time based on the most recent midnight (UTC time)
        current_time = time.time()

        if DEBUG_DISPENSER_STATE_MACHINE:
            # If debugging, force first dispense to be right now
            self.persistence.set("next_dispense_time", current_time)
        else:
            # Otherwise calculate next dispense time based on persisted time and current time
            prev_next_dispense_time = self.persistence.get("next_dispense_time")
            if prev_next_dispense_time is None:
                prev_next_dispense_time = current_time
            next_dispense_time = max(prev_next_dispense_time, current_time)
            self.persistence.set("next_dispense_time", next_dispense_time)
        
        self.log(f'Set to dispense at {time.asctime(time.localtime(self.persistence.get("next_dispense_time")))}')

        # State machine outputs (latching)
        self.open_door_request = False
        self.dispense_request = False

        # Track timers for servo events
        self.door_open_completion_time = 0
        self.dispense_completion_time = 0


    def log(self, s):
        output = f"[{time.asctime()}][Dispenser {self.name}] {s}"
        self.logfile.write(f"{output}\n")
        self.logfile.flush()
        print(output)


    def print_status(self):
        self.log("Dispenser status:")
        self.log(f"  State: {self.state}")
        self.log(f"  Dispenses per day: {self.dispenses_per_day}")
        self.log(f"  Next dispense: {time.asctime(time.localtime(self.persistence.get('next_dispense_time')))}")
        self.log("--------------")
    

    # Force dispenser state machine to dispense food NOW
    def schedule_dispense_now(self):
        self.persistence.set("next_dispense_time", time.time())
        self.log(f"*** Forced dispense scheduled for now! ({time.asctime(time.localtime((self.persistence.get('next_dispense_time'))))})")
    

    # Function to call at each step to run the state machine
    # Returns door and dispenser commands
    def step(self, allowed_cat_detected, disallowed_cat_detected):
        current_time = time.time()

        if self.state == DispenserState.IDLE:
            # Transition to SEARCHING if it's time to dispense
            if current_time >= self.persistence.get("next_dispense_time"):
                # On transition, schedule next dispense
                self.persistence.set("next_dispense_time", current_time + (SECONDS_PER_DAY / self.dispenses_per_day))

                # Set next state
                self.state = DispenserState.SEARCHING

                self.log("Transitioned IDLE->SEARCHING")

        elif self.state == DispenserState.SEARCHING:
            # Transition to opening on no cats detected
            if not allowed_cat_detected and not disallowed_cat_detected:
                # On transition, open door
                self.open_door_request = True
                self.door_open_completion_time = current_time + Servo.DELAY_CONSECUTIVE_SERVO_STEP_WAIT # Door uses the queue_angle_stepped() function
                self.log(f"Scheduled door open completion time for {time.asctime(time.localtime(self.door_open_completion_time))}")

                # Set next state
                self.state = DispenserState.OPENING

                self.log("Transitioned SEARCHING->OPENING")
        
        elif self.state == DispenserState.OPENING:
            # Transition back to SEARCHING if a cat is detected
            if allowed_cat_detected or disallowed_cat_detected:
                self.open_door_request = False
                self.state = DispenserState.SEARCHING

                self.log("Transitioned OPENING->SEARCHING")

            # Transition to DISPENSING once the door is open
            # Check servo state somehow (timer?)
            elif current_time >= self.door_open_completion_time:
                self.dispense_request = True
                self.dispense_completion_time = current_time + Servo.DELAY_CONSECUTIVE_SERVO_WAIT # Dispenser uses the queue_angle() function

                self.state = DispenserState.DISPENSING

                self.log("Transitioned OPENING->DISPENSING")

        elif self.state == DispenserState.DISPENSING:
            # Transition to IDLE once dispensing is complete
            if current_time >= self.dispense_completion_time:
                self.dispense_request = False
                self.open_door_request = False

                self.state = DispenserState.IDLE

                self.log("Transitioned DISPENSING->IDLE")
        
        return self.open_door_request, self.dispense_request
