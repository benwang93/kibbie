"""
Kibbie Serial Library

Managees reading and writing operations of Kibbie, including:
- Reading current measurements from Arduino and decoding into per-channel current
- Publishing serial heartbeat message
- Publishing per-channel relay enable/disable messages

"""

import serial

class KibbieSerial:

    def __init__(self):
        # Define serial port
        self.ser = serial.Serial(
            port='/dev/ttyACM0',
            baudrate=9600,
            parity=serial.PARITY_ODD,
            stopbits=serial.STOPBITS_TWO,
            bytesize=serial.SEVENBITS
        )

        # Buffer to store received data in
        self.buffer_string = ""

        # Open port
        try: 
            if(self.ser.isOpen() == False):
                self.ser.open()
        except Exception as e:
            print("error open serial port: ", e)
            raise e
    
    def update(self):
        if self.ser.isOpen():
            # Read/process any buffered messages
            self.buffer_string += self.ser.read(self.ser.inWaiting()).decode()

            if '\n' in self.buffer_string:
                lines = self.buffer_string.split('\n') # Guaranteed to have at least 2 entries

                for i,line in enumerate(lines[:-1]):
                    # Process each line
                    print(i, ": ", line)
                
                # Remove processed lines
                self.buffer_string = lines[-1]

            # Write any buffered messages
