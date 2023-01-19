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

# class syntax
class DispenserState(Enum):
    IDLE = 1
    SEARCHING = 2
    OPENING = 3
    DISPENSING = 4

SECONDS_PER_DAY = 60 * 60 * 24 # s/min * min/hr * hr/day

class dispenser:
    def __init__(self, dispenses_per_day):
        self.state = DispenserState.IDLE
        self.dispenses_per_day = dispenses_per_day

        # Initialize dispense time based on the most recent midnight
        self.next_dispense_time = XXX + (SECONDS_PER_DAY / self.dispenses_per_day)

        # State machine outputs (latching)
        self.open_door_request = False
        self.dispense_request = False
    
    # Function to call at each step to run the state machine
    # Returns door and dispenser commands
    def step(self, allowed_cat_detected, disallowed_cat_detected):
        if self.state == DispenserState.IDLE:
            # Transition to SEARCHING if it's time to dispense
            current_time = time.time()
            if current_time >= self.next_dispense_time:
                # On transition, schedule next dispense
                self.next_dispense_time = current_time + (SECONDS_PER_DAY / self.dispenses_per_day)

                # Set next state
                self.state = DispenserState.SEARCHING

        elif self.state == DispenserState.SEARCHING:
            # Transition to opening on no cats detected
            if not allowed_cat_detected and not disallowed_cat_detected:
                # On transition, open door
                self.open_door_request = True

                # Set next state
                self.state = DispenserState.OPENING
        
        elif self.state == DispenserState.OPENING:
            # Transition back to SEARCHING if a cat is detected
            if allowed_cat_detected or disallowed_cat_detected:
                self.open_door_request = False
                self.state = DispenserState.SEARCHING

            # Transition to DISPENSING once the door is open
            # Check servo state somehow (timer?)
            elif door_is_open:
                self.dispense_request = True
                self.state = DispenserState.DISPENSING

        elif self.state == DispenserState.DISPENSING:
            # Transition to IDLE once dispensing is complete
            if dispense_complete:
                self.dispense_request = False
                self.open_door_request = False

                self.state = DispenserState.IDLE
        
        return self.open_door_request, self.dispense_request
