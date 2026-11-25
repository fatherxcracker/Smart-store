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

// The sensor reports about once a second, so hours of history are thousands of
// points (the chart looked like a barcode). Average them into ~60 time buckets.
const CHART_POINTS = 60;

function smooth(rows, field, hours) {
    const bucketMs = Math.max(60000, hours * 3600000 / CHART_POINTS);  // at least 1 minute
    const buckets = new Map();
    for (const row of rows) {
        if (row[field] === null || row[field] === undefined) continue;
        const time = Date.parse(row.recorded_at.replace(" ", "T") + "Z");
        const key = Math.floor(time / bucketMs);
        const bucket = buckets.get(key) || { recorded_at: row.recorded_at, sum: 0, count: 0 };
        bucket.sum += Number(row[field]);
        bucket.count += 1;
        buckets.set(key, bucket);
    }
    return [...buckets.values()].map(b => ({
        recorded_at: b.recorded_at,
        [field]: Math.round(b.sum / b.count * 100) / 100,
    }));
}

async function loadHistory() {
    try {
        const hours = $("range").value;
        const response = await fetch(`/sensors/api/history?hours=${hours}`, { credentials: "same-origin", cache: "no-store" });
        if (!response.ok) throw new Error();
        const rows = await response.json();
        window.setChart($("c-temp"), smooth(rows, "temperature", hours));
        window.setChart($("c-hum"), smooth(rows, "humidity", hours));
        window.setChart($("c-light"), smooth(rows, "light", hours));
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

$("range").addEventListener("change", event => {
    const hours = event.target.value;
    const current = new URL(location.href);
    current.searchParams.set("hours", hours);
    history.replaceState(history.state, "", current);
    for (const link of document.querySelectorAll(".report-views a")) {
        const target = new URL(link.href);
        target.searchParams.set("hours", hours);
        link.href = target.href;
    }
    loadHistory();
});
loadSensor(); loadHistory();
setInterval(loadSensor, 5000);
setInterval(loadHistory, 30000);
