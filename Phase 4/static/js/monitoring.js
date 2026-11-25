"use strict";
/* Fridges and fan (Phase 2 dashboard, now part of the store application). */
const BASE = "/monitoring";
let fanIsOn = false;
let sliderBusy = false;

async function getJson(path) {
    const response = await fetch(BASE + path, { credentials: "same-origin", cache: "no-store" });
    if (!response.ok) throw new Error(String(response.status));
    return response.json();
}

async function postJson(path, body) {
    const response = await fetch(BASE + path, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || "Request failed");
    return data;
}

async function refreshReadings() {
    try {
        const data = await getJson("/api/readings");
        for (const id of [1, 2]) {
            const r = data[id];
            setText("temp" + id, number(r.temperature, 1, " °C"));
            setText("humidity" + id, number(r.humidity, 1, " %"));
            const pill = $("status" + id);
            const status = fridgeStatus(r);
            pill.textContent = status.text;
            pill.className = "pill " + status.level;
            setText("updated" + id, fridgeUpdated(r));
        }
    } catch (error) { markFridgeConnectionLost(); console.error("Readings:", error); }
}

async function loadThresholds() {
    try {
        const data = await getJson("/api/thresholds");
        for (const id of [1, 2]) if (data[id] !== undefined) $("threshold" + id).value = data[id];
    } catch (error) { console.error("Thresholds:", error); }
}

async function saveThreshold(id) {
    const value = parseFloat($("threshold" + id).value);
    if (Number.isNaN(value)) { alert("Enter a valid temperature limit first."); return; }
    try { await postJson(`/api/thresholds/${id}`, { threshold: value }); refreshReadings(); refreshNotifications(); }
    catch (error) { alert(error.message); }
}

async function refreshHistory() {
    for (const id of [1, 2]) {
        try { window.setChart($("hist" + id), await getJson(`/api/history/${id}?hours=6`)); } catch (error) { console.error("History:", error); }
    }
}

function applyFan(state) {
    fanIsOn = state.status === "ON";
    const presentation = fanPresentation(state);
    setText("fanStatus", presentation.status);
    $("fanStatus").className = "pill " + (presentation.level || (fanIsOn ? "good" : ""));
    setText("fanMode", presentation.mode);
    $("fanMode").className = "pill " + presentation.level;
    setText("fanModeNote", presentation.note);
    $("fanIcon").classList.toggle("spinning", fanIsOn);
    setText("powerButton", state.hardware_mode === "mock" ? (fanIsOn ? "Simulate OFF" : "Simulate ON") : (fanIsOn ? "Turn OFF" : "Turn ON"));
    const slider = $("fanSlider");
    slider.disabled = !fanIsOn;
    if (!sliderBusy && state.duty_cycle !== undefined) slider.value = state.duty_cycle;
    setText("rpmDisplay", (fanIsOn ? Number(slider.value) : 0) + "%");
    setText("speedValue", slider.value + "% duty cycle");
}

async function loadFan() {
    try { applyFan(await getJson("/api/fan/status")); } catch (error) { console.error("Fan:", error); }
}

async function refreshNotifications() {
    try {
        const items = await getJson("/api/notifications");
        const list = $("notifications");
        list.replaceChildren();
        if (!items.length) list.append(el("li", "", "No active alerts."));
        for (const n of items) {
            const item = el("li", "note-" + n.level);
            item.append(el("span", "pill " + (n.level === "warning" ? "low" : n.level === "success" ? "good" : ""), n.level),
                document.createTextNode(` [${new Date(n.created_at).toLocaleTimeString()}] `), el("span", "", n.message));
            list.append(item);
        }
    } catch (error) { console.error("Notifications:", error); }
}

document.querySelectorAll("[data-save]").forEach(b => b.addEventListener("click", () => saveThreshold(Number(b.dataset.save))));
$("powerButton").addEventListener("click", async () => {
    try { applyFan(await postJson("/api/fan/toggle")); refreshNotifications(); } catch (error) { alert(error.message); }
});
$("fanSlider").addEventListener("input", () => {
    sliderBusy = true;
    setText("rpmDisplay", (fanIsOn ? Number($("fanSlider").value) : 0) + "%");
    setText("speedValue", $("fanSlider").value + "% duty cycle");
});
$("fanSlider").addEventListener("change", async () => {
    sliderBusy = false;
    try { applyFan(await postJson("/api/fan/speed", { duty_cycle: Number($("fanSlider").value) })); }
    catch (error) { alert(error.message); }
});

loadThresholds(); refreshReadings(); loadFan(); refreshNotifications(); refreshHistory();
setInterval(refreshReadings, 3000);
setInterval(loadFan, 3000);
setInterval(refreshNotifications, 4000);
setInterval(refreshHistory, 30000);
