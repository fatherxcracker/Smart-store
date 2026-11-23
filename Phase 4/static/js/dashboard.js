"use strict";

function renderDashboard(d) {
    setText("k-sales", money(d.today.total));
    setText("k-orders", d.today.orders);
    setText("k-customers", d.today.customers);
    setText("k-low", d.stock.low_count);
    setText("week-note", `Last 7 days: ${money(d.week.total)}`);
    window.setChart($("week-chart"), d.week.daily);

    const low = $("low-list");
    low.replaceChildren();
    if (!d.stock.low.length) low.append(el("li", "", "Every product is above its low-stock limit."));
    for (const p of d.stock.low) {
        const item = el("li", "", `${p.name} (${p.category}) — `);
        item.append(el("strong", "", `${p.in_stock} left`), document.createTextNode(` · limit ${p.limit}`));
        low.append(item);
    }

    const tiles = $("fridge-tiles");
    tiles.replaceChildren();
    if (!d.fridges) tiles.append(el("article", "", "Fridge monitoring is not running."));
    else {
        for (const [id, r] of Object.entries(d.fridges.readings)) {
            const tile = el("article");
            tile.append(el("span", "", `Refrigerator ${id}`), el("strong", "", number(r.temperature, 1, " °C")));
            const pill = el("span", "pill " + (r.temperature === null ? "" : r.status === "warning" ? "low" : "good"),
                r.temperature === null ? "Waiting for data" : r.status === "warning" ? "Too warm" : "Normal");
            tile.append(pill, el("small", "", `Humidity ${number(r.humidity, 0, " %")} · limit ${number(r.threshold, 1, " °C")}`));
            tiles.append(tile);
        }
        const fan = el("article");
        fan.append(el("span", "", "Fan"), el("strong", "", d.fridges.fan.status),
            el("small", "", `${d.fridges.fan.duty_cycle}% duty cycle · MQTT ${d.fridges.mqtt ? "connected" : "not connected"}`));
        tiles.append(fan);
    }

    renderSensor(d.sensor, "d");

    const notes = $("notes");
    notes.replaceChildren();
    if (!d.notifications.length) notes.append(el("li", "", "No notifications yet."));
    for (const n of d.notifications) {
        const item = el("li", "note-" + n.level);
        item.append(el("span", "pill " + (n.level === "error" || n.level === "warning" ? "low" : "good"), n.level), document.createTextNode(" " + n.message));
        notes.append(item);
    }
    setText("dash-status", `Updated ${new Date().toLocaleTimeString()} · refreshes every 5 seconds`);
}

async function loadDashboard() {
    try {
        const response = await fetch("/reports/api/dashboard", { credentials: "same-origin", cache: "no-store" });
        if (response.status === 401 || response.status === 403) { setText("dash-status", "Log in again as an administrator."); return; }
        if (!response.ok) throw new Error();
        renderDashboard(await response.json());
    } catch {
        setText("dash-status", "Could not refresh. Retrying shortly.");
    }
    setTimeout(loadDashboard, 5000);
}
loadDashboard();
