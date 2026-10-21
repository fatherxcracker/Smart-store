
/*
  Smart Fridge Dashboard
  Talks to the Flask backend (app.py) for live readings, thresholds,
  notifications, and fan control. Polls every few seconds instead of
  using a page reload, same pattern as Phase 1.
*/

// How often the dashboard requests new sensor readings.
// 3000 milliseconds = 3 seconds.
const READINGS_POLL_MS = 3000;

// How often the dashboard checks for new notifications.
// 4000 milliseconds = 4 seconds.
const NOTIFICATIONS_POLL_MS = 4000;

// Keeps track of whether the fan is currently ON or OFF.
// false = OFF, true = ON.
let fanIsOn = false;


// gauges: Temperature and Humidity

// Updates the circular temperature or humidity gauge
// fridgeId: Refrigerator 1 or 2.
// type: "temperature" or "humidity".
// value: Reading received from the backend.
// Example: updateGauge(1, "temperature", 8.5)
// Updates Refrigerator 1's temperature gauge to 8.5°C.
function updateGauge(fridgeId, type, value) {

    // Select the correct circle based on the reading type.
    // Examples: tempGauge1, humidityGauge2.
    const gaugeId = type === "temperature" ? "tempGauge" + fridgeId : "humidityGauge" + fridgeId;

    // Select the text inside the corresponding circle
    // Examples: temp1, humidity2.
    const textId = type === "temperature" ? "temp" + fridgeId : "humidity" + fridgeId;

    // Find the HTML elements using their IDs.
    const gauge = document.getElementById(gaugeId);
    const text = document.getElementById(textId);

    // Stop if the gauge or its text element cannot be found.
    if (!gauge || !text) return;

    // If there is no reading yet, display placeholders.
    // The circle remains empty and gray.
    if (value === null || value === undefined) {
        text.textContent = type === "temperature" ? "--°C" : "--%";
        gauge.style.background = "conic-gradient(#e2e8f0 0% 100%)";
        return;
    }

    // Maximum value used to calculate the circle's progress
    // Temperature uses 40°C and humidity uses 100%
    const max = type === "temperature" ? 40 : 100;

    // Convert the reading into a percentage
    // Example: 10°C / 40°C * 100 = 25%.
    // Math.max and Math.min keep the result between 0 and 100.
    const progress = Math.max(0, Math.min(100, (value / max) * 100));

    // Choose the gauge color
    // Temperature = teal, Humidity = blue
    const color = type === "temperature" ? "#14b8a6" : "#60a5fa";

    // Fill the circle based on the calculated percentage.
    // The remaining portion of the circle stays gray.
    gauge.style.background = `conic-gradient(${color} 0% ${progress}%, #e2e8f0 ${progress}% 100%)`;

    // Display the reading inside the circle with one decimal place.
    // Example: 8.5°C or 65.0%.
    text.textContent = type === "temperature" ? value.toFixed(1) + "°C" : value.toFixed(1) + "%";
}


// readings: Get Sensor Data from Flask

// Requests the latest temperature and humidity readings
// for both refrigerators from the Flask backend.
async function refreshReadings() {

    // try/catch prevents a failed request from crashing the script.
    try {

        // Send a GET request to the Flask readings endpoint.
        const res = await fetch("/api/readings");

        // Convert the JSON response into a JavaScript object.
        const data = await res.json();

        // Repeat the process for Refrigerator 1 and Refrigerator 2.
        for (const fridgeId of [1, 2]) {

            // Get the current refrigerator's readings.
            const reading = data[fridgeId];

            // Skip this refrigerator if no reading object exists.
            if (!reading) continue;

            // Update the temperature circle using the received value.
            updateGauge(fridgeId, "temperature", reading.temperature);

            // Update the humidity circle using the received value.
            updateGauge(fridgeId, "humidity", reading.humidity);

            // Find the refrigerator's status label in HTML.
            // Example: status1 or status2.
            const statusEl = document.getElementById("status" + fridgeId);

            // Only update the status if the HTML element exists.
            if (statusEl) {

                // If temperature is missing, show Waiting for data.
                if (reading.temperature === null) {
                    statusEl.textContent = "Waiting for data";

                    // Remove the red warning appearance.
                    statusEl.classList.remove("warning");

                // If Flask reports a warning, show Warning.
                } else if (reading.status === "warning") {
                    statusEl.textContent = "Warning";

                    // Apply the warning CSS styling.
                    statusEl.classList.add("warning");

                // Otherwise, show Normal.
                } else {
                    statusEl.textContent = "Normal";

                    // Remove warning styling if it was previously applied.
                    statusEl.classList.remove("warning");
                }
            }
        }

    // Handle errors such as Flask not responding.
    } catch (err) {
        console.error("Failed to load readings:", err);
    }
}


// thresholds: Load Saved Temperature Limits

// Gets the saved temperature thresholds from Flask
// These are the limits used to determine if a fridge is too warm
async function loadThresholds() {
    try {

        // Request the saved thresholds from the backend.
        const res = await fetch("/api/thresholds");

        // Convert the JSON response into a JavaScript object.
        const data = await res.json();

        // Update the threshold input for each refrigerator.
        for (const fridgeId of [1, 2]) {

            // Find the correct input box.
            // Example: threshold1 or threshold2.
            const input = document.getElementById("threshold" + fridgeId);

            // If the input exists and Flask returned a threshold,
            // display the saved value inside the box.
            if (input && data[fridgeId] !== undefined) {
                input.value = data[fridgeId];
            }
        }

    // Display an error in the browser console if loading fails.
    } catch (err) {
        console.error("Failed to load thresholds:", err);
    }
}


// thresholds - Save a New Temperature Limit

// Runs when the user clicks Save beside a refrigerator.
// Sends the entered threshold to the Flask backend.
async function saveThreshold(fridgeId) {

    // Find the input box for the selected refrigerator.
    const input = document.getElementById("threshold" + fridgeId);

    // Convert the entered value into a decimal number.
    const value = parseFloat(input.value);

    // If the input is not a number, show an alert and stop.
    if (Number.isNaN(value)) {
        alert("Enter a valid temperature threshold first.");
        return;
    }

    try {

        // Send the new threshold to Flask.
        // POST is used because we are submitting data.
        const res = await fetch(`/api/thresholds/${fridgeId}`, {
            method: "POST",

            // Tell Flask that the request contains JSON.
            headers: { "Content-Type": "application/json" },

            // Convert the threshold into JSON before sending.
            // Example: {"threshold":6}
            body: JSON.stringify({ threshold: value }),
        });

        // Read Flask's response after attempting to save.
        const data = await res.json();

        // Check whether Flask reports a successful save.
        if (data.success) {

            // Refresh the readings to update the fridge status
            // according to the newly saved threshold.
            refreshReadings();

        } else {

            // Show the error returned by Flask,
            // or a default message if none was provided.
            alert(data.message || "Could not save threshold.");
        }

    // Handle connection problems with the backend.
    } catch (err) {
        alert("Could not reach the server. Is app.py running?");
    }
}

// fan control: Update the Fan's Appearance

// Updates the fan section of the dashboard.
// It changes the displayed status, button, icon, and RPM.
// It does not directly control the physical motor.
function applyFanUi(status) {

    // Convert the received status into a boolean.
    // "ON" becomes true, anything else becomes false.
    fanIsOn = status === "ON";

    // Find all fan-related elements in index.html.
    const fanStatusEl = document.getElementById("fanStatus");
    const fanIconEl = document.getElementById("fanIcon");
    const powerButton = document.getElementById("powerButton");
    const slider = document.getElementById("fanSlider");
    const rpmDisplay = document.getElementById("rpmDisplay");
    const speedValue = document.getElementById("speedValue");

    // Display ON or OFF beside Fan Control.
    fanStatusEl.textContent = fanIsOn ? "ON" : "OFF";

    // Add or remove the green running status style.
    fanStatusEl.classList.toggle("running", fanIsOn);

    // Make the fan icon spin when the fan is ON.
    fanIconEl.classList.toggle("spinning", fanIsOn);

    // Change the button text based on the fan's state.
    powerButton.textContent = fanIsOn ? "Turn OFF" : "Turn ON";

    // Enable the speed slider when ON, disable it when OFF.
    slider.disabled = !fanIsOn;

    // Show the selected RPM when ON, or 0 when OFF.
    // This is a displayed target value, not measured RPM.
    const rpm = fanIsOn ? slider.value : 0;

    // Update the large RPM number.
    rpmDisplay.textContent = rpm;

    // Update the RPM label beside the slider.
    speedValue.textContent = rpm + " RPM";
}

// fan control: Turn Fan ON or OFF

// Runs when the user clicks the fan power button.
// Sends a POST request to Flask to toggle the fan.
async function toggleFan() {
    try {

        // Ask Flask to change the fan state.
        const res = await fetch("/api/fan/toggle", { method: "POST" });

        // Convert Flask's response into a JavaScript object.
        const data = await res.json();

        // Update the fan interface with the returned status.
        applyFanUi(data.status);

    // Show an error if the server cannot be reached.
    } catch (err) {
        alert("Could not reach the server. Is app.py running?");
    }
}


// fan control: Update RPM Display

// Runs when the user moves the fan speed slider.
// This only changes the displayed RPM value.
// It does not send speed commands to the motor.
function updateFanSpeed() {

    // Find the slider and both RPM display elements.
    const slider = document.getElementById("fanSlider");
    const rpmDisplay = document.getElementById("rpmDisplay");
    const speedValue = document.getElementById("speedValue");

    // Stop if the fan is OFF.
    if (!fanIsOn) return;

    // Update the large RPM display using the slider value.
    rpmDisplay.textContent = slider.value;

    // Update the RPM label beside the slider.
    speedValue.textContent = slider.value + " RPM";
}

// fan control: Load Current Fan Status

// Gets the current fan status when the dashboard opens.
// This makes the interface match the backend's reported state.
async function loadFanStatus() {
    try {

        // Request the current fan state from Flask.
        const res = await fetch("/api/fan/status");

        // Convert the JSON response.
        const data = await res.json();

        // Update the fan interface.
        applyFanUi(data.status);

    // Log an error if the status cannot be loaded.
    } catch (err) {
        console.error("Failed to load fan status:", err);
    }
}

// notifications - Display System Alerts

// Requests notifications from Flask and displays them
// inside the System Notifications section.
async function refreshNotifications() {
    try {

        // Get the notifications from the backend.
        const res = await fetch("/api/notifications");

        // Convert the JSON response into an array.
        const items = await res.json();

        // Find the notification container in index.html.
        const container = document.getElementById("notifications");

        // If no notifications exist, display a default message.
        if (!items.length) {
            container.textContent = "No active alerts.";
            return;
        }

        // Clear previously displayed notifications.
        container.innerHTML = "";

        // Loop through every notification returned by Flask.
        items.forEach((item) => {

            // Create a new HTML div for this notification.
            const div = document.createElement("div");

            // Use red alert styling for warnings.
            // Other messages use the normal note styling.
            div.className = item.level === "warning" ? "alert" : "note";

            // Convert the notification timestamp to local time.
            const time = new Date(item.created_at).toLocaleTimeString();

            // Combine the time and notification message.
            div.textContent = `[${time}] ${item.message}`;

            // Add the notification to the dashboard.
            container.appendChild(div);
        });

    // Log an error if notifications cannot be retrieved.
    } catch (err) {
        console.error("Failed to load notifications:", err);
    }
}


//initialization: Start the Dashboard

// Load saved thresholds when the dashboard first opens.
loadThresholds();

// Get the latest temperature and humidity readings.
refreshReadings();

// Get the current fan ON/OFF status.
loadFanStatus();

// Load existing system notifications.
refreshNotifications();

//automatic refresh:

// Automatically request new readings every 3 seconds.
// The whole webpage does not need to reload.
setInterval(refreshReadings, READINGS_POLL_MS);

// Automatically request new notifications every 4 seconds.
setInterval(refreshNotifications, NOTIFICATIONS_POLL_MS);
