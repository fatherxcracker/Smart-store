/*
  Smart Fridge Dashboard
  Talks to the Flask backend (app.py) for live readings, thresholds,
  notifications, and fan control. Polls every few seconds instead of
  using a page reload, same pattern as Phase 1.
*/

const READINGS_POLL_MS = 3000;
const NOTIFICATIONS_POLL_MS = 4000;

let fanIsOn = false;

// Gauges
function updateGauge(fridgeId, type, value) {
    const gaugeId = type === "temperature" ? "tempGauge" + fridgeId : "humidityGauge" + fridgeId;
    const textId = type === "temperature" ? "temp" + fridgeId : "humidity" + fridgeId;

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

    gauge.style.background = `conic-gradient(${color} 0% ${progress}%, #e2e8f0 ${progress}% 100%)`;
    text.textContent = type === "temperature" ? value.toFixed(1) + "°C" : value.toFixed(1) + "%";
}

// Readings + status + thresholds
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

// Fan control
function applyFanUi(status) {
    fanIsOn = status === "ON";

    const fanStatusEl = document.getElementById("fanStatus");
    const fanIconEl = document.getElementById("fanIcon");
    const powerButton = document.getElementById("powerButton");
    const slider = document.getElementById("fanSlider");
    const rpmDisplay = document.getElementById("rpmDisplay");
    const speedValue = document.getElementById("speedValue");

    fanStatusEl.textContent = fanIsOn ? "ON" : "OFF";
    fanStatusEl.classList.toggle("running", fanIsOn);
    fanIconEl.classList.toggle("spinning", fanIsOn);
    powerButton.textContent = fanIsOn ? "Turn OFF" : "Turn ON";
    slider.disabled = !fanIsOn;

    const rpm = fanIsOn ? slider.value : 0;
    rpmDisplay.textContent = rpm;
    speedValue.textContent = rpm + " RPM";
}

async function toggleFan() {
    try {
        const res = await fetch("/api/fan/toggle", { method: "POST" });
        const data = await res.json();
        applyFanUi(data.status);
    } catch (err) {
        alert("Could not reach the server. Is app.py running?");
    }
}

function updateFanSpeed() {
    // Cosmetic only: the dashboard doesn't have a tachometer on the motor,
    // so the slider just reflects the target speed while the fan is on.
    const slider = document.getElementById("fanSlider");
    const rpmDisplay = document.getElementById("rpmDisplay");
    const speedValue = document.getElementById("speedValue");
    if (!fanIsOn) return;
    rpmDisplay.textContent = slider.value;
    speedValue.textContent = slider.value + " RPM";
}

async function loadFanStatus() {
    try {
        const res = await fetch("/api/fan/status");
        const data = await res.json();
        applyFanUi(data.status);
    } catch (err) {
        console.error("Failed to load fan status:", err);
    }
}

// Notifications
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
            div.className = item.level === "warning" ? "alert" : "note";
            const time = new Date(item.created_at).toLocaleTimeString();
            div.textContent = `[${time}] ${item.message}`;
            container.appendChild(div);
        });
    } catch (err) {
        console.error("Failed to load notifications:", err);
    }
}

// Init
loadThresholds();
refreshReadings();
loadFanStatus();
refreshNotifications();

setInterval(refreshReadings, READINGS_POLL_MS);
setInterval(refreshNotifications, NOTIFICATIONS_POLL_MS);
