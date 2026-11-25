const fridgeMessagesFr = {
    "Waiting for data": "En attente de données",
    "Warning": "Avertissement",
    "Normal": "Normal",
    "ON": "MARCHE",
    "OFF": "ARRÊT",
    "Turn OFF": "Éteindre",
    "Turn ON": "Allumer",
    "Enter a valid temperature threshold first.": "Entrez d’abord un seuil de température valide.",
    "Could not save threshold.": "Impossible d’enregistrer le seuil.",
    "Could not change fan state.": "Impossible de modifier l’état du ventilateur.",
    "Could not set fan speed.": "Impossible de régler la vitesse du ventilateur.",
    "Could not reach the server. Is app.py running?": "Impossible de joindre le serveur. Est-ce que app.py est en cours d’exécution?",
    "No active alerts.": "Aucune alerte active.",
    "Unknown fridge id.": "Identifiant de réfrigérateur inconnu.",
    "threshold must be a number.": "Le seuil doit être un nombre.",
    "duty_cycle must be an integer from 0 to 100.": "Le rapport cyclique doit être un nombre entier de 0 à 100.",
    "duty_cycle must be between 0 and 100.": "Le rapport cyclique doit être compris entre 0 et 100.",
    "Fan turned OFF manually from the dashboard.": "Le ventilateur a été éteint manuellement depuis le tableau de bord."
};

const isFrench = () => document.documentElement.lang === "fr";
const localized = text => isFrench() ? fridgeMessagesFr[text] ?? text : text;
const dutyLabel = value => isFrench() ? `${value} % de rapport cyclique` : `${value}% duty cycle`;

function localizedAlert(text) {
    if (!isFrench()) return text;
    return localized(text)
        .replace(/^Refrigerator (\d+) threshold set to (.+)C\.$/, "Seuil du r\u00e9frig\u00e9rateur $1 r\u00e9gl\u00e9 \u00e0 $2 \u00b0C.")
        .replace(/^Fan duty cycle set to (\d+)%\.$/, "Rapport cyclique du ventilateur r\u00e9gl\u00e9 \u00e0 $1 %.")
        .replace(/^Fan turned ON manually at (\d+)% duty cycle\.$/, "Ventilateur allum\u00e9 manuellement \u00e0 $1 %.")
        .replace(/^Temperature alert: Refrigerator (\d+) is (.+)C \(threshold (.+)C\)\. Email sent - waiting for a response\.$/, "Alerte : le r\u00e9frig\u00e9rateur $1 est \u00e0 $2 \u00b0C (seuil : $3 \u00b0C). Courriel envoy\u00e9, en attente d'une r\u00e9ponse.")
        .replace(/^Temperature alert: Refrigerator (\d+) is (.+)C, but the alert email could not be sent \(check \.env SMTP settings\)\.$/, "Alerte : le r\u00e9frig\u00e9rateur $1 est \u00e0 $2 \u00b0C. Le courriel n'a pas pu \u00eatre envoy\u00e9 (v\u00e9rifiez les param\u00e8tres SMTP).")
        .replace(/^User replied YES \((.+)\) - fan turned ON at (\d+)% \(Refrigerator (\d+) was (.+)C\)\.$/, "R\u00e9ponse OUI ($1) : ventilateur allum\u00e9 \u00e0 $2 % (r\u00e9frig\u00e9rateur $3 : $4 \u00b0C).")
        .replace(/^User replied NO \((.+)\) - no action taken for Refrigerator (\d+) \((.+)C\)\.$/, "R\u00e9ponse NON ($1) : aucune action pour le r\u00e9frig\u00e9rateur $2 ($3 \u00b0C).");
}

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
        gauge.style.setProperty("--gauge-progress", "0%");
        return;
    }

    const max = type === "temperature" ? 40 : 100;
    const progress = Math.max(0, Math.min(100, (value / max) * 100));

    // Send the reading percentage to CSS to fill the gauge
    gauge.style.setProperty("--gauge-progress", `${progress}%`);

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
                    statusEl.textContent = localized("Waiting for data");
                    statusEl.classList.remove("warning");
                } else if (reading.status === "warning") {
                    statusEl.textContent = localized("Warning");
                    statusEl.classList.add("warning");
                } else {
                    statusEl.textContent = localized("Normal");
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
        alert(localized("Enter a valid temperature threshold first."));
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
            alert(localized(data.message || "Could not save threshold."));
        }
    } catch (err) {
        alert(localized("Could not reach the server. Is app.py running?"));
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

    fanStatusEl.textContent = localized(fanIsOn ? "ON" : "OFF");
    fanStatusEl.classList.toggle("running", fanIsOn);
    fanIconEl.classList.toggle("spinning", fanIsOn);
    powerButton.textContent = localized(fanIsOn ? "Turn OFF" : "Turn ON");

    // Allow changing the duty cycle when the fan is running.
    slider.disabled = !fanIsOn;

    // Synchronize the slider with the duty cycle returned by Flask.
    if (status && typeof status === "object" &&
        status.duty_cycle !== undefined && !sliderBusy) {
        slider.value = status.duty_cycle;
    }

    const dutyCycle = fanIsOn ? Number(slider.value) : 0;

    rpmDisplay.textContent = dutyCycle + "%";
    speedValue.textContent = dutyLabel(slider.value);
}


// fan control: Turn Fan ON or OFF

async function toggleFan() {
    try {
        const res = await fetch("/api/fan/toggle", {
            method: "POST"
        });

        const data = await res.json();

        if (!res.ok) {
            alert(localized(data.message || "Could not change fan state."));
            return;
        }

        applyFanUi(data);
    } catch (err) {
        alert(localized("Could not reach the server. Is app.py running?"));
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
    speedValue.textContent = dutyLabel(dutyCycle);
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
            alert(localized(data.message || "Could not set fan speed."));
            return;
        }

        applyFanUi(data);
    } catch (err) {
        alert(localized("Could not reach the server. Is app.py running?"));
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
            container.textContent = localized("No active alerts.");
            return;
        }

        container.innerHTML = "";

        items.forEach((item) => {
            const div = document.createElement("div");

            div.className =
                item.level === "warning" ? "alert" : "note " + item.level;

            const time = new Date(item.created_at).toLocaleTimeString(isFrench() ? "fr-CA" : "en-CA");

            div.textContent = `[${time}] ${localizedAlert(item.message)}`;

            container.appendChild(div);
        });
    } catch (err) {
        console.error("Failed to load notifications:", err);
    }
}


// initialization: Start the Dashboard

document.addEventListener("smartstore-language", () => {
    refreshReadings();
    loadFanStatus();
    refreshNotifications();
});

loadThresholds();
refreshReadings();
loadFanStatus();
refreshNotifications();


// automatic refresh

setInterval(refreshReadings, READINGS_POLL_MS);
setInterval(refreshNotifications, NOTIFICATIONS_POLL_MS);
setInterval(loadFanStatus, FAN_POLL_MS);


// Connect each Save button to the correct fridge
document.querySelectorAll("[data-save-threshold]").forEach(button => {
    button.addEventListener("click", () => saveThreshold(Number(button.dataset.saveThreshold)));
});
// Connect the fan button and speed slider to their actions
document.getElementById("powerButton").addEventListener("click", toggleFan);
document.getElementById("fanSlider").addEventListener("input", updateFanSpeed);
document.getElementById("fanSlider").addEventListener("change", saveFanSpeed);
