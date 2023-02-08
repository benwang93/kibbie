from adafruit_servokit import ServoKit
import time

kit = ServoKit(channels=16)

kit.servo[0].actuation_range = 180
kit.servo[0].set_pulse_width_range(500, 2500)

for i in range(4):
    angle = i%2 * 180
    kit.servo[0].angle = angle
    print(f"Set angle to {angle} deg")
    time.sleep(2)


# for i in range(180):
#     angle = i
#     kit.servo[0].angle = angle
#     print(f"Set angle to {angle} deg")
#     time.sleep(0.1)

print("Done!")