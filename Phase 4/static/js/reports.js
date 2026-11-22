"use strict";

document.getElementById("print-report")?.addEventListener("click", () => window.print());

function drawCharts() {
    const ns = "http://www.w3.org/2000/svg";
    for (const figure of document.querySelectorAll(".chart")) {
        const data = JSON.parse(figure.querySelector("script").textContent);
        figure.querySelector("svg")?.remove();
        figure.querySelector(".empty-chart")?.remove();
        if (!data.length) {
            const message = document.createElement("p");
            message.className = "empty-chart";
            message.textContent = "No purchases in this period. Try a different date range.";
            figure.append(message);
            continue;
        }
        function element(tag, attrs = {}, text = null) {
            const node = document.createElementNS(ns, tag);
            for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
            if (text !== null) node.textContent = text;
            return node;
        }
        const width = Math.max(300, figure.clientWidth);
        const right = width - 20;
        const svg = element("svg", { viewBox: `0 0 ${width} 260`, role: "img", "aria-label": figure.getAttribute("aria-label") });
        const peak = Math.max(1, ...data.map(row => Number(row[figure.dataset.y])));
        const max = figure.dataset.money ? peak : Math.max(2, Math.ceil(peak / 2) * 2);
        const x = index => data.length === 1 ? (70 + right) / 2 : 70 + index / (data.length - 1) * (right - 70);
        const y = value => 210 - Number(value) / max * 175;
        const format = value => figure.dataset.money ? new Intl.NumberFormat("en-CA", {style:"currency",currency:"CAD"}).format(value) : String(Math.round(value));
        for (const ratio of [0, 0.5, 1]) {
            svg.append(element("line", {x1:70, x2:right, y1:y(max * ratio), y2:y(max * ratio)}));
            svg.append(element("text", {x:62, y:y(max * ratio) + 4, "text-anchor":"end"}, format(max * ratio)));
        }
        svg.append(element("polyline", {points:data.map((row, i) => `${x(i)},${y(row[figure.dataset.y])}`).join(" ")}));
        data.forEach((row, i) => {
            const dot = element("circle", {cx:x(i), cy:y(row[figure.dataset.y]), r:data.length > 90 ? 2 : 4});
            dot.append(element("title", {}, `${row[figure.dataset.x]}: ${format(row[figure.dataset.y])}`));
            svg.append(dot);
        });
        const ticks = width < 540 ? [0, data.length - 1] : [0, Math.floor((data.length - 1) / 2), data.length - 1];
        for (const i of new Set(ticks)) {
            svg.append(element("text", {x:x(i), y:242, "text-anchor":data.length === 1 ? "middle" : i === 0 ? "start" : i === data.length - 1 ? "end" : "middle"}, String(data[i][figure.dataset.x]).slice(0, 10)));
        }
        figure.append(svg);
    }
}

drawCharts();
let resizeFrame;
window.addEventListener("resize", () => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(drawCharts);
});
let timer;
let stopped = false;
async function refreshReport() {
    const status = document.getElementById("refresh-status");
    if (!document.hidden) {
        try {
            const response = await fetch(location.href, {credentials:"same-origin", cache:"no-store"});
            if (response.status === 401 || response.status === 403) {
                status.textContent = "Your session or access has changed. Log in again on the account page.";
                document.getElementById("report-content").replaceChildren();
                stopped = true;
                return;
            }
            if (!response.ok) throw new Error();
            const page = new DOMParser().parseFromString(await response.text(), "text/html");
            const content = page.getElementById("report-content");
            if (!content) throw new Error();
            // Report content has no form inputs; keep filter edits and focus intact.
            document.getElementById("report-content").replaceChildren(...content.childNodes);
            drawCharts();
            status.textContent = `Updated ${new Date().toLocaleTimeString()} · refreshes every 5 seconds`;
        } catch {
            status.textContent = "Could not refresh. Showing the last successful report; retrying shortly.";
        }
    }
    if (!stopped) timer = setTimeout(refreshReport, 5000);
}
if (!document.querySelector("#report-content h2")?.textContent.includes("Check your filters")) {
    timer = setTimeout(refreshReport, 5000);
}
window.addEventListener("pagehide", () => { stopped = true; clearTimeout(timer); });
