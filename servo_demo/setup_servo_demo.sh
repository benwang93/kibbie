# Install libraries
. ../venv/bin/activate
sudo pip install RPi.GPIO
sudo apt-get install python-smbus

# Download demo code and unzip
sudo apt-get install p7zip-full
wget https://www.waveshare.com/wiki/File:Servo_Driver_HAT.7z
7zr x Servo_Driver_HAT.7z -r -o./Servo_Driver_HAT
sudo chmod 777 -R Servo_Driver_HAT
cd Servo_Driver_HAT/Raspberry\ Pi/

# #For python3
# cd ~/Servo_Driver_HAT/Raspberry\ Pi/
# cd python3/
# sudo python3 PCA9685.py

## Expected result:Connect a servo to Channel 0, the servo will rotate.。
