"use strict";
/* Small helpers shared by the dashboard, fridge and sensor pages (all text goes in
   with textContent, so product names or messages can never inject HTML). */
const $ = id => document.getElementById(id);

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
}

function ago(seconds) {
    if (seconds === null || seconds === undefined) return "never";
    if (seconds < 10) return "just now";
    if (seconds < 90) return `${Math.round(seconds)} s ago`;
    if (seconds < 5400) return `${Math.round(seconds / 60)} min ago`;
    if (seconds < 172800) return `${Math.round(seconds / 3600)} h ago`;
    return `${Math.round(seconds / 86400)} days ago`;
}

function money(value) {
    return new Intl.NumberFormat(document.documentElement.lang === "fr" ? "fr-CA" : "en-CA", { style: "currency", currency: "CAD" }).format(value || 0);
}

function number(value, digits = 1, unit = "") {
    return value === null || value === undefined ? "--" : `${Number(value).toFixed(digits)}${unit}`;
}

function setText(id, text) { const node = $(id); if (node) node.textContent = text; }

/* The MSP01 tiles are used on both the dashboard and the sensor page. */
function renderSensor(data, prefix) {
    const online = data.online;
    const readings = [data.temperature, data.humidity, data.light, data.motion, data.battery].filter(Boolean);
    const hasSimulated = readings.some(reading => reading.source === "simulator");
    const hasOther = readings.some(reading => reading.source !== "simulator");
    const pill = $(prefix + "-status");
    if (pill) {
        let status = data.seconds_since_update === null ? "No data yet" : "Offline (stale)";
        if (online) status = hasSimulated ? (hasOther ? "Includes simulated data" : "Simulated") : "Online";
        else if (hasSimulated) status = hasOther ? "Offline (includes simulated data)" : "Simulated (stale)";
        pill.textContent = status;
        pill.className = "pill " + (online ? "good" : "low");
    }
    setText(prefix + "-temp", number(data.temperature?.value, 1, " °C"));
    setText(prefix + "-hum", number(data.humidity?.value, 0, " %"));
    setText(prefix + "-light", data.light ? `${Math.round(data.light.value)} lux` : "--");
    const motion = $(prefix + "-motion");
    const motionIsFresh = data.motion && data.motion.age_seconds <= data.stale_after_seconds;
    if (motion) {
        motion.textContent = !data.motion ? "Waiting for motion data" : !motionIsFresh ? "Motion data is stale" :
            (data.motion.value === 1 ? "Motion detected" : "No motion");
        motion.className = motionIsFresh && data.motion.value === 1 ? "motion-on" : "";
    }
    setText(prefix + "-motion-note", !motionIsFresh || data.last_motion_seconds === null ? "" :
        `Last motion ${ago(data.last_motion_seconds)} · ${data.motion_last_hour} ${data.motion_last_hour === 1 ? "event" : "events"} in the last hour`);
    setText(prefix + "-updated", data.seconds_since_update === null ? "Waiting for the sensor" : `Updated ${ago(data.seconds_since_update)}`);
    setText(prefix + "-battery", data.battery ? `Battery ${Math.round(data.battery.value)} %` : "");
}
