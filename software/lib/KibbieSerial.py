"""
Kibbie Serial Library

Managees reading and writing operations of Kibbie, including:
- Reading current measurements from Arduino and decoding into per-channel current
- Publishing serial heartbeat message
- Publishing per-channel relay enable/disable messages

"""

import serial
from .Parameters import *

class KibbieSerial:
    # Separator used between tokens in a message
    SEPARATOR = ","

    def __init__(self):
        # Define serial port
        self.ser = serial.Serial(
            port='/dev/ttyACM0',
            baudrate=115200,
            parity=serial.PARITY_ODD,
            stopbits=serial.STOPBITS_TWO,
            bytesize=serial.SEVENBITS
        )

        # Buffer to store received data in
        self.buffer_string = ""

        # Store most recent current sample
        self.channel_current = []

        # Open port
        try: 
            if(self.ser.isOpen() == False):
                self.ser.open()
        except Exception as e:
            print("error open serial port: ", e)
            raise e
    

    # Getter to retrieve the last receieved current
    # from Kibbie monitor. Returns current in amps
    def channel_current(self, channel):
        if channel < len(self.channel_current):
            return self.channel_current[channel]
        else:
            return 0
    
    def set_current(self, channel, current):
        if channel < len(self.channel_current):
            self.channel_current[channel] = current
        elif channel == len(self.channel_current):
            self.channel_current.append(current)
        else:
            raise Exception(f"Current channel {channel} out of bounds!")
    
    # Helper method to process a single line of serial
    def process_line(self, line):
        # Remove trailing characters
        line = line.strip("\r")

        # Tokenize string for processing
        tokens = line.split(KibbieSerial.SEPARATOR)
        opcode = tokens[0]

        try:
            if opcode == "I":
                # Current measurement
                for i,sample in enumerate(tokens[2:]):
                    self.set_current(i, float(sample))
                
                if DEBUG_SERIAL_PRINT:
                    print(f"Updated current: {self.channel_current}")
            else:
                if DEBUG_SERIAL_PRINT:
                    print(f'Unrecognized token for "{line}"')
        except Exception as e:
            print(f"*** Error decoding serial: {e}")

    # Periodic function to perform receive and send operations
    # Call this from main run loop
    def update(self):
        if self.ser.isOpen():
            # Read/process any buffered messages
            try:
                self.buffer_string += self.ser.read(self.ser.inWaiting()).decode()

                if '\n' in self.buffer_string:
                    lines = self.buffer_string.split('\n') # Guaranteed to have at least 2 entries

                    for i,line in enumerate(lines[:-1]):
                        # Process each line
                        # print(i, ": ", line)
                        self.process_line(line)        
                    
                    # Remove processed lines
                    self.buffer_string = lines[-1]
            except Exception as e:
                print(f"*** Failed to decode serial: {e}")

            # Write any buffered messages
