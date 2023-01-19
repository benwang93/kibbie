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

        self.state = DispenserState.IDLE
        self.dispenses_per_day = dispenses_per_day

        # Initialize dispense time based on the most recent midnight (UTC time)
        current_time = time.time()
        start_of_day = current_time - (current_time % (3600 * 24))
        self.next_dispense_time = start_of_day + (SECONDS_PER_DAY / self.dispenses_per_day)
        self.log(f'Set to dispense at {time.asctime(time.localtime(self.next_dispense_time))} (Start of day was {time.asctime(time.localtime(start_of_day))})')

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
    

    # Function to call at each step to run the state machine
    # Returns door and dispenser commands
    def step(self, allowed_cat_detected, disallowed_cat_detected):
        current_time = time.time()

        if self.state == DispenserState.IDLE:
            # Transition to SEARCHING if it's time to dispense
            if current_time >= self.next_dispense_time:
                # On transition, schedule next dispense
                self.next_dispense_time = current_time + (SECONDS_PER_DAY / self.dispenses_per_day)

                # Set next state
                self.state = DispenserState.SEARCHING

                self.log("Transitioned IDLE->SEARCHING")

        elif self.state == DispenserState.SEARCHING:
            # Transition to opening on no cats detected
            if not allowed_cat_detected and not disallowed_cat_detected:
                # On transition, open door
                self.open_door_request = True
                self.door_open_completion_time = current_time + Servo.DELAY_CONSECUTiVE_SERVO_STEP_WAIT # Door uses the queue_angle_stepped() function

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
                self.dispense_completion_time = current_time + Servo.DELAY_CONSECUTiVE_SERVO_WAIT # Dispenser uses the queue_angle() function

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
