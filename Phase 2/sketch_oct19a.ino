
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// Wi-Fi credentials
const char* ssid = "wifi network";
const char* password = "passwd";

// Raspberry Pi MQTT broker IP address
const char* mqtt_server = "ip";

// Change these for each ESP32
const char* mqtt_topic = "Frig2";
const char* client_id = "ESP32_Frig2";

// DHT11 sensor settings
#define DHTPIN 4
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  Serial.print("Connecting to WiFi");

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");

    if (client.connect(client_id)) {
      Serial.println("Connected!");
    } else {
      Serial.print("Failed, rc=");
      Serial.println(client.state());
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);

  dht.begin();

  setup_wifi();

  client.setServer(mqtt_server, 1883);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }

  client.loop();

  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("Failed to read DHT11!");
    delay(2000);
    return;
  }

  // Create JSON message
  String message = "{";
  message += "\"temperature\":";
  message += String(temperature, 1);
  message += ",";
  message += "\"humidity\":";
  message += String(humidity, 1);
  message += "}";

  // Send data to MQTT broker
  client.publish(mqtt_topic, message.c_str());

  Serial.print("Published to ");
  Serial.print(mqtt_topic);
  Serial.print(": ");
  Serial.println(message);

  delay(2000);
}
