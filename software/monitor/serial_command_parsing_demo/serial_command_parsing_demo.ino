/*
  Supported opcodes (RX):
  - "R": Relay command

  Relay command:
  - Actual relay (efuse) state will be dependent upon serial command AND the efuse status
  - On boot, default relay state will be open

    R,<ch0 close 0/1>,<ch1 close 0/1>
    
  For example, to close ch0 and open ch1: "R,1,0"
*/

// Serial receive buffer
String buffer;

void setup() {
  // initialize serial:
  Serial.begin(115200);

  // Use a short timeout to make sure we don't hold up processing
  Serial.setTimeout(1);
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
              bool ch0Cmd = (buffer[2] == '1');
              bool ch1Cmd = (buffer[4] == '1');
              Serial.println("Commanding:" + String(ch0Cmd) + String(ch1Cmd));
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

void loop() {
  processSerialCommands();
}
