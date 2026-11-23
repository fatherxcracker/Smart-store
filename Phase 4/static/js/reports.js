"use strict";

document.getElementById("print-report")?.addEventListener("click", () => window.print());

const SVG_NS = "http://www.w3.org/2000/svg";

function svgNode(tag, attrs = {}, text = null) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (text !== null) node.textContent = text;
    return node;
}

/* Line chart without any library. The <figure> says what to plot:
   data-x / data-y: field names, data-money: dollars, data-unit: suffix such as "°C",
   data-time: x values are timestamps (shows HH:MM), data-empty: text when no data. */
function drawChart(figure, data) {
    figure.querySelector("svg")?.remove();
    figure.querySelector(".empty-chart")?.remove();
    if (!data.length) {
        const message = document.createElement("p");
        message.className = "empty-chart";
        message.textContent = figure.dataset.empty || "No purchases in this period. Try a different date range.";
        figure.append(message);
        return;
    }
    const y = figure.dataset.y;
    const values = data.map(row => Number(row[y]));
    const width = Math.max(300, figure.clientWidth);
    const right = width - 20;
    const svg = svgNode("svg", { viewBox: `0 0 ${width} 260`, role: "img", "aria-label": figure.getAttribute("aria-label") || "Chart" });
    const hasRange = figure.dataset.range === "true";
    const low = hasRange ? Math.min(...values) : 0;
    const high = Math.max(Math.max(1, ...values), low + 1);
    const span = hasRange ? (high - low) * 1.1 : (figure.dataset.money ? high : Math.max(2, Math.ceil(high / 2) * 2));
    const base = hasRange ? low - (high - low) * 0.05 : 0;
    const x = index => data.length === 1 ? (70 + right) / 2 : 70 + index / (data.length - 1) * (right - 70);
    const py = value => 210 - (Number(value) - base) / span * 175;
    const unit = figure.dataset.unit || "";
    const format = value => figure.dataset.money
        ? new Intl.NumberFormat(document.documentElement.lang === "fr" ? "fr-CA" : "en-CA", { style: "currency", currency: "CAD" }).format(value)
        : (Math.round(value * 10) / 10) + unit;
    for (const ratio of [0, 0.5, 1]) {
        const level = base + span * ratio;
        svg.append(svgNode("line", { x1: 70, x2: right, y1: py(level), y2: py(level) }));
        svg.append(svgNode("text", { x: 62, y: py(level) + 4, "text-anchor": "end" }, format(level)));
    }
    svg.append(svgNode("polyline", { points: data.map((row, i) => `${x(i)},${py(row[y])}`).join(" ") }));
    const label = value => {
        const text = String(value);
        if (figure.dataset.time === "true") {
            const stamp = new Date(text.replace(" ", "T") + "Z");
            return isNaN(stamp) ? text : stamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        }
        return text.slice(0, 10);
    };
    data.forEach((row, i) => {
        const dot = svgNode("circle", { cx: x(i), cy: py(row[y]), r: data.length > 90 ? 2 : 4 });
        dot.append(svgNode("title", {}, `${label(row[figure.dataset.x])}: ${format(row[y])}`));
        svg.append(dot);
    });
    const ticks = width < 540 ? [0, data.length - 1] : [0, Math.floor((data.length - 1) / 2), data.length - 1];
    for (const i of new Set(ticks)) {
        svg.append(svgNode("text", { x: x(i), y: 242, "text-anchor": data.length === 1 ? "middle" : i === 0 ? "start" : i === data.length - 1 ? "end" : "middle" },
            label(data[i][figure.dataset.x])));
    }
    figure.append(svg);
}

function drawCharts() {
    for (const figure of document.querySelectorAll(".chart")) {
        const source = figure.querySelector("script");
        if (source) drawChart(figure, JSON.parse(source.textContent));
        else if (figure._data) drawChart(figure, figure._data);
    }
}

/* Pages with their own live widgets call this to (re)draw one chart. */
window.setChart = (figure, data) => { figure._data = data; drawChart(figure, data); };

drawCharts();
document.addEventListener("smartstore-language", drawCharts);
let resizeFrame;
window.addEventListener("resize", () => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(drawCharts);
});

/* Report pages re-fetch themselves every 5 seconds. Pages with their own live
   widgets (dashboard, fridges, sensor) set data-live="off" and update themselves. */
let timer;
let stopped = false;
async function refreshReport() {
    const status = document.getElementById("refresh-status");
    if (!document.hidden) {
        try {
            const response = await fetch(location.href, { credentials: "same-origin", cache: "no-store" });
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
            // Don't replace the page while an administrator is typing in a form inside it.
            if (!document.activeElement?.closest?.("#report-content form")) {
                document.getElementById("report-content").replaceChildren(...content.childNodes);
                drawCharts();
            }
            status.textContent = `Updated ${new Date().toLocaleTimeString()} · refreshes every 5 seconds`;
        } catch {
            status.textContent = "Could not refresh. Showing the last successful report; retrying shortly.";
        }
    }
    if (!stopped) timer = setTimeout(refreshReport, 5000);
}
if (document.body.dataset.live !== "off" && !document.querySelector("#report-content h2")?.textContent.includes("Check your filters")) {
    timer = setTimeout(refreshReport, 5000);
}
window.addEventListener("pagehide", () => { stopped = true; clearTimeout(timer); });
