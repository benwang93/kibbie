/*
 * Kibbie watchdog monitor
 * 
 * The Arduino watchdog monitor performs the following tasks:
 *  - Monitors current to each door of Kibbie (door and latch servos combined)
 *  - Reports overcurrent conditions to the Raspberry Pi once timing threshold exceeded
 *  - Monitors digital heartbeat signal from Raspberry Pi that should be toggled while the Kibbie program is running
 *  - If timeout is exceeded, reboot the Raspberry pi via a relay control
 */

// Calibration
const unsigned long OVERCURRENT_THRESHOLD_MS = 5000; // Number of milliseconds of overcurrent allowed before setting the overcurrent output pin high

// Current sense pins
int currentSenseLeftPin = A0;
int currentSenseRightPin = A1;
int overcurrentLeftPin = D4;
int overcurrentRightPin = D5;

// Heartbeat pins
int heartbeatPin = D2;
int mainPowerRelayPin = D3

// Current sense variables
int currentSenseLeftValue = 0;    // variable to store the value coming from the sensor
int currentSenseRightValue = 0;   // variable to store the value coming from the sensor

bool overcurrentActiveLeft = false;   // true if currently overcurrent
bool overcurrentActiveRight = false;  // true if currently overcurrent

unsigned long overcurrentStartTimeLeft = 0;    // milliseconds when the overcurrent condition started
unsigned long overcurrentStartTimeRight = 0;   // milliseconds when the overcurrent condition started


void setup() {
  pinMode(heartbeatPin, INPUT);
  pinMode(mainPowerRelayPin, OUTPUT);
  pinMode(overcurrentLeftPin, OUTPUT);
  pinMode(overcurrentRightPin, OUTPUT);

  // Set initial output state
  digitalWrite(overcurrentLeftPin, LOW);
  digitalWrite(overcurrentRightPin, LOW);
}

void loop() {
  // Read current sensor values
  currentSenseLeftValue = analogRead(currentSenseLeftPin);
  currentSenseRightValue = analogRead(currentSenseRightPin);

  // Track if overcurrent occurs
  // TODO: Do we need a filter? Not sure how noisy this signal will be
  if (currentSenseLeftValue > overcurrentThreshold) {
    // Check for edge
    if (overcurrentActiveLeft) {
      // Check for us exceeding overcurrent time
      if ((millis() - overcurrentStartTimeLeft) > OVERCURRENT_THRESHOLD_MS) {
        print("*** Overcurrent detected on left door for xxx ms");
        digitalWrite(overcurrentLeftPin, HIGH);
      }
    } else {
      // Start of overcurrent. Save overcurrent start time
      overcurrentStartTimeLeft = millis();
      overcurrentActiveLeft = true;
    }
  } else {
    // Clear overcurrent condition
    overcurrentActiveLeft = false;
    digitalWrite(overcurrentLeftPin, LOW);
  }

  // Read heartbeat value
  int heartbeatValue = digitalRead(heartbeatPin);


  // turn the ledPin on
  digitalWrite(ledPin, HIGH);
  // stop the program for <sensorValue> milliseconds:
  delay(sensorValue);

  // turn the ledPin off:
  digitalWrite(ledPin, LOW);
  // stop the program for for <sensorValue> milliseconds:
  delay(sensorValue);
}
