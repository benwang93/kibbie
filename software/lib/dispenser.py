"""
Class to operate each dispenser on kibbie

Takes in per-cat state as input, runs the dispenser state machine logic, and commands dispensers as-needed

Dispenser state machine:

  init  ┌──────┐                      ┌───────────────┐
 ──────►│      │  on scheduled time   │               │
        │ Idle ├─────────────────────►│ Searching     │
   ┌───►│      │                      │               │
   │    └──────┘                      │ Wait for      │
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

class dispenser:
    def __init__(self):
        return
    
    def step(self):
        return