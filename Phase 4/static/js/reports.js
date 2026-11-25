/* An administrator who opens a report page directly lands inside the one-page dashboard instead. */
(function () {
    var body = document.body, shell = body && body.dataset.shell;
    var names = { dashboard: "overview", inventory: "inventory-report", sales: "sales", customers: "customers", monitoring: "fridges", sensors: "sensor", notifications: "notifications" };
    if (shell && window.self === window.top && names[body.dataset.section] && location.search.indexOf("standalone") < 0) {
        location.replace(shell + "#" + names[body.dataset.section]);
    }
})();
"use strict";

const reportExport = document.querySelector(".report-export");
if (reportExport) {
    const summary = reportExport.querySelector("summary");
    document.addEventListener("click", event => {
        if (!reportExport.open) return;
        const option = event.target.closest(".report-export-options a, .report-export-options button");
        if (option || !reportExport.contains(event.target)) reportExport.open = false;
        if (option) summary.focus();
    });
    reportExport.addEventListener("keydown", event => {
        if (event.key !== "Escape" || !reportExport.open) return;
        reportExport.open = false;
        summary.focus();
    });
    document.getElementById("print-report").addEventListener("click", () => window.print());
    document.getElementById("download-report-png")?.addEventListener("click", downloadReportPng);
}

function loadPngRenderer(url) {
    if (window.html2canvas) return Promise.resolve();
    return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = url;
        script.addEventListener("load", resolve, { once: true });
        script.addEventListener("error", () => {
            script.remove();
            reject(new Error("Could not load the PNG renderer"));
        }, { once: true });
        document.head.append(script);
    });
}

async function downloadReportPng(event) {
    const button = event.currentTarget;
    const status = document.getElementById("report-export-status");
    const report = document.getElementById("report-content");
    button.disabled = true;
    status.textContent = "Preparing PNG…";
    try {
        await loadPngRenderer(button.dataset.renderer);
        const options = {
            logging: false,
            windowWidth: Math.max(window.innerWidth, 960),
            onclone(doc, snapshot) {
                snapshot.closest(".screen-fit")?.style.removeProperty("--screen-scale");
                snapshot.classList.add("report-png-snapshot");
                const title = doc.createElement("h1");
                title.textContent = document.querySelector("main h1").textContent;
                snapshot.prepend(title);
                if (snapshot.dataset.exportContext) {
                    const context = doc.createElement("p");
                    context.className = "note";
                    context.textContent = snapshot.dataset.exportContext;
                    title.after(context);
                }

                // The renderer serializes SVGs as images, so chart styles must travel with them.
                for (const part of snapshot.querySelectorAll(".chart svg :is(line, polyline, circle, text)")) {
                    const style = doc.defaultView.getComputedStyle(part);
                    for (const property of ["fill", "stroke", "stroke-width", "font-size", "font-family"]) {
                        part.style.setProperty(property, style.getPropertyValue(property));
                    }
                }

                const { width, height } = snapshot.getBoundingClientRect();
                // Bound both the canvas dimensions and the amount of pixel memory.
                options.scale = Math.min(1.5, 16000 / Math.max(width, height), Math.sqrt(12_000_000 / (width * height)));
            }
        };
        const canvas = await window.html2canvas(report, options);
        const png = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
        if (!png) throw new Error("Could not encode the PNG");
        const download = document.createElement("a");
        const url = URL.createObjectURL(png);
        download.href = url;
        download.download = `smart-store-${document.body.dataset.section}.png`;
        document.body.append(download);
        download.click();
        download.remove();
        setTimeout(() => URL.revokeObjectURL(url), 30000);
        status.textContent = "";
    } catch {
        status.textContent = "PNG download failed. Try again or choose another format.";
    } finally {
        button.disabled = false;
    }
}

document.getElementById("report-logout")?.addEventListener("click", async event => {
    const button = event.currentTarget;
    const response = await fetch("/api/account/logout", { method: "POST", credentials: "same-origin" }).catch(() => null);
    if (response?.ok) window.location.assign(button.dataset.home);
});

const SVG_NS = "http://www.w3.org/2000/svg";

function svgNode(tag, attrs = {}, text = null) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (text !== null) node.textContent = text;
    return node;
}

/* Line chart without any library. The <figure> says what to plot:
   data-x / data-y: field names, data-money: dollars, data-unit: suffix such as "°C",
   data-time: sensor timestamps (shows HH:MM), data-time-axis: ISO timestamps spaced by time,
   data-empty: text when no data. */
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
    const timeAxis = figure.dataset.timeAxis === "true";
    const positions = data.map((row, index) => timeAxis ? Date.parse(row[figure.dataset.x]) : index);
    const start = positions[0];
    const extent = positions[positions.length - 1] - start;
    const x = index => extent ? 70 + (positions[index] - start) / extent * (right - 70) : (70 + right) / 2;
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
        const stamp = row[figure.dataset.x];
        const detail = timeAxis ? String(stamp).slice(0, 16).replace("T", " ") : label(stamp);
        dot.append(svgNode("title", {}, `${detail}: ${format(row[y])}`));
        svg.append(dot);
    });
    const last = data.length - 1;
    const mid = Math.floor(last / 2);
    const ticks = extent ? [0, last] : [0];
    if (width >= 540 && x(mid) - x(0) >= 90 && x(last) - x(mid) >= 90) ticks.splice(1, 0, mid);
    for (const i of ticks) {
        svg.append(svgNode("text", { x: x(i), y: 242, "text-anchor": !extent ? "middle" : i === 0 ? "start" : i === last ? "end" : "middle" },
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
            // Keep the current results in place while the reader uses the report controls.
            const report = document.getElementById("report-content");
            if (!document.activeElement?.closest?.("#report-content :is(form, details, .screen-pager), #report-content + .screen-pager") &&
                !report.querySelector(".price-history[open], [data-screen-page-active]") &&
                !report.nextElementSibling?.matches(".screen-pager[data-screen-page-active]")) {
                report.replaceChildren(...content.childNodes);
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
