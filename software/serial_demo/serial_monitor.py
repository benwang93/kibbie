import serial

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

if ser.isOpen():
    while 1:
        line = ser.readline()   # read a '\n' terminated line
        print(line)
