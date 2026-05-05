// WebServer_v4.2_PIDProfiling_2points.ino
// Mission:
// 1) Move float to depth = 2.5m, then PID-hold for 30 seconds
// 2) Move float to depth = 0.4m, then PID-hold for 30 seconds
// 3) After both holds: mission completed (motor off)
//
// Notes:
// - This sketch reuses the existing WiFi/AP + WebServer + MS5837 depth logic
//   from WebServer_v4.2.ino.
// - Motor is controlled via IN1/IN2 direction pins (no analog PWM pin).
//   PID output is translated into a pulse duty cycle inside a fixed time window.
// - You may need PID gain tuning (Kp/Ki/Kd) for your specific setup.

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include "MS5837.h"

//---------- Maybe Change Here ----------
const char* ssid = "A_MosaFloat";
const char* password = "pcmsrov22";
//---------- Maybe Change Here ----------

String companyID = "NotSetYet";
bool DEBUG_MODE = true;

// Kept for compatibility with existing frontend (/init).
unsigned long descendTime = 7300;  // (ms) max time allowed to reach first setpoint (best effort)
unsigned long waitTime = 10000;     // (unused in this PID mission)
unsigned long ascendTime = 7300;   // (ms) max time allowed to reach second setpoint (best effort)
bool useTimer = false;             // if true, timeouts are enforced

float depthData = 0.0;
float depthOffset = 0.0;

// Buffer size: 5 minutes * 12 records/min = 60 points (same as original)
const int BUFFER_SIZE = 60;
String timeBuffer[BUFFER_SIZE];
float depthBuffer[BUFFER_SIZE];
int writeIndex = 0;
int readIndex = 0;
int dataCount = 0;
unsigned long lastRecordTime = 0;
const unsigned long RECORD_INTERVAL = 5000; // 5 seconds

String utcTime = "";
unsigned long utcStartMillis = 0;
bool isTimeInitialized = false;

// Initialize pressure sensor
MS5837 sensor;

// Motor control pins
const int IN1 = 25;
const int IN2 = 26;
const int TopLimitBtn = 5;   // descending safety limit (LOW active)
const int DownLimitBtn = 18;  // ascending safety limit (LOW active)

// ---------------- PID parameters (tune these) ----------------
// PID output range is clamped to [-PID_OUTPUT_MAX, PID_OUTPUT_MAX].
// Then it becomes duty-cycle in a time window.
const float PID_KP = 0.8f;
const float PID_KI = 0.02f;
const float PID_KD = 0.08f;

const float PID_OUTPUT_MAX = 1.0f;
const float PID_INTEGRAL_MAX = 5.0f; // anti-windup clamp (in meter-seconds)

const unsigned long PID_SAMPLE_MS = 80;   // how often we recompute PID
const unsigned long PID_WINDOW_MS = 250;  // pulse duty window
const float PID_MIN_OUTPUT_TO_RUN = 0.05f; // deadband to reduce hunting

// Mission parameters
const float TARGET_DEPTH_1 = 1.0f;
const float TARGET_DEPTH_2 = 0.4f;

const unsigned long HOLD_DURATION_MS_1 = 30000; // 30s
const unsigned long HOLD_DURATION_MS_2 = 30000; // 30s

const float REACH_TOLERANCE_M = 0.03f; // "close enough" to switch into hold
const unsigned long REACH_STABLE_MS = 700; // must stay in tolerance for this long

// ---------------- Mission state machine ----------------
enum MissionPhase {
  IDLE = 0,
  GO_TO_DEPTH_1,
  HOLD_DEPTH_1,
  GO_TO_DEPTH_2,
  HOLD_DEPTH_2,
  COMPLETED
};

MissionPhase missionPhase = IDLE;
unsigned long phaseStartTime = 0;
bool startProcess = false;
bool progress = false; // reuse naming from old sketch: true while mission is active
bool forceStop = false;
bool motorRunning = false;

// Emergency test flags (keep compatibility with frontend buttons)
bool testPull = false;
bool testPush = false;
bool testPullAll = false;
bool testPushAll = false;

// PID runtime
float pidIntegral = 0.0f;
float pidLastError = 0.0f;
bool pidHasLast = false;
unsigned long pidLastSampleMillis = 0;
float pidOutput = 0.0f; // cached last output for duty control
unsigned long pidWindowStartMillis = 0;

unsigned long toleranceStartMillis = 0;

String inputString = "";
WebServer server(80);

/**
 * Setup WiFi AP mode
 */
void setupWiFi() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);

  if (DEBUG_MODE) {
    Serial.print("接入点已创建, IP地址: ");
    Serial.println(WiFi.softAPIP());
  }
}

/**
 * Root page (simple data fetch UI; same idea as original)
 */
void handleRoot() {
  String html = "<html><head><title>Float Depth Server</title>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>";
  html += "body { font-family: Arial; text-align: center; margin: 0; padding: 20px; }";
  html += "h1 { color: #0066cc; }";
  html += ".btn { background-color: #4CAF50; border: none; color: white; padding: 15px 32px; ";
  html += "text-align: center; text-decoration: none; display: inline-block; font-size: 16px; ";
  html += "margin: 4px 2px; cursor: pointer; border-radius: 8px; }";
  html += "</style></head><body>";
  html += "<h1>Float Depth Server</h1>";
  html += "<div><button class='btn' onclick='getData()'>获取数据</button></div>";
  html += "<div id='data' style='margin-top: 20px;'></div>";
  html += "<script>";
  html += "function getData() {";
  html += "  fetch('/data')";
  html += "    .then(response => response.json())";
  html += "    .then(data => {";
  html += "      let html = '<h2>时间数据列表</h2><ul>';";
  html += "      data.forEach(time => { html += '<li>' + time + '</li>'; });";
  html += "      html += '</ul>'; document.getElementById('data').innerHTML = html;";
  html += "    });";
  html += "}";
  html += "</script></body></html>";
  server.send(200, "text/html", html);
}

/**
 * Return recorded time+depth data for frontend plotting
 */
void handleData() {
  if (!isTimeInitialized) {
    server.send(200, "application/json", "[]");
    return;
  }

  String response = "[";
  bool firstData = true;

  while (readIndex != writeIndex) {
    if (!firstData) response += ",";
    response += "\"";
    response += companyID + ", ";
    response += timeBuffer[readIndex] + " UTC, ";
    response += String(depthBuffer[readIndex], 2) + " meters";
    response += "\"";

    readIndex = (readIndex + 1) % BUFFER_SIZE;
    firstData = false;
  }
  response += "]";
  server.send(200, "application/json", response);

  if (DEBUG_MODE) {
    Serial.print("发送数据，当前读取位置: ");
    Serial.print(readIndex);
    Serial.print(", 写入位置: ");
    Serial.println(writeIndex);
  }
}

/**
 * /init: receive timing params used by old sketch; we keep for compatibility.
 */
void handleInit() {
  if (server.method() != HTTP_POST) {
    server.send(405, "text/plain", "Method Not Allowed");
    return;
  }

  String postBody = server.arg("plain");
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, postBody);
  if (error) {
    server.send(400, "text/plain", "Invalid JSON");
    return;
  }

  utcTime = doc["utc_time"].as<String>();
  descendTime = doc["descend_time"].as<unsigned long>();
  ascendTime = doc["ascend_time"].as<unsigned long>();
  waitTime = doc["wait_time"].as<unsigned long>();
  DEBUG_MODE = doc["debug_mode"].as<bool>();
  useTimer = doc["use_timer"].as<bool>();
  companyID = doc["company_id"].as<String>();

  int hours = utcTime.substring(0, 2).toInt();
  int minutes = utcTime.substring(3, 5).toInt();
  int seconds = utcTime.substring(6, 8).toInt();

  unsigned long totalSeconds = hours * 3600 + minutes * 60 + seconds;
  (void)totalSeconds;

  utcStartMillis = millis();
  isTimeInitialized = true;
  depthOffset = depthData; // set current depth as 0 reference

  if (DEBUG_MODE) {
    Serial.println("Received initial connection parameters:");
    Serial.print("Company ID: "); Serial.println(companyID);
    Serial.print("UTC Time: "); Serial.println(utcTime);
    Serial.print("Descend Time: "); Serial.println(descendTime);
    Serial.print("Ascend Time: "); Serial.println(ascendTime);
    Serial.print("Wait Time: "); Serial.println(waitTime);
    Serial.print("Debug Mode: "); Serial.println(DEBUG_MODE ? "Enabled" : "Disabled");
    Serial.print("Use Timer: "); Serial.println(useTimer ? "Enabled" : "Disabled");
  }

  server.send(200, "text/plain", "Initial connection successful");
}

/**
 * /motor/start: start the 2-point PID profiling mission once.
 */
void handleMotorControl() {
  if (server.method() != HTTP_POST) {
    server.send(405, "text/plain", "Method Not Allowed");
    return;
  }

  if (!progress) {
    startProcess = true;
    missionPhase = GO_TO_DEPTH_1;
    phaseStartTime = millis();
    progress = true;
    pidReset();
    toleranceStartMillis = 0;
    stopMotor(); // ensure clean start before PID takes over

    if (DEBUG_MODE) Serial.println("PID mission started: GO_TO_DEPTH_1");
    server.send(200, "text/plain", "PID mission started");
  } else {
    server.send(400, "text/plain", "Mission is already running");
  }
}

void handleTestPull() {
  if (server.method() == HTTP_POST) {
    testPull = true;
    server.send(200, "text/plain", "Test pull started");
  } else {
    server.send(405, "text/plain", "Method Not Allowed");
  }
}

void handleTestPush() {
  if (server.method() == HTTP_POST) {
    testPush = true;
    server.send(200, "text/plain", "Test push started");
  } else {
    server.send(405, "text/plain", "Method Not Allowed");
  }
}

void handleTestPullAll() {
  if (server.method() == HTTP_POST) {
    testPullAll = true;
    server.send(200, "text/plain", "Test pull all started");
  } else {
    server.send(405, "text/plain", "Method Not Allowed");
  }
}

void handleTestPushAll() {
  if (server.method() == HTTP_POST) {
    testPushAll = true;
    server.send(200, "text/plain", "Test push all started");
  } else {
    server.send(405, "text/plain", "Method Not Allowed");
  }
}

void handleForceStop() {
  if (server.method() != HTTP_POST) {
    server.send(405, "text/plain", "Method Not Allowed");
    return;
  }
  forceStop = true;
  server.send(200, "text/plain", "Force stop command received");
}

void handleNotFound() {
  server.send(404, "text/plain", "Not found");
}

/**
 * Motor helper functions
 */
void startMotorForward() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  motorRunning = true;
}

void startMotorReverse() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  motorRunning = true;
}

void stopMotor() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  motorRunning = false;
}

/**
 * PID reset between setpoint transitions
 */
void pidReset() {
  pidIntegral = 0.0f;
  pidLastError = 0.0f;
  pidHasLast = false;
  pidOutput = 0.0f;
  pidLastSampleMillis = 0;
  pidWindowStartMillis = millis();
}

/**
 * Compute PID output in [-PID_OUTPUT_MAX, PID_OUTPUT_MAX]
 */
float pidCompute(float setpoint, float measured) {
  float error = setpoint - measured;

  unsigned long now = millis();
  float dt = 0.0f;
  if (pidHasLast && pidLastSampleMillis > 0) {
    dt = (now - pidLastSampleMillis) / 1000.0f;
  }

  pidLastSampleMillis = now;
  if (!pidHasLast) {
    pidHasLast = true;
    pidLastError = error;
    return 0.0f; // no derivative on first sample
  }

  if (dt <= 0.0001f) dt = 0.0001f;

  // Integral with anti-windup clamp
  pidIntegral += error * dt;
  if (pidIntegral > PID_INTEGRAL_MAX) pidIntegral = PID_INTEGRAL_MAX;
  if (pidIntegral < -PID_INTEGRAL_MAX) pidIntegral = -PID_INTEGRAL_MAX;

  // Derivative on measurement error
  float derivative = (error - pidLastError) / dt;

  float out = (PID_KP * error) + (PID_KI * pidIntegral) + (PID_KD * derivative);

  // Clamp output
  if (out > PID_OUTPUT_MAX) out = PID_OUTPUT_MAX;
  if (out < -PID_OUTPUT_MAX) out = -PID_OUTPUT_MAX;

  // Simple anti-windup: if we're saturated, don't keep integrating aggressively
  // (keeps integral bounded even if tuning is off).
  if (out == PID_OUTPUT_MAX || out == -PID_OUTPUT_MAX) {
    // Reduce integral growth when saturated by scaling it back slightly.
    pidIntegral *= 0.98f;
  }

  pidLastError = error;
  return out;
}

/**
 * Apply PID output as a duty-cycle pulse inside a fixed window.
 * (Motor driver uses direction-only pins, so we approximate "power" via on/off pulses.)
 */
void pidControlToSetpoint(float setpoint) {
  unsigned long now = millis();

  if (pidWindowStartMillis == 0) pidWindowStartMillis = now;
  if (now - pidWindowStartMillis >= PID_WINDOW_MS) {
    pidWindowStartMillis = now;
  }

  // Update PID output periodically
  if (pidLastSampleMillis == 0 || (now - pidLastSampleMillis) >= PID_SAMPLE_MS) {
    pidOutput = pidCompute(setpoint, depthData);
  }

  float absOut = abs(pidOutput);
  if (absOut < PID_MIN_OUTPUT_TO_RUN) {
    stopMotor();
    return;
  }

  unsigned long windowElapsed = now - pidWindowStartMillis;
  unsigned long onTime = (unsigned long)(absOut * PID_WINDOW_MS);

  if (windowElapsed < onTime) {
    if (pidOutput > 0.0f) startMotorForward();
    else startMotorReverse();
  } else {
    stopMotor();
  }
}

/**
 * Get formatted current time string ("HH:MM:SS") as in the original sketch.
 */
String getTimeString() {
  if (!isTimeInitialized) return "00:00:00";

  unsigned long elapsedMillis = millis() - utcStartMillis;

  int hours = utcTime.substring(0, 2).toInt();
  int minutes = utcTime.substring(3, 5).toInt();
  int seconds = utcTime.substring(6, 8).toInt();

  unsigned long totalSeconds = hours * 3600 + minutes * 60 + seconds;
  totalSeconds += elapsedMillis / 1000;

  hours = (totalSeconds / 3600) % 24;
  minutes = (totalSeconds / 60) % 60;
  seconds = totalSeconds % 60;

  char timeStr[9];
  sprintf(timeStr, "%02d:%02d:%02d", hours, minutes, seconds);
  return String(timeStr);
}

/**
 * Setup
 */
void setup() {
  Serial.begin(115200);
  if (DEBUG_MODE) Serial.println("\nStarting PID Depth Server...");

  Wire.begin();
  while (!sensor.init()) {
    if (DEBUG_MODE) {
      Serial.println("Init failed!");
      Serial.println("Are SDA/SCL connected correctly?");
    }
    delay(5000);
  }
  sensor.setFluidDensity(997);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(TopLimitBtn, INPUT_PULLUP);
  pinMode(DownLimitBtn, INPUT_PULLUP);

  for (int i = 0; i < BUFFER_SIZE; i++) {
    timeBuffer[i] = "";
    depthBuffer[i] = 0.0f;
  }

  setupWiFi();

  server.on("/", HTTP_GET, handleRoot);
  server.on("/data", HTTP_GET, handleData);
  server.on("/init", HTTP_POST, handleInit);
  server.on("/motor/start", HTTP_POST, handleMotorControl);
  server.on("/motor/test/pull", HTTP_POST, handleTestPull);
  server.on("/motor/test/push", HTTP_POST, handleTestPush);
  server.on("/motor/test/pullall", HTTP_POST, handleTestPullAll);
  server.on("/motor/test/pushall", HTTP_POST, handleTestPushAll);
  server.on("/motor/force/stop", HTTP_POST, handleForceStop);
  server.onNotFound(handleNotFound);

  server.begin();
  if (DEBUG_MODE) Serial.println("HTTP服务器已启动");

  stopMotor();
  pidReset();
}

/**
 * Main loop
 */
void loop() {
  server.handleClient();

  // Update sensor reading first (used by PID).
  sensor.read();
  depthData = sensor.depth() - depthOffset;

  unsigned long currentTime = millis();

  // Emergency stop
  if (forceStop) {
    stopMotor();
    progress = false;
    startProcess = false;
    missionPhase = IDLE;
    forceStop = false;
    pidReset();
    toleranceStartMillis = 0;
    if (DEBUG_MODE) Serial.println("Force stop: mission aborted.");
    return;
  }

  // Motor test buttons (do not interfere with PID mission control).
  if (testPull) {
    startMotorForward();
    delay(100);
    stopMotor();
    testPull = false;
  }

  if (testPush) {
    startMotorReverse();
    delay(100);
    stopMotor();
    testPush = false;
  }

  if (testPullAll) {
    if (forceStop) {
      stopMotor();
      testPullAll = false;
      forceStop = false;
    } else {
      startMotorForward();
      if (digitalRead(TopLimitBtn) == LOW) {
        startMotorReverse();
        delay(250);
        stopMotor();
        testPullAll = false;
      }
    }
  }

  if (testPushAll) {
    if (forceStop) {
      stopMotor();
      testPushAll = false;
      forceStop = false;
    } else {
      startMotorReverse();
      if (digitalRead(DownLimitBtn) == LOW) {
        startMotorForward();
        delay(250);
        stopMotor();
        testPushAll = false;
      }
    }
  }

  // Start PID mission (triggered by /motor/start)
  if (startProcess) {
    startProcess = false; // handler already set missionPhase/progress
  }

  // Apply mission control
  if (progress) {
    if (DEBUG_MODE && millis() % 1000 < 60) {
      const char* phaseName = "";
      switch (missionPhase) {
        case GO_TO_DEPTH_1: phaseName = "GO_TO_DEPTH_1"; break;
        case HOLD_DEPTH_1: phaseName = "HOLD_DEPTH_1"; break;
        case GO_TO_DEPTH_2: phaseName = "GO_TO_DEPTH_2"; break;
        case HOLD_DEPTH_2: phaseName = "HOLD_DEPTH_2"; break;
        case COMPLETED: phaseName = "COMPLETED"; break;
        default: phaseName = "UNKNOWN"; break;
      }
      Serial.print("Mission phase: "); Serial.print(phaseName);
      Serial.print(", depth="); Serial.print(depthData, 2);
      Serial.print("m, motor="); Serial.println(motorRunning ? "ON" : "OFF");
    }

    float setpoint = TARGET_DEPTH_1;
    unsigned long holdDuration = HOLD_DURATION_MS_1;

    switch (missionPhase) {
      case GO_TO_DEPTH_1: setpoint = TARGET_DEPTH_1; holdDuration = HOLD_DURATION_MS_1; break;
      case HOLD_DEPTH_1: setpoint = TARGET_DEPTH_1; holdDuration = HOLD_DURATION_MS_1; break;
      case GO_TO_DEPTH_2: setpoint = TARGET_DEPTH_2; holdDuration = HOLD_DURATION_MS_2; break;
      case HOLD_DEPTH_2: setpoint = TARGET_DEPTH_2; holdDuration = HOLD_DURATION_MS_2; break;
      default: break;
    }

    // Safety limit checks (best-effort).
    // IMPORTANT: if limit is hit, we stop and skip PID output for this loop.
    bool safetyLimitHit = false;
    if ((missionPhase == GO_TO_DEPTH_1 || missionPhase == HOLD_DEPTH_1) && digitalRead(TopLimitBtn) == LOW) {
      safetyLimitHit = true;
    }
    if ((missionPhase == GO_TO_DEPTH_2 || missionPhase == HOLD_DEPTH_2) && digitalRead(DownLimitBtn) == LOW) {
      safetyLimitHit = true;
    }

    if (!safetyLimitHit) {
      // Always run PID to current setpoint during active phases.
      // This covers both "moving" and "holding" without duplicating code.
      pidControlToSetpoint(setpoint);
    } else {
      stopMotor();
    }

    unsigned long now = millis();

    // --- State transitions ---
    if (missionPhase == GO_TO_DEPTH_1) {
      // Timeout (optional)
      if (useTimer && (now - phaseStartTime >= descendTime) && descendTime > 0) {
        stopMotor();
        progress = false;
        missionPhase = COMPLETED;
        if (DEBUG_MODE) Serial.println("Timeout reaching depth 1.");
        return;
      }

      float err = abs(depthData - TARGET_DEPTH_1);
      if (err <= REACH_TOLERANCE_M) {
        if (toleranceStartMillis == 0) toleranceStartMillis = now;
        if (now - toleranceStartMillis >= REACH_STABLE_MS) {
          missionPhase = HOLD_DEPTH_1;
          phaseStartTime = now;
          toleranceStartMillis = 0;
          pidReset(); // reset PID to avoid integrator bias from approach
          if (DEBUG_MODE) Serial.println("Reached depth 1, entering HOLD.");
        }
      } else {
        toleranceStartMillis = 0;
      }
    }

    else if (missionPhase == HOLD_DEPTH_1) {
      if (now - phaseStartTime >= HOLD_DURATION_MS_1) {
        missionPhase = GO_TO_DEPTH_2;
        phaseStartTime = now;
        toleranceStartMillis = 0;
        pidReset();
        if (DEBUG_MODE) Serial.println("Hold depth 1 done, moving to depth 2.");
      }
    }

    else if (missionPhase == GO_TO_DEPTH_2) {
      if (useTimer && (now - phaseStartTime >= ascendTime) && ascendTime > 0) {
        stopMotor();
        progress = false;
        missionPhase = COMPLETED;
        if (DEBUG_MODE) Serial.println("Timeout reaching depth 2.");
        return;
      }

      float err = abs(depthData - TARGET_DEPTH_2);
      if (err <= REACH_TOLERANCE_M) {
        if (toleranceStartMillis == 0) toleranceStartMillis = now;
        if (now - toleranceStartMillis >= REACH_STABLE_MS) {
          missionPhase = HOLD_DEPTH_2;
          phaseStartTime = now;
          toleranceStartMillis = 0;
          pidReset();
          if (DEBUG_MODE) Serial.println("Reached depth 2, entering HOLD.");
        }
      } else {
        toleranceStartMillis = 0;
      }
    }

    else if (missionPhase == HOLD_DEPTH_2) {
      if (now - phaseStartTime >= HOLD_DURATION_MS_2) {
        stopMotor();
        progress = false;
        startProcess = false;
        missionPhase = COMPLETED;
        if (DEBUG_MODE) Serial.println("Mission completed (both holds done).");
        delay(3000);
      }
    }
  }

  // Record time+depth for frontend plotting
  if (isTimeInitialized && currentTime - lastRecordTime >= RECORD_INTERVAL) {
    String currentTimeStr = getTimeString();
    timeBuffer[writeIndex] = currentTimeStr;
    depthBuffer[writeIndex] = depthData;
    writeIndex = (writeIndex + 1) % BUFFER_SIZE;
    if (writeIndex == readIndex) {
      readIndex = (readIndex + 1) % BUFFER_SIZE;
    }
    lastRecordTime = currentTime;
    if (DEBUG_MODE) {
      Serial.print("Depth at record: ");
      Serial.print(depthData, 2);
      Serial.println(" meters");
    }
  }

  // Keep loop responsive for PID pulse window and web server.
  delay(20);
}

