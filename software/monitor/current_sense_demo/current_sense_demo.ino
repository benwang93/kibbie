/*
  ReadAnalogVoltage

  Reads an analog input on pin 0, converts it to voltage, and prints the result to the Serial Monitor.
  Graphical representation is available using Serial Plotter (Tools > Serial Plotter menu).
  Attach the center pin of a potentiometer to pin A0, and the outside pins to +5V and ground.

  This example code is in the public domain.

  https://www.arduino.cc/en/Tutorial/BuiltInExamples/ReadAnalogVoltage
*/

const float FILT_LEARNING_FACTOR = 0.95;       // Each new sample is 0.9*old + (1 - 0.9) * new

const float VOLTAGE_BIAS = 2.5; // V, 0-current DC offset of current sensors
const float CURRENT_GAIN_A_PER_V = 1.0 /*A*/ / 0.185 /*V*/; // From https://smile.amazon.com/dp/B00XT0PLXE

// Pin definitions for current sense
const int NUM_CURRENT_CHANNELS = 2;
uint8_t CURRENT_CHANNEL_PINS[] = {
  A0, // Left door
  A1  // Right door
};

// Array to store per-channel filtered current
int rawValues[] = {0, 0};
float unfilteredVoltage[] = {0, 0};
float unfilteredCurrent[] = {0, 0};
float filteredCurrent[] = {0, 0};

const int SERIAL_OUTPUT_PERIOD_MS = 100; // ms, period at which to report current measurements on serial (lower bound)
// const int SERIAL_OUTPUT_PERIOD_MS = 100; // ms, period at which to report current measurements on serial (lower bound)
unsigned long nextOutputTime = 0; // Next timestamp at which to report current measurement to serial

// the setup routine runs once when you press reset:
void setup() {
  // initialize serial communication at 9600 bits per second:
  Serial.begin(9600);

  Serial.println("Starting current measurements...");
}

void sampleAndFilter(uint8_t channel) {
  uint8_t pin = CURRENT_CHANNEL_PINS[channel];

  // read the input on analog pin 0:
  int sensorValue = analogRead(pin);

  // Convert the analog reading (which goes from 0 - 1023) to a voltage (0 - 5V):
  float voltage = sensorValue * (5.0 / 1023.0);
  float current = CURRENT_GAIN_A_PER_V * (voltage - VOLTAGE_BIAS);

  // Apply filter
  rawValues[channel] = sensorValue;
  unfilteredVoltage[channel] = voltage;
  unfilteredCurrent[channel] = current;
  filteredCurrent[channel] = FILT_LEARNING_FACTOR * filteredCurrent[channel] + (1.0 - FILT_LEARNING_FACTOR) * current;
}

void reportCurrentOnSerial() {
  String output = "";

  String separator = ","; // Can also use a tab instead
  
  // Prepend csv output with timestamp for CSV output
  output += String(millis()) + separator;

  for (int channel = 0; channel < NUM_CURRENT_CHANNELS; channel++) {
    if (channel > 0) {
      output += separator;
    }

    // output += String(filteredCurrent[CURRENT_CHANNEL_PINS[channel]]);
    output += String(rawValues[channel]) + separator +
              String(unfilteredVoltage[channel]) + separator +
              String(unfilteredCurrent[channel]) + separator +
              String(filteredCurrent[channel]);
  }

  Serial.println(output);
}

// the loop routine runs over and over again forever:
void loop() {
  for (int channel = 0; channel < NUM_CURRENT_CHANNELS; channel++) {
    sampleAndFilter(channel);
  }

  // Report filtered current on serial periodically
  unsigned long currentTime = millis();
  if (currentTime >= nextOutputTime) {
    reportCurrentOnSerial();

    nextOutputTime = currentTime + SERIAL_OUTPUT_PERIOD_MS;
  }
}

// Observed 2.50V for 0A
// Observed around 2.68V for 1A?