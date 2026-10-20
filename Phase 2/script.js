
/*
  Smart Fridge Dashboard
  Front-end only

  No MQTT, sensors, database, or backend.
*/

// Set the initial dashboard appearance
document.getElementById("fanStatus").textContent = "OFF";

document.getElementById("status1").textContent =
    "Waiting for data";

document.getElementById("status2").textContent =
    "Waiting for data";

// Display placeholders instead of sensor readings
document.getElementById("temp1").textContent = "--°C";
document.getElementById("humidity1").textContent = "--%";

document.getElementById("temp2").textContent = "--°C";
document.getElementById("humidity2").textContent = "--%";

// Display initial notification message
document.getElementById("notifications").textContent =
    "No notifications to display.";

// Front-end placeholder for threshold saving
function saveThreshold(id) {
    alert(
        "Threshold setting for Refrigerator " + id +
        " will be connected to the backend later."
    );
}


// Update the circular gauges when sensor data is available
function updateGauge(fridgeId, type, value) {

    // Find the correct gauge and text
    const gaugeId = type === "temperature"
        ? "tempGauge" + fridgeId
        : "humidityGauge" + fridgeId;

    const textId = type === "temperature"
        ? "temp" + fridgeId
        : "humidity" + fridgeId;

    const gauge = document.getElementById(gaugeId);
    const text = document.getElementById(textId);

    // Temperature: 0 to 40°C
    // Humidity: 0 to 100%
    const max = type === "temperature" ? 40 : 100;

    // Calculate how much of the circle should fill
    const progress = Math.max(
        0,
        Math.min(100, (value / max) * 100)
    );

    // Set the colors
    const color = type === "temperature"
        ? "#14b8a6"  // Temperature: teal
        : "#60a5fa"; // Humidity: blue

    // Fill the circle according to the value
    gauge.style.background = `conic-gradient(
        ${color} 0% ${progress}%,
        #e2e8f0 ${progress}% 100%
    )`;

    // Display the value inside the circle
    text.textContent = type === "temperature"
        ? value.toFixed(1) + "°C"
        : value.toFixed(1) + "%";
}


