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
        self.ser = serial.Serial(
            port='/dev/ttyACM0',
            baudrate=9600,
            parity=serial.PARITY_ODD,
            stopbits=serial.STOPBITS_TWO,
            bytesize=serial.SEVENBITS
        )

        try: 
            if(self.ser.isOpen() == False):
                self.ser.open()
        except Exception as e:
            print("error open serial port: ", e)
            raise e
    
    def update(self):
        if self.ser.isOpen():
            # Read/process any buffered messages
            # while 1:
            line = self.ser.readline()   # read a '\n' terminated line
            print(line)

            # Write any buffered messages
