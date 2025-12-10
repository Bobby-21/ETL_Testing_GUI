#include <Arduino.h>
// #include <DHT20.h>
#include <Wire.h>
#include <PWFusion_MAX31856.h>
#include <SPI.h>
#include <DHT.h>

// Declare DHT22 (rH/temp) sensor object
const int DHT22_PIN = 6;
DHT dht(DHT22_PIN, DHT22);

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

  Serial.setTimeout(1000);
}

void clearSerialInputBuffer() {
  while (Serial.available() > 0) {
    Serial.read(); // Read and discard the character
  }
}

void loop() {

  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if (input == "GetData") {
      int door_state = digitalRead(door_pin); // 1 = closed
      int leak_state = digitalRead(leak_pin); // 1 = leaking

      Serial.print("DATA,");
      Serial.print(door_state);
      Serial.print(",");
      Serial.print(leak_state);
      Serial.print(",");


      for (int i=0; i<NUM_PROBES; i++) {
        tcs[i].sample();
        temps[i] = tcs[i].getTemperature();
        fault_bytes[i] = tcs[i].getStatus();
        Serial.print(temps[i]);
        Serial.print(",");
        Serial.print(fault_bytes[i]);
        Serial.print(",");
      }

      float ambient_temperature = dht.readTemperature();
      float humidity = dht.readHumidity();
      bool dhtstatus = 1;

      Serial.print(ambient_temperature);
      Serial.print(",");
      Serial.print(humidity);
      Serial.print(",");
      Serial.print(dhtstatus);
      Serial.println(",DONE");
    }

    else if (input == "RestartDHT") {
      dht.begin();
      dht.readTemperature();
      dht.readHumidity();
      Serial.println(1);
    }

    else {
      clearSerialInputBuffer();
    }

    

  }
      
}

