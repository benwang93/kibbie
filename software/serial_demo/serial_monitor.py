import serial
import time

ser = serial.Serial(
    port='/dev/ttyACM0',
    baudrate=9600,
    parity=serial.PARITY_ODD,
    stopbits=serial.STOPBITS_TWO,
    bytesize=serial.SEVENBITS
)

try: 
    if(ser.isOpen() == False):
        ser.open()
except Exception as e:
    print("error open serial port: ", e)
    exit()

buffer_string = ''

def update():
    global buffer_string

    buffer_string = buffer_string + ser.read(ser.inWaiting()).decode()

    print(f'buffer string: "{buffer_string}"')

    if '\n' in buffer_string:
        lines = buffer_string.split('\n') # Guaranteed to have at least 2 entries

        for i,line in enumerate(lines[:-1]):
            # Process each line
            print(i, ":\t ", line)
        
        # Remove processed lines
        buffer_string = lines[-1]

if ser.isOpen():
    while 1:
        update()

        # Wait some time for buffer to grow
        time.sleep(1.0)
 