/*
  # Kibbie Current Sense Demo

  Outputs measurements in a comma-separated format:

    <opcode>,<timestamp>,<value1>,<value2>,...
  
  ## Supported opcodes (TX):
  - "I": Current measurement
  - "F": EFuse status (true = open/error, false = closed/OK)
  
  ### Current measurements (exponentially filtered):

    I,<timestamp>,<ch0 current (A)>,<ch1 current (A)>
  
  ### Efuse open status

    F,<timestamp>,<ch0 amp-seconds>,<ch0 open>,<ch1 amp-seconds>,<ch1 open>
  
  ## Supported opcodes (RX):
  - "R": Relay command

  ### Relay command:
  - Actual relay (efuse) state will be dependent upon serial command AND the efuse status
  - On boot, default relay state will be open

    R,<ch0 close 0/1>,<ch1 close 0/1>
    
  For example, to close ch0 and open ch1: "R,1,0"

*/

#include <limits.h>

// Set to true to turn on current debug message (raw sample, unfiltered voltage, unfiltered current)
const bool ENABLE_CURRENT_DEBUG = false;

// Set to true to turn on efuse debug message (current integral)
const bool ENABLE_EFUSE_DEBUG = false;

const float FILT_LEARNING_FACTOR = 0.95;       // Each new sample is 0.9*old + (1 - 0.9) * new

const float VOLTAGE_BIAS = 2.5; // V, 0-current DC offset of current sensors
const float CURRENT_GAIN_A_PER_V = 1.0 /*A*/ / 0.185 /*V*/; // From https://smile.amazon.com/dp/B00XT0PLXE

// Pin definitions for current sense
const int NUM_CURRENT_CHANNELS = 2;
uint8_t CURRENT_CHANNEL_PINS[] = {
  A0, // Left door
  A1  // Right door
};

// Pin definition for efuse relays
uint8_t EFUSE_CHANNEL_PINS[] = {
  2,  // Left door
  3   // Right door
};

// Efuse relay values
#define RELAY_ON LOW
#define RELAY_OFF HIGH

// Array to store per-channel filtered current
int rawValues[NUM_CURRENT_CHANNELS] = {0, 0};
float unfilteredVoltage[NUM_CURRENT_CHANNELS] = {0, 0};
float unfilteredCurrent[NUM_CURRENT_CHANNELS] = {0, 0};
float filteredCurrent[NUM_CURRENT_CHANNELS] = {0, 0};

// Periodic definitions
const int SERIAL_OUTPUT_PERIOD_MS = 100; // ms, period at which to report current measurements on serial (lower bound)
const int SAMPLE_INPUT_PERIOD_MS = 10;  // ms, period at which to run main loop (sample current)
unsigned long nextOutputTime = 0; // Next timestamp at which to report current measurement to serial
unsigned long nextLoopTime = 0; // Next timestamp at which to sample inputs

// Efuse
const int EFUSE_CALC_PERIOD_MS = 500;
unsigned long nextEfuseCalcTime = 0;  // ms timestamp to run next efuse calculation
const float EFUSE_AMP_SECONDS_THRESHOLD = 1.0 /*A*/ * 10 /*s*/;  // current*time threshold to blow efuse
                                                                // Set to 1A * 1s for testing
                                                                // Good value is probably 1.0A for 5s or 10s
const int NUM_SECONDS_TO_INTEGRATE = 20; // s
const int NUM_CURRENT_WINDOW_SAMPLES = NUM_SECONDS_TO_INTEGRATE /*s*/ * (1000 / EFUSE_CALC_PERIOD_MS) /*samples/second*/;  // Integral window
const float EFUSE_DT = (float)EFUSE_CALC_PERIOD_MS / 1000;
float filteredCurrentSumOverWindow[NUM_CURRENT_CHANNELS] = {0.0, 0.0};                // Raw sum of all samples in window
float filteredCurrentIntegralOverWindow[NUM_CURRENT_CHANNELS] = {0.0, 0.0};           // Multiply sum by dt to obtain integral
float filteredCurrentWindowSamples[NUM_CURRENT_CHANNELS][NUM_CURRENT_WINDOW_SAMPLES]; // Circular buffer of samples to update sum with
unsigned int nextFilteredCurrentWindowSamples[NUM_CURRENT_CHANNELS] = {0, 0};         // Next index in circular buffer to pop
bool efuseOpenStatus[NUM_CURRENT_CHANNELS] = {false, false};                          // true for blown, false for closed

// Array to store per-channel relay requests
// Final relay state is 
float relayRequestClosed[NUM_CURRENT_CHANNELS] = {false, false};

// Serial receive buffer
String buffer;

// DC offset due to relays consuming power
const float CURRENT_OFFSET_PER_RELAY_ON_AMPS = 0.03; // A, how much we need to add to the current value per relay that's on

// the setup routine runs once when you press reset:
void setup() {
  // Initialize current integral window to all 0s
  for (int channel = 0; channel < NUM_CURRENT_CHANNELS; channel++) {
    for (int i = 0; i < NUM_CURRENT_WINDOW_SAMPLES; i++) {
      filteredCurrentWindowSamples[channel][i] = 0.0;
    }
  }

  // Disable efuses by default
  for (int channel = 0; channel < NUM_CURRENT_CHANNELS; channel++) {
    uint8_t pin = EFUSE_CHANNEL_PINS[channel];
    pinMode(pin, OUTPUT);
    digitalWrite(pin, RELAY_OFF);
  }

  // initialize serial communication at 9600 bits per second:
  Serial.begin(115200);

  // Use a short timeout to make sure we don't hold up processing
  Serial.setTimeout(1);

  // Serial.println("Starting current measurements...");

  // Perform unit tests here
  if (!unitTestsPass()) {
    Serial.println("*** TEST FAILURE DETECTED! Holding the program captive... ***");
    while (1);
  }
}

// Helper function similar to an assertion that prints the message if `testPassed` is false
bool verifyTest(bool testPassed, String message) {
  if (!testPassed) {
    Serial.println("*** Test failed: " + message);
  }
  return testPassed;
}

bool unitTestsPass() {
  bool testsPassed = true;

  // Tests for `isTimeToUpdateEfuses(unsigned long nextCalculationTime, unsigned long currentTime)`
  testsPassed &= verifyTest(isTimeToUpdateEfuses(EFUSE_CALC_PERIOD_MS, 0)                         == false, "nominal 0");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(EFUSE_CALC_PERIOD_MS, EFUSE_CALC_PERIOD_MS - 1)  == false, "nominal -1");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(EFUSE_CALC_PERIOD_MS, EFUSE_CALC_PERIOD_MS)      == true,  "nominal ==");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(EFUSE_CALC_PERIOD_MS, EFUSE_CALC_PERIOD_MS + 1)  == true,  "nominal +1");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(EFUSE_CALC_PERIOD_MS, EFUSE_CALC_PERIOD_MS + 10) == true,  "nominal +10");

  // The following test the case where the clock is 1 cycle from rolling over
  unsigned long rolloverThreshold = ULONG_MAX - EFUSE_CALC_PERIOD_MS;
  unsigned long timerThreshold = rolloverThreshold + 10;
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, timerThreshold - EFUSE_CALC_PERIOD_MS + 1) == false, "1 cycle from rollover start");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, timerThreshold - 1)                        == false, "1 cycle from rollover -1");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, timerThreshold)                            == true,  "1 cycle from rollover ==");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, timerThreshold + 1)                        == true,  "1 cycle from rollover +1");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, timerThreshold + 10)                       == true,  "1 cycle from rollover +10");

  // The following test the case where the clock has rolled over (nominal)
  timerThreshold = EFUSE_CALC_PERIOD_MS - 100;
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, ULONG_MAX - 50)      == false, "rollover -150");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, timerThreshold - 1)  == false, "rollover -1");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, timerThreshold)      == true,  "rollover ==");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, timerThreshold + 1)  == true,  "rollover +1");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, timerThreshold + 10) == true,  "rollover +10");

  // The following test the case where the clock has rolled over (edge)
  timerThreshold = EFUSE_CALC_PERIOD_MS - 1;
  testsPassed &= verifyTest((ULONG_MAX + 1) == 0, "verify rollover");
  testsPassed &= verifyTest((ULONG_MAX + EFUSE_CALC_PERIOD_MS) == (EFUSE_CALC_PERIOD_MS - 1), "verify rollover limit");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, ULONG_MAX)           == false, "rollover start");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, timerThreshold - 1)  == false, "rollover -1");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, timerThreshold)      == true,  "rollover ==");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, timerThreshold + 1)  == true,  "rollover +1");
  testsPassed &= verifyTest(isTimeToUpdateEfuses(timerThreshold, timerThreshold + 10) == true,  "rollover +10");

  return testsPassed;
}

// Process incoming serial commands
void processSerialCommands() {
    while (Serial.available()) {
    char nextByte = Serial.read();

    if (nextByte == '\n') {
      // Process
      // Attempt to parse
      if (buffer.length() >= 1) {
        char opcode = buffer[0];
        switch (opcode) {
          case 'R':
            if ((buffer.length() == 5) && (buffer[1] == ',') && (buffer[3] == ',')) {
              relayRequestClosed[0] = (buffer[2] == '1');
              relayRequestClosed[1] = (buffer[4] == '1');
            } else {
              Serial.println("*** Invalid command for opcode R:" + buffer);
            }
            break;
          default:
            Serial.println("*** Unrecognized opcode:" + String(opcode) + " for cmd:\"" + buffer + "\"");
        }

        buffer = "";
      }
    } else {
      // Concatenate
      buffer += String(nextByte);
    }
  }
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

void updateEfuse(uint8_t channel) {
  // A hack to offset the current readings due to relays consuming power
  int num_relays_on = 0;
  for (int channel = 0; channel < NUM_CURRENT_CHANNELS; channel++) {
    if (!efuseOpenStatus[channel]) {
      num_relays_on++;
    }
  }
  // Serial.println("Num relays on:" + String(num_relays_on));

  // Integrate current and update sliding window
  for (int channel = 0; channel < NUM_CURRENT_CHANNELS; channel++) {
    // First pop the value to remove
    unsigned int sampleToRemoveIdx = nextFilteredCurrentWindowSamples[channel];
    float sampleToRemove = filteredCurrentWindowSamples[channel][sampleToRemoveIdx];

    // Replace it with the new sample
    float currentSample = abs(filteredCurrent[channel] + (CURRENT_OFFSET_PER_RELAY_ON_AMPS * num_relays_on));
    filteredCurrentWindowSamples[channel][sampleToRemoveIdx] = currentSample;

    // Compute new integral
    filteredCurrentSumOverWindow[channel] += currentSample - sampleToRemove;
    filteredCurrentIntegralOverWindow[channel] = filteredCurrentSumOverWindow[channel] * EFUSE_DT;

    // Check against limit
    if (filteredCurrentIntegralOverWindow[channel] > EFUSE_AMP_SECONDS_THRESHOLD) {
      // Blow the fuse and latch
      efuseOpenStatus[channel] = true;
    }

    // Increment index
    nextFilteredCurrentWindowSamples[channel] = ((nextFilteredCurrentWindowSamples[channel] + 1) % NUM_CURRENT_WINDOW_SAMPLES);
  }
}

void reportCurrentOnSerial(bool debug=false) {
  String output = "";

  String separator = ","; // Can also use a tab instead
  
  // Opcode (I for current measurement)
  output += "I" + separator;

  // Prepend csv output with timestamp for CSV output
  output += String(millis()) + separator;

  for (int channel = 0; channel < NUM_CURRENT_CHANNELS; channel++) {
    if (channel > 0) {
      output += separator;
    }

    if (debug) {
      output +=
        String(rawValues[channel]) + separator +          // Raw integer ADC values
        String(unfilteredVoltage[channel]) + separator +  // Unfiltered float voltage
        String(unfilteredCurrent[channel]) + separator;   // Unfiltered float current
    }

    output +=
      String(filteredCurrent[channel]);                   // Filtered float current
  }

  Serial.println(output);
}

void reportEfuseStatusOnSerial(bool debug=false) {
  String output = "";

  String separator = ","; // Can also use a tab instead
  
  // Opcode (F for Fuse status)
  output += "F" + separator;

  // Prepend csv output with timestamp for CSV output
  output += String(millis()) + separator;

  for (int channel = 0; channel < NUM_CURRENT_CHANNELS; channel++) {
    if (channel > 0) {
      output += separator;
    }

    if (debug) {
      output +=
        // String(nextFilteredCurrentWindowSamples[channel]) + separator +   // Next sample number
        String(filteredCurrentSumOverWindow[channel]) + separator;      // Sum of moving window

        // // Print out arrays
        // Serial.print("Ch " + String(channel) + ": ");
        // for (int i = 0; i < NUM_CURRENT_WINDOW_SAMPLES; i++) {
        //   Serial.print(String(filteredCurrentWindowSamples[channel][i]) + ",");
        // }
        // Serial.println();
    }

    output +=
      String(filteredCurrentIntegralOverWindow[channel]) + separator +    // Integral value (A*s)
      String(efuseOpenStatus[channel]);                                   // Efuse status (0 for OK, 1 for off)
  }

  Serial.println(output);
}

// Given the next schedule efuse calculation time and current time in ms, returns true if efuses should be updated
bool isTimeToUpdateEfuses(unsigned long nextCalculationTime, unsigned long currentTime) {
  return (currentTime >= nextCalculationTime) && (              // Current time is past the trigger time, AND
            (nextCalculationTime >= EFUSE_CALC_PERIOD_MS) ||    // Nominal case - timer has not rolled over
            (currentTime < (ULONG_MAX - EFUSE_CALC_PERIOD_MS))  // Special case - else if timer rolled over, we also require that currentTime has rolled over
         );
}

// the loop routine runs over and over again forever:
void loop() {
  // Check for any commands from kibbie via serial
  processSerialCommands();

  // Sample and filter current
  for (int channel = 0; channel < NUM_CURRENT_CHANNELS; channel++) {
    sampleAndFilter(channel);
  }

  // Periodically update efuse status
  // Additionally account for rollover of the clock
  unsigned long currentTime = millis();
  if (isTimeToUpdateEfuses(currentTime, millis())) {
    for (int channel = 0; channel < NUM_CURRENT_CHANNELS; channel++) {
      updateEfuse(channel);
    }
    nextEfuseCalcTime = currentTime + EFUSE_CALC_PERIOD_MS;
  }

  // Report filtered current and status on serial periodically
  currentTime = millis();
  if (currentTime >= nextOutputTime) {
    if (ENABLE_CURRENT_DEBUG) {
      reportCurrentOnSerial(true);
    } else if (ENABLE_EFUSE_DEBUG) {
      reportEfuseStatusOnSerial(true);
    } else {
      reportCurrentOnSerial();
      reportEfuseStatusOnSerial();
    }

    nextOutputTime = currentTime + SERIAL_OUTPUT_PERIOD_MS;
  }

  // Set relays
  for (int channel = 0; channel < NUM_CURRENT_CHANNELS; channel++) {
    if (efuseOpenStatus[channel] || !relayRequestClosed[channel]) {
      digitalWrite(EFUSE_CHANNEL_PINS[channel], RELAY_OFF);
    } else {
      digitalWrite(EFUSE_CHANNEL_PINS[channel], RELAY_ON);
    }
  }
}

// Observed 2.50V for 0A
// Observed around 2.68V for 1A?