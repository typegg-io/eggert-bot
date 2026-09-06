const SVG_NS = "http://www.w3.org/2000/svg";
const PALETTE = [
    "#58a6ff", "#f778ba", "#7ee787", "#ffa657",
    "#a5a5ff", "#f2cc60", "#79c0ff", "#3f4a72",
];
const POLL_MS = 30000;

let stats = null;
let dailyDays = 90;

const tooltip = document.createElement("div");
tooltip.className = "tooltip";
tooltip.hidden = true;
document.body.appendChild(tooltip);

function el(name, attrs, text) {
    const node = document.createElementNS(SVG_NS, name);
    for (const key in attrs) node.setAttribute(key, attrs[key]);
    if (text !== undefined) node.textContent = text;
    return node;
}

function svg(width, height) {
    return el("svg", {viewBox: `0 0 ${width} ${height}`, preserveAspectRatio: "xMidYMid meet"});
}

function comma(n) {
    return n.toLocaleString("en-US");
}

function showTooltip(event, lines) {
    tooltip.replaceChildren(...lines.map(line => {
        const row = document.createElement("div");
        row.textContent = line;
        return row;
    }));
    tooltip.hidden = false;
    tooltip.style.left = `${Math.min(event.clientX + 12, window.innerWidth - tooltip.offsetWidth - 8)}px`;
    tooltip.style.top = `${event.clientY + 12}px`;
}

function hideTooltip() {
    tooltip.hidden = true;
}

function hoverable(node, lines) {
    node.addEventListener("mousemove", event => showTooltip(event, lines));
    node.addEventListener("mouseleave", hideTooltip);
}

// Charts

function niceMax(value) {
    if (value <= 0) return 1;
    const magnitude = 10 ** Math.floor(Math.log10(value));
    return Math.ceil(value / magnitude) * magnitude;
}

function drawGrid(chart, width, height, pad, max, lines = 4) {
    for (let i = 0; i <= lines; i++) {
        const y = pad.top + (height - pad.top - pad.bottom) * (i / lines);
        chart.appendChild(el("line", {
            class: "grid-line", x1: pad.left, x2: width - pad.right, y1: y, y2: y,
        }));
        chart.appendChild(el("text", {
            class: "axis-label", x: pad.left - 6, y: y + 3, "text-anchor": "end",
        }, comma(Math.round(max * (1 - i / lines)))));
    }
}

function drawXLabels(chart, labels, width, height, pad, count = 6) {
    const step = Math.max(1, Math.ceil(labels.length / count));
    const span = width - pad.left - pad.right;
    labels.forEach((label, i) => {
        if (i % step !== 0) return;
        const x = pad.left + (labels.length > 1 ? span * (i / (labels.length - 1)) : span / 2);
        chart.appendChild(el("text", {
            class: "axis-label", x: x, y: height - pad.bottom + 14, "text-anchor": "middle",
        }, label));
    });
}

function lineChart(target, points, options) {
    const width = 900;
    const height = options.height || 260;
    const pad = {top: 10, right: 10, bottom: 24, left: 46};
    const chart = svg(width, height);
    const max = niceMax(Math.max(...points.map(p => p.value), 0));
    const span = width - pad.left - pad.right;
    const plot = height - pad.top - pad.bottom;
    const color = options.color || "#58a6ff";

    drawGrid(chart, width, height, pad, max);

    const x = i => pad.left + (points.length > 1 ? span * (i / (points.length - 1)) : span / 2);
    const y = v => pad.top + plot * (1 - v / max);
    const path = points.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.value)}`).join(" ");

    chart.appendChild(el("path", {
        d: `${path} L${x(points.length - 1)},${height - pad.bottom} L${x(0)},${height - pad.bottom} Z`,
        fill: color, "fill-opacity": "0.12", stroke: "none",
    }));
    chart.appendChild(el("path", {d: path, fill: "none", stroke: color, "stroke-width": "2"}));

    const slot = span / points.length;
    points.forEach((p, i) => {
        const hit = el("rect", {
            x: x(i) - slot / 2, y: pad.top, width: slot, height: plot, fill: "transparent",
        });
        hoverable(hit, [p.label, `${comma(p.value)} ${options.unit}`]);
        chart.appendChild(hit);
    });

    drawXLabels(chart, points.map(p => p.short), width, height, pad);

    target.replaceChildren(chart);
}

function stackedChart(target, columns, buckets, series, height = 280) {
    const width = 900;
    const pad = {top: 10, right: 10, bottom: 24, left: 46};
    const chart = svg(width, height);
    const totals = columns.map((_, i) => buckets.reduce((sum, b) => sum + series[b][i], 0));
    const max = niceMax(Math.max(...totals, 0));
    const span = width - pad.left - pad.right;
    const plot = height - pad.top - pad.bottom;
    const barWidth = Math.max(1, (span / Math.max(columns.length, 1)) * 0.7);

    drawGrid(chart, width, height, pad, max);

    columns.forEach((column, i) => {
        const center = pad.left + span * ((i + 0.5) / columns.length);
        let bottom = height - pad.bottom;

        buckets.forEach((bucket, b) => {
            const value = series[bucket][i];
            if (!value) return;
            const barHeight = plot * (value / max);
            bottom -= barHeight;
            const rect = el("rect", {
                x: center - barWidth / 2, y: bottom, width: barWidth, height: barHeight,
                fill: PALETTE[b % PALETTE.length],
            });
            hoverable(rect, [column, `${bucket}: ${comma(value)}`]);
            chart.appendChild(rect);
        });
    });

    drawXLabels(chart, columns, width, height, pad);

    target.replaceChildren(chart);
}

function barChart(target, rows) {
    const max = Math.max(...rows.map(r => r.total), 1);

    target.replaceChildren(...rows.map(row => {
        const line = document.createElement("div");
        line.className = "bar-row";

        const name = document.createElement("span");
        name.className = "bar-name";
        name.textContent = row.label;
        name.title = row.label;

        const track = document.createElement("div");
        track.className = "bar-track";
        const fill = document.createElement("div");
        fill.className = "bar-fill";
        fill.style.width = `${(row.total / max) * 100}%`;
        track.appendChild(fill);

        const value = document.createElement("span");
        value.className = "bar-value";
        value.textContent = comma(row.total);

        line.append(name, track, value);
        return line;
    }));
}

// Panels

function tile(value, label, note) {
    const node = document.createElement("div");
    node.className = "tile";

    for (const [className, text] of [["tile-value", value], ["tile-label", label], ["tile-note", note]]) {
        const child = document.createElement("div");
        child.className = className;
        child.textContent = text;
        node.appendChild(child);
    }

    return node;
}

function percent(part, whole) {
    return whole ? `${((part / whole) * 100).toFixed(1)}%` : "0%";
}

function renderTiles() {
    const {totals, active, concentration} = stats;
    const recent = stats.daily.slice(-30);
    const perDay = recent.length
        ? Math.round(recent.reduce((sum, d) => sum + d.commands, 0) / recent.length)
        : 0;

    document.getElementById("tiles").replaceChildren(
        tile(comma(totals.commands), "Commands run", `${totals.distinctCommands} distinct commands`),
        tile(comma(totals.users), "Users", `${comma(active.month)} active this month`),
        tile(comma(perDay), "Commands per day", "30 day average"),
        tile(percent(active.day, active.month), "Stickiness", "DAU / MAU"),
        tile(percent(totals.linked, totals.commands), "From linked users", `${comma(totals.linked)} commands`),
        tile(percent(totals.dm, totals.commands), "Run in DMs", `${comma(totals.commands - totals.dm)} in servers`),
        tile(
            percent(concentration.commands, totals.commands),
            `Top ${concentration.users} users`,
            `${comma(concentration.commands)} commands`,
        ),
    );
}

function shortDay(day) {
    return day.slice(5).replace("-", "/");
}

function renderDaily() {
    const rows = stats.daily.slice(-dailyDays);

    lineChart(document.getElementById("daily-chart"), rows.map(d => ({
        label: d.day, short: shortDay(d.day), value: d.commands,
    })), {unit: "commands"});

    lineChart(document.getElementById("active-chart"), rows.map(d => ({
        label: d.day, short: shortDay(d.day), value: d.users,
    })), {unit: "users", color: "#7ee787", height: 220});
}

function renderMix() {
    const {weeks, buckets, series} = stats.mix;
    stackedChart(document.getElementById("mix-chart"), weeks, buckets, series);

    document.getElementById("mix-legend").replaceChildren(...buckets.map((bucket, i) => {
        const item = document.createElement("span");
        item.className = "legend-item";

        const swatch = document.createElement("span");
        swatch.className = "legend-swatch";
        swatch.style.backgroundColor = PALETTE[i % PALETTE.length];

        const label = document.createElement("span");
        label.textContent = bucket;

        item.append(swatch, label);
        return item;
    }));
}

function renderNewUsers() {
    stackedChart(
        document.getElementById("new-users-chart"),
        stats.newUsers.map(r => r.week),
        ["users"],
        {users: stats.newUsers.map(r => r.users)},
        220,
    );
}

function render() {
    renderTiles();
    renderDaily();
    barChart(document.getElementById("top-commands"), stats.topCommands.map(
        row => ({label: row.command, total: row.total}),
    ));
    barChart(document.getElementById("top-servers"), stats.topServers.map(
        row => ({label: `${row.name} (${comma(row.users)} users)`, total: row.total}),
    ));
    renderMix();
    renderNewUsers();
    document.getElementById("updated").textContent =
        `Updated ${new Date(stats.generated * 1000).toLocaleTimeString()}`;
}

// Polling

async function refresh() {
    const response = await fetch("/dashboard/stats");
    if (!response.ok) {
        document.getElementById("updated").textContent = "Session expired. Run -dashboard in Discord.";
        return false;
    }

    stats = await response.json();
    render();
    return true;
}

document.getElementById("range-buttons").addEventListener("click", event => {
    const button = event.target.closest("button");
    if (!button || !stats) return;

    dailyDays = Number(button.dataset.days);
    document.querySelectorAll("#range-buttons button")
        .forEach(b => b.classList.toggle("active", b === button));
    renderDaily();
});

refresh().then(ok => {
    if (ok) setInterval(refresh, POLL_MS);
});
