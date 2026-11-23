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
    const pill = $(prefix + "-status");
    if (pill) {
        pill.textContent = online ? "Online" : (data.seconds_since_update === null ? "No data yet" : "Offline (stale)");
        pill.className = "pill " + (online ? "good" : "low");
    }
    setText(prefix + "-temp", number(data.temperature?.value, 1, " °C"));
    setText(prefix + "-hum", number(data.humidity?.value, 0, " %"));
    setText(prefix + "-light", data.light ? `${Math.round(data.light.value)} lux` : "--");
    const motion = $(prefix + "-motion");
    if (motion) {
        const recent = data.last_motion_seconds !== null && data.last_motion_seconds < 60;
        motion.textContent = data.last_motion_seconds === null ? "No motion yet" : (recent ? "Motion detected" : "No motion");
        motion.className = recent ? "motion-on" : "";
    }
    setText(prefix + "-motion-note", data.last_motion_seconds === null ? "" :
        `Last motion ${ago(data.last_motion_seconds)} · ${data.motion_last_hour} ${data.motion_last_hour === 1 ? "event" : "events"} in the last hour`);
    setText(prefix + "-updated", data.seconds_since_update === null ? "Waiting for the sensor" : `Updated ${ago(data.seconds_since_update)}`);
    setText(prefix + "-battery", data.battery ? `Battery ${Math.round(data.battery.value)} %` : "");
}
