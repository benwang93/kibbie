/*
  ReadAnalogVoltage

  Reads an analog input on pin 0, converts it to voltage, and prints the result to the Serial Monitor.
  Graphical representation is available using Serial Plotter (Tools > Serial Plotter menu).
  Attach the center pin of a potentiometer to pin A0, and the outside pins to +5V and ground.

  This example code is in the public domain.

  https://www.arduino.cc/en/Tutorial/BuiltInExamples/ReadAnalogVoltage
*/

const float FILT_LEARNING_FACTOR = 0.95;       // Each new sample is 0.9*old + (1 - 0.9) * new

const float CURRENT_GAIN_A_PER_V = 1.0 /*A*/ / 0.185 /*V*/; // From https://smile.amazon.com/dp/B00XT0PLXE

// Pin definitions for current sense
const int NUM_CURRENT_CHANNELS = 2;
uint8_t CURRENT_CHANNEL_PINS[] = {
  A0, // Left door
  A1  // Right door
};

// Array to store per-channel filtered current
float filteredCurrent[] = {0, 0};

const int CYCLES_TO_REPORT_CURRENT = 100;
int cyclesLeftBeforeReportingCurrent = 0;

// the setup routine runs once when you press reset:
void setup() {
  // initialize serial communication at 9600 bits per second:
  Serial.begin(9600);
}

void sampleAndFilter(uint8_t channel) {
  uint8_t pin = CURRENT_CHANNEL_PINS[channel];

  // read the input on analog pin 0:
  int sensorValue = analogRead(pin);

  // Convert the analog reading (which goes from 0 - 1023) to a voltage (0 - 5V):
  float voltage = sensorValue * (5.0 / 1023.0);
  float current = CURRENT_GAIN_A_PER_V * (voltage - 2.5);

  // Apply filter
  filteredCurrent[pin] = FILT_LEARNING_FACTOR * filteredCurrent[pin] + (1.0 - FILT_LEARNING_FACTOR) * current;

  // Serial.println("Ch " + String(channel) + ": " + String(filteredCurrent[pin]));
}

void reportCurrentOnSerial() {
  String output = "";

  for (int channel = 0; channel < NUM_CURRENT_CHANNELS; channel++) {
    if (channel > 0) {
      output += "\t";
    }
    output += filteredCurrent[CURRENT_CHANNEL_PINS[channel]];
  }

  Serial.println(output);
}

// the loop routine runs over and over again forever:
void loop() {
  for (int channel = 0; channel < NUM_CURRENT_CHANNELS; channel++) {
    sampleAndFilter(channel);
  }

  // Report every 1 in 50 samples
  // Serial.println("Cycles before reporting current: " + String(cyclesLeftBeforeReportingCurrent));
  if (cyclesLeftBeforeReportingCurrent <= 0) {
    reportCurrentOnSerial();

    // Reset countdown
    cyclesLeftBeforeReportingCurrent = CYCLES_TO_REPORT_CURRENT;
  }
  cyclesLeftBeforeReportingCurrent--;
}

// Observed 2.50V for 0A
// Observed around 2.68V for 1A?