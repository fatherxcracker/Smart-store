/*
  Smart Fridge Dashboard
  Talks to the Flask backend (app.py) for live readings, thresholds,
  notifications, and fan control. Polls every few seconds instead of
  using a page reload, same pattern as Phase 1.
*/

// How often the dashboard requests new sensor readings.
const READINGS_POLL_MS = 3000;

// How often the dashboard checks for new notifications.
const NOTIFICATIONS_POLL_MS = 4000;

// How often the dashboard checks the fan status (so an email YES reply
// shows up as ON without refreshing the page).
const FAN_POLL_MS = 3000;

// Keeps track of whether the fan is currently ON or OFF.
let fanIsOn = false;

// True while the user is dragging the speed slider, so polling
// doesn't snap the slider back mid-drag.
let sliderBusy = false;


// gauges: Temperature and Humidity

function updateGauge(fridgeId, type, value) {
    const gaugeId = type === "temperature"
        ? "tempGauge" + fridgeId
        : "humidityGauge" + fridgeId;

    const textId = type === "temperature"
        ? "temp" + fridgeId
        : "humidity" + fridgeId;

    const gauge = document.getElementById(gaugeId);
    const text = document.getElementById(textId);

    if (!gauge || !text) return;

    if (value === null || value === undefined) {
        text.textContent = type === "temperature" ? "--°C" : "--%";
        gauge.style.background = "conic-gradient(#e2e8f0 0% 100%)";
        return;
    }

    const max = type === "temperature" ? 40 : 100;
    const progress = Math.max(0, Math.min(100, (value / max) * 100));
    const color = type === "temperature" ? "#14b8a6" : "#60a5fa";

    gauge.style.background =
        `conic-gradient(${color} 0% ${progress}%, #e2e8f0 ${progress}% 100%)`;

    text.textContent = type === "temperature"
        ? value.toFixed(1) + "°C"
        : value.toFixed(1) + "%";
}


// readings: Get Sensor Data from Flask

async function refreshReadings() {
    try {
        const res = await fetch("/api/readings");
        const data = await res.json();

        for (const fridgeId of [1, 2]) {
            const reading = data[fridgeId];

            if (!reading) continue;

            updateGauge(fridgeId, "temperature", reading.temperature);
            updateGauge(fridgeId, "humidity", reading.humidity);

            const statusEl = document.getElementById("status" + fridgeId);

            if (statusEl) {
                if (reading.temperature === null) {
                    statusEl.textContent = "Waiting for data";
                    statusEl.classList.remove("warning");
                } else if (reading.status === "warning") {
                    statusEl.textContent = "Warning";
                    statusEl.classList.add("warning");
                } else {
                    statusEl.textContent = "Normal";
                    statusEl.classList.remove("warning");
                }
            }
        }
    } catch (err) {
        console.error("Failed to load readings:", err);
    }
}


// thresholds: Load Saved Temperature Limits

async function loadThresholds() {
    try {
        const res = await fetch("/api/thresholds");
        const data = await res.json();

        for (const fridgeId of [1, 2]) {
            const input = document.getElementById("threshold" + fridgeId);

            if (input && data[fridgeId] !== undefined) {
                input.value = data[fridgeId];
            }
        }
    } catch (err) {
        console.error("Failed to load thresholds:", err);
    }
}


// thresholds: Save a New Temperature Limit

async function saveThreshold(fridgeId) {
    const input = document.getElementById("threshold" + fridgeId);
    const value = parseFloat(input.value);

    if (Number.isNaN(value)) {
        alert("Enter a valid temperature threshold first.");
        return;
    }

    try {
        const res = await fetch(`/api/thresholds/${fridgeId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ threshold: value }),
        });

        const data = await res.json();

        if (data.success) {
            refreshReadings();
        } else {
            alert(data.message || "Could not save threshold.");
        }
    } catch (err) {
        alert("Could not reach the server. Is app.py running?");
    }
}


// fan control: Update the Fan's Appearance

function applyFanUi(status) {
    fanIsOn =
        (typeof status === "string" ? status : status.status) === "ON";

    const fanStatusEl = document.getElementById("fanStatus");
    const fanIconEl = document.getElementById("fanIcon");
    const powerButton = document.getElementById("powerButton");
    const slider = document.getElementById("fanSlider");
    const rpmDisplay = document.getElementById("rpmDisplay");
    const speedValue = document.getElementById("speedValue");

    if (!fanStatusEl || !fanIconEl || !powerButton ||
        !slider || !rpmDisplay || !speedValue) {
        return;
    }

    fanStatusEl.textContent = fanIsOn ? "ON" : "OFF";
    fanStatusEl.classList.toggle("running", fanIsOn);
    fanIconEl.classList.toggle("spinning", fanIsOn);
    powerButton.textContent = fanIsOn ? "Turn OFF" : "Turn ON";

    // Allow changing the duty cycle when the fan is running.
    slider.disabled = !fanIsOn;

    // Synchronize the slider with the duty cycle returned by Flask.
    if (status && typeof status === "object" &&
        status.duty_cycle !== undefined && !sliderBusy) {
        slider.value = status.duty_cycle;
    }

    const dutyCycle = fanIsOn ? Number(slider.value) : 0;

    rpmDisplay.textContent = dutyCycle + "%";
    speedValue.textContent = slider.value + "% duty cycle";
}


// fan control: Turn Fan ON or OFF

async function toggleFan() {
    try {
        const res = await fetch("/api/fan/toggle", {
            method: "POST"
        });

        const data = await res.json();

        if (!res.ok) {
            alert(data.message || "Could not change fan state.");
            return;
        }

        applyFanUi(data);
    } catch (err) {
        alert("Could not reach the server. Is app.py running?");
    }
}


// fan control: Update the duty-cycle display while moving the slider

function updateFanSpeed() {
    const slider = document.getElementById("fanSlider");
    const rpmDisplay = document.getElementById("rpmDisplay");
    const speedValue = document.getElementById("speedValue");

    const dutyCycle = Number(slider.value);
    sliderBusy = true;

    // Show 0% when the fan is OFF.
    rpmDisplay.textContent = (fanIsOn ? dutyCycle : 0) + "%";
    speedValue.textContent = dutyCycle + "% duty cycle";
}


// Send the selected duty cycle to the Raspberry Pi when the slider is released.

async function saveFanSpeed() {
    const slider = document.getElementById("fanSlider");
    const dutyCycle = Number(slider.value);
    sliderBusy = false;

    try {
        const res = await fetch("/api/fan/speed", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ duty_cycle: dutyCycle })
        });

        const data = await res.json();

        if (!res.ok || !data.success) {
            alert(data.message || "Could not set fan speed.");
            return;
        }

        applyFanUi(data);
    } catch (err) {
        alert("Could not reach the server. Is app.py running?");
    }
}


// fan control: Load Current Fan Status

async function loadFanStatus() {
    try {
        const res = await fetch("/api/fan/status");
        const data = await res.json();

        applyFanUi(data);
    } catch (err) {
        console.error("Failed to load fan status:", err);
    }
}


// notifications: Display System Alerts

async function refreshNotifications() {
    try {
        const res = await fetch("/api/notifications");
        const items = await res.json();

        const container = document.getElementById("notifications");

        if (!items.length) {
            container.textContent = "No active alerts.";
            return;
        }

        container.innerHTML = "";

        items.forEach((item) => {
            const div = document.createElement("div");

            div.className =
                item.level === "warning" ? "alert" : "note " + item.level;

            const time = new Date(item.created_at).toLocaleTimeString();

            div.textContent = `[${time}] ${item.message}`;

            container.appendChild(div);
        });
    } catch (err) {
        console.error("Failed to load notifications:", err);
    }
}


// initialization: Start the Dashboard

loadThresholds();
refreshReadings();
loadFanStatus();
refreshNotifications();


// automatic refresh

setInterval(refreshReadings, READINGS_POLL_MS);
setInterval(refreshNotifications, NOTIFICATIONS_POLL_MS);
setInterval(loadFanStatus, FAN_POLL_MS);
