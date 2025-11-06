#include <Arduino.h>
#include <DHT20.h>
#include <Wire.h>
#include <PWFusion_MAX31856.h>
#include <SPI.h>

// Declare DHT20 (rH/temp) sensor object
DHT20 dht;

// Declare thermocouple object (assuming 2 TC probes)
const int NUM_PROBES = 2;
MAX31856 tcs[NUM_PROBES];
float temps[NUM_PROBES];
uint8_t fault_bytes[NUM_PROBES];

// Status Flags for TC (stored as 8 bit binary number, 1 = faulted)
const char* fault_names[] = {
	"Open Circuit",   // bit 0
	"TC Voltage OOR", // bit 1
	"TC Temp Low",    // bit 2
	"TC Temp High",   // bit 3
	"CJ Temp Low",    // bit 4
	"CJ Temp High",   // bit 5
	"TC Temp OOR",    // bit 6
	"CJ Temp OOR",    // bit 7
};


// Declare pin numbers
const int door_pin = 2;
const int leak_pin = 3;
const int cs_pins[NUM_PROBES] {4,5}; // CS pins for TCs

void setup() {

  Serial.begin(115200);
  Wire.begin();
  dht.begin();

  pinMode(door_pin, INPUT_PULLUP);
  pinMode(leak_pin, INPUT_PULLUP);
  
  for (int i=0; i<NUM_PROBES; i++) {
    tcs[i].begin(cs_pins[i]);
    tcs[i].config(TYPE_T, CUTOFF_60HZ, AVG_SEL_4SAMP, CMODE_AUTO);
  }

  Serial.setTimeout(10);
}

void loop() {
  delay(2000);
  dht.read();
  float ambient_temperature = dht.getTemperature();
  float humidity = dht.getHumidity();
  bool dhtstatus = dht.isConnected();

  for (int i=0; i<NUM_PROBES; i++) {
    tcs[i].sample();
    temps[i] = tcs[i].getTemperature();
    fault_bytes[i] = tcs[i].getStatus();
  }

  int door_state = digitalRead(door_pin); // 1 = closed
  int leak_state = digitalRead(leak_pin); // 1 = leaking
  

  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input == "GetAmbTemp") {
      Serial.println(ambient_temperature);
    }
    if (input == "GetrH") {
      Serial.println(humidity);
    }
    if (input == "GetLeak") {
      Serial.println(leak_state);
    }
    if (input == "GetDoor") {
      Serial.println(door_state);
    }
    if (input == "GetTC1Temp") {
      Serial.println(temps[0]);
    }
    if (input == "GetTC2Temp") {
      Serial.println(temps[1]);
    }
    if (input == "GetTC1Status") {
      if (fault_bytes[0] == 0){
        Serial.println("Good");
      }
      else {
        Serial.print("Faulted,");
        for (int i = 0; i < 8; i++) {
          if (fault_bytes[0] & (1 << i)) {
            Serial.print(fault_names[i]);
            Serial.print(",");
          }
        }
        Serial.println();
      }
    }

    if (input == "GetTC2Status") {
      if (fault_bytes[1] == 0){
        Serial.println("Good");
      }
      else {
        Serial.print("Faulted,");
        for (int i = 0; i < 8; i++) {
          if (fault_bytes[1] & (1 << i)) {
            Serial.print(fault_names[i]);
            Serial.print(",");
          }
        }
        Serial.println();
      }
    }
    
    if (input == "GetDHTStatus") {
      Serial.println(dhtstatus);
    }

    if (input == "RestartDHT") {
      dht.begin();
      dht.read();
      Serial.println(dht.isConnected());
    }

  }
      
}
