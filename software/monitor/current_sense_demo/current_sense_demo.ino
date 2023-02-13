/*
  ReadAnalogVoltage

  Reads an analog input on pin 0, converts it to voltage, and prints the result to the Serial Monitor.
  Graphical representation is available using Serial Plotter (Tools > Serial Plotter menu).
  Attach the center pin of a potentiometer to pin A0, and the outside pins to +5V and ground.

  This example code is in the public domain.

  https://www.arduino.cc/en/Tutorial/BuiltInExamples/ReadAnalogVoltage
*/

float weighted_avg = 0.0;
const float WEIGHT = 0.9;       // Each new sample is 0.9*old + (1 - 0.9) * new

const float CURRENT_GAIN_A_PER_V = 1.0 /*A*/ / 0.185 /*V*/; // From https://smile.amazon.com/dp/B00XT0PLXE

// the setup routine runs once when you press reset:
void setup() {
  // initialize serial communication at 9600 bits per second:
  Serial.begin(9600);
}

// the loop routine runs over and over again forever:
void loop() {
  // read the input on analog pin 0:
  int sensorValue = analogRead(A1);
  // Convert the analog reading (which goes from 0 - 1023) to a voltage (0 - 5V):
  float voltage = sensorValue * (5.0 / 1023.0);
  float current = CURRENT_GAIN_A_PER_V * (voltage - 2.5);


  weighted_avg = WEIGHT * weighted_avg + (1.0 - WEIGHT) * current;

  // print out the value you read:
  // Serial.println(voltage);
  Serial.println(weighted_avg);
}

// Observed 2.50V for 0A
// Observed around 2.68V for 1A?