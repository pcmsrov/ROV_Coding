===== Notes =====
In Air
Accending 上升, Push, 7.3s
Deccending 下降, Pull, 7.5s 

===== Float Side Server =====
HTTP_GET
HTTP_POST

void setupWebServer() {
  // API端點
  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/up", HTTP_POST, handleMoveUp);
  server.on("/down", HTTP_POST, handleMoveDown);
  server.on("/stop", HTTP_POST, handleStop);
  server.on("/vertical_profile", HTTP_POST, handleVerticalProfile);  // 添加垂直剖面端點
  
  // 404處理
  server.onNotFound(handleNotFound);
  
  // 啟動服務器
  server.begin();
  Serial.println("HTTP服務器已啟動");
}


sendDefinedDataPacket

motorUp
    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, HIGH);

motorDown
    digitalWrite(MOTOR_IN1, HIGH);
    digitalWrite(MOTOR_IN2, LOW);



// 構建數據包
  String dataPacket = "{";
  dataPacket += "\"company_id\":\"" + String(COMPANY_ID) + "\",";
  dataPacket += "\"timestamp\":\"" + getUTCTime() + "\",";
  dataPacket += "\"depth\":" + String(currentDepth, 3) + ",";
  dataPacket += "\"unit\":\"m\",";
  dataPacket += "\"device_id\":\"" + deviceId + "\"";
  dataPacket += "}";


  getUTCTime