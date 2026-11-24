"use strict";

async function loadSensor() {
    try {
        const response = await fetch("/sensors/api/latest", { credentials: "same-origin", cache: "no-store" });
        if (!response.ok) throw new Error();
        const data = await response.json();
        renderSensor(data, "s");
        setText("motion-count", data.motion ? data.motion_last_24h : "--");
    } catch (error) { console.error("Sensor:", error); }
}

async function loadHistory() {
    try {
        const hours = $("range").value;
        const response = await fetch(`/sensors/api/history?hours=${hours}`, { credentials: "same-origin", cache: "no-store" });
        if (!response.ok) throw new Error();
        const rows = await response.json();
        window.setChart($("c-temp"), rows.filter(r => r.temperature !== null));
        window.setChart($("c-hum"), rows.filter(r => r.humidity !== null));
        window.setChart($("c-light"), rows.filter(r => r.light !== null));
        const body = $("motion-rows");
        body.replaceChildren();
        const motion = rows.filter(r => r.motion === 1).slice(-10).reverse();
        if (!motion.length) {
            const tr = el("tr");
            const message = rows.some(r => r.motion !== null) ? "No motion in this period." : "No motion readings in this period.";
            const td = el("td", "", message);
            td.colSpan = 2;
            tr.append(td);
            body.append(tr);
        }
        for (const r of motion) {
            const tr = el("tr");
            tr.append(el("td", "", new Date(r.recorded_at.replace(" ", "T") + "Z").toLocaleString()), el("td", "", "Motion detected"));
            body.append(tr);
        }
    } catch (error) { console.error("History:", error); }
}

$("range").addEventListener("change", loadHistory);
loadSensor(); loadHistory();
setInterval(loadSensor, 5000);
setInterval(loadHistory, 30000);
