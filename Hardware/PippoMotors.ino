#define ENA 5
#define IN1 8
#define IN2 9

#define ENB 6
#define IN3 10
#define IN4 11

// Direction variables received from WiFi server
bool forward = false;
bool backward = false;
bool left = false;
bool right = false;

void setup() {
  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);

  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  // Stop motors initially
  stopBot();

  Serial.begin(115200);
}

void loop() {

  // ------------------------------------------------
  // RECEIVE DATA FROM WIFI SERVER HERE
  // ------------------------------------------------
  //
  // Example:
  // forward = 1;
  // backward = 0;
  // left = 0;
  // right = 0;
  //
  // Replace this section with your actual
  // WiFi-server communication code.
  // ------------------------------------------------


  // --------------------------------
  // MOTOR CONTROL
  // --------------------------------

  if (forward) {
    moveForward();
  }

  else if (backward) {
    moveBackward();
  }

  else if (left) {
    turnLeft();
  }

  else if (right) {
    turnRight();
  }

  else {
    stopBot();
  }
}


// ================================
// FORWARD
// ================================
void moveForward() {

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);

  analogWrite(ENA, 200);
  analogWrite(ENB, 200);
}


// ================================
// BACKWARD
// ================================
void moveBackward() {

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);

  analogWrite(ENA, 200);
  analogWrite(ENB, 200);
}


// ================================
// LEFT
// ================================
void turnLeft() {

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);

  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);

  analogWrite(ENA, 200);
  analogWrite(ENB, 200);
}


// ================================
// RIGHT
// ================================
void turnRight() {

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);

  analogWrite(ENA, 200);
  analogWrite(ENB, 200);
}


// ================================
// STOP
// ================================
void stopBot() {

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);

  analogWrite(ENA, 0);
  analogWrite(ENB, 0);
}