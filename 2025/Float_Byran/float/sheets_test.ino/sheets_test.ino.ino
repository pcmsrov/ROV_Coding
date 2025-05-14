#include <Arduino.h>
#include <WiFi.h>
#include "time.h"
#include <list>
#include <ESP_Google_Sheet_Client.h>

// For SD/SD_MMC mounting helper
#include <GS_SDHelper.h>

#define WIFI_SSID "pcmsrov"
#define WIFI_PASSWORD "12345678"

using namespace std; 
list<int> timeList; 
list<float> depthlist;

// Google Project ID
#define PROJECT_ID "float-info"

// Service Account's client email
#define CLIENT_EMAIL "floattransmitter@float-info.iam.gserviceaccount.com"

// Service Account's private key
const char PRIVATE_KEY[] PROGMEM = "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC642yaOO24f20Z\nkyQby2UOoNV3AsbVEjuPVDdLw/VRS3GpWtTcp4+SWWuPALIdNUaW8UCQESDiLnyL\n6E8M0Dm/nQyDyYgix8mJ8sG3CeatkzNmVbEdCeLHqsX5hSQjtOyTJN3snl/+jmbx\nmiT9r6VwZfwED4k536XmlPTOd7mU/yjK9bAE5ntmbpKBHQj/WrHUpykZgTYZe8M0\n1SY+f6cRLyxB9KJyB4UZCRsdmGvbABUbFmf+PK1tVN9QhweZK488Nt6nQHXVlp12\nlIiGKBp5QCW/F91LCVXxIx5uDCA/Jib0fAVxvAY1s8HvBgquVF0AtBfNXgZiN/qC\n6do+s9BfAgMBAAECggEACCYJYrIPv2ci8SYGwYV9SwV9OTqwQ7MPUMEJxi5toFVL\nR+iTdmmB644lj+8mVPqxMLylJYLxrZr8SDdhVvwvQGkPFiHv4yBV68NfaeUvHytX\nZuNenRcEwdLy3d3NxRbK5+GIIZyIL/eyil8/tKX3by6rLdwljhXvzF17TRNQTqw8\nO0EZVsM5H6OdOOiwBwF/yg/OjY5ISfy9n8Uq4ri/7003LcXgoiyFlEjg1qYdkW9e\nADf5mbxd77xFjqPs7nDc5NrLf9ZZ8QqbNCTkNAfmpQTIRFyOxoSZGMxCGI0+yZkG\nQUPku5h4XmRuoN3TFUveV9rBI8PXLvU67lWkq+woxQKBgQD2rSX26TM8jqq2vSZs\ng8Y3NxB2yfC1JEHqZOyvdHD2mbNrgxpqiMOSOdu2yIJIvekshzNIHLI7po4pB8rq\nWKcYw3YLBh8SsQmlSGZONl4VSrs4rUjk+tKMIJgnWeq5mKE+tG/FJgH0hTtrWffk\nnWqMGXtRTVbIbjrL5IvH7jhUywKBgQDB88PBLwBB2zzcTQrRudeCfnKr6uGj6w4S\npAc5S+d67s1evISf60/i2kxsZJbm0NrvPo5YTZZ6jAg4VIRtq4FAm/1P7Ao/levG\n+UUWK2gg9iEwKJ/g9/r6Pyc3sG6vi4ZmDTzaby+RaRXsTZzHUKj8bGMEXAPujPg4\nSdVytL9UPQKBgQCjuhtHvlMmr575uaRGRFSNE3xXDAQ7hvxFQoWik0vjMfNXueYP\nrgT5CnQd5woqk/qvdnGAPKPEWfFjpGt3ji4ijqHMAV0gf+diECLvaMCbq0WHAeUv\nLpgPMBctj03vsDHeN88z8N09Wi0tPML/t8gfg05JkWa3lApsiJ6KrkAvbwKBgE0w\nGD3v2Khc+jGqr52b2nrim/xzc+1qhKVChmV1IeC43R7Q4+9JFPfxbOzOc4fUou0H\n9lqKNlL7G+JfMHz8/mmaKwv9om5/2d/MIIScLcrAaaDi6g38YvPo4lC1dLeETa6b\nohZEnae/LKxojvZ70WT0NcvsWtw7WiX8rGgEKwj5AoGBAKH1RwEOEOCH+NryGzbK\n7pk5tJP30usAt4BFNGbhPPYIruNZl0O1mYtNH5oT7srPC54XOpDkXlAq6gOHPXiJ\nsnGJSdNw2InLZCOp4OWSgM1PVdkRwgJ0kA4tygyx/a4b4/m5CbfYIh7AptUIUZsd\nNpxeGT1dwYvH7wyJFhYNabyA\n-----END PRIVATE KEY-----\n";

// The ID of the spreadsheet where you'll publish the data
const char spreadsheetId[] = "1l9fQ2_P42tdo-NMY-iV2iqaUs8bRqyZpD1TH2Bab2fw";

// Timer variables
unsigned long lastTime = 0;  
unsigned long timerDelay = 10000;

// Token Callback function
void tokenStatusCallback(TokenInfo info);

// BME280 I2C
// Variables to hold sensor readings
char temp[] = "hi";

// NTP server to request epoch time
const char* ntpServer = "pool.ntp.org";

// Variable to save current epoch time
int epochTime; 

// Function that gets current epoch time
unsigned long getTime() {
  time_t now;
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    //Serial.println("Failed to obtain time");
    return(0);
  }
  time(&now);
  return now;
}

void setup() {

    Serial.begin(115200);
    Serial.println();
    Serial.println();

    //Configure time
    configTime(0, 0, ntpServer);

    // Initialize BME280 sensor 

    GSheet.printf("ESP Google Sheet Client v%s\n\n", ESP_GOOGLE_SHEET_CLIENT_VERSION);

    // Connect to Wi-Fi
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
    Serial.print("Connecting to Wi-Fi");
    while (WiFi.status() != WL_CONNECTED) {
      Serial.print(".");
      delay(1000);
    }
    Serial.println();
    Serial.print("Connected with IP: ");
    Serial.println(WiFi.localIP());
    Serial.println();

    // Set the callback for Google API access token generation status (for debug only)
    GSheet.setTokenCallback(tokenStatusCallback);

    // Set the seconds to refresh the auth token before expire (60 to 3540, default is 300 seconds)
    GSheet.setPrerefreshSeconds(3540);

    // Begin the access token generation for Google API authentication
    GSheet.begin(CLIENT_EMAIL, PROJECT_ID, PRIVATE_KEY);
    epochTime = getTime();
}

void loop(){
    // Call ready() repeatedly in loop for authentication checking and processing
    bool ready = GSheet.ready();
    Serial.println(ready);
    if (ready && millis() - lastTime > timerDelay){
      lastTime = millis();
      if (WiFi.status() == WL_CONNECTED) {
        for (int i = 0; i < timeList.size(); i++) {
          FirebaseJson response;

          Serial.println("\nAppend spreadsheet values...");
          Serial.println("----------------------------");

          FirebaseJson valueRange;

          valueRange.add("majorDimension", "COLUMNS");
          valueRange.set("values/[0]/[0]", *next(timeList.begin(), i));
          valueRange.set("values/[1]/[0]", "1.0");

          bool success = GSheet.values.append(&response, spreadsheetId, "Sheet1!A1", &valueRange);
          if (success){
              response.toString(Serial, true);
              valueRange.clear();
          }
          else{
              Serial.println(GSheet.errorReason());
          }
          Serial.println();
          Serial.println(ESP.getFreeHeap());
        }

        FirebaseJson response;

        Serial.println("\nAppend spreadsheet values...");
        Serial.println("----------------------------");

        FirebaseJson valueRange;

        valueRange.add("majorDimension", "COLUMNS");
        valueRange.set("values/[0]/[0]", epochTime + (lastTime / 1000));
        valueRange.set("values/[1]/[0]", "1.0");

        bool success = GSheet.values.append(&response, spreadsheetId, "Sheet1!A1", &valueRange);
        if (success){
            response.toString(Serial, true);
            valueRange.clear();
        }
        else{
            Serial.println(GSheet.errorReason());
        }
        Serial.println();
        Serial.println(ESP.getFreeHeap());

        timeList.clear();
      }
      else {
        timeList.push_back(epochTime + (lastTime / 1000));
      }
    }
    else if (!ready && millis() - lastTime > timerDelay) {
      timeList.push_back(epochTime + (lastTime / 1000));
    }
}

void tokenStatusCallback(TokenInfo info){
    if (info.status == token_status_error){
        GSheet.printf("Token info: type = %s, status = %s\n", GSheet.getTokenType(info).c_str(), GSheet.getTokenStatus(info).c_str());
        GSheet.printf("Token error: %s\n", GSheet.getTokenError(info).c_str());
    }
    else{
        GSheet.printf("Token info: type = %s, status = %s\n", GSheet.getTokenType(info).c_str(), GSheet.getTokenStatus(info).c_str());
    }
}