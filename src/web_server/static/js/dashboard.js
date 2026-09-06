const SVG_NS = "http://www.w3.org/2000/svg";
const PALETTE = [
    "#58a6ff", "#f778ba", "#7ee787", "#ffa657",
    "#a5a5ff", "#f2cc60", "#79c0ff", "#3f4a72",
];
const RANGES = [
    {label: "30d", days: 30},
    {label: "90d", days: 90},
    {label: "1y", days: 365},
    {label: "All", days: null},
];
let stats = null;

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

// Dates

function shortDate(day) {
    return new Date(`${day}T00:00:00Z`).toLocaleDateString("en-US", {
        month: "short", day: "numeric", timeZone: "UTC",
    });
}

function longDate(day) {
    return new Date(`${day}T00:00:00Z`).toLocaleDateString("en-US", {
        year: "numeric", month: "short", day: "numeric", timeZone: "UTC",
    });
}

function within(day, days) {
    if (!days) return true;
    return Date.parse(`${day}T00:00:00Z`) >= Date.now() - days * 86400000;
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

    if (!points.length) {
        target.replaceChildren(chart);
        return;
    }

    const x = i => pad.left + (points.length > 1 ? span * (i / (points.length - 1)) : span / 2);
    const y = v => pad.top + plot * (1 - v / max);
    const path = points.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.value)}`).join(" ");

    chart.appendChild(el("path", {
        d: `${path} L${x(points.length - 1)},${height - pad.bottom} L${x(0)},${height - pad.bottom} Z`,
        fill: color, "fill-opacity": "0.12", stroke: "none",
    }));
    chart.appendChild(el("path", {d: path, fill: "none", stroke: color, "stroke-width": "2"}));

    const marker = el("circle", {
        r: 4, fill: color, stroke: "#00031B", "stroke-width": "2",
        "pointer-events": "none", visibility: "hidden",
    });

    const slot = span / points.length;
    points.forEach((p, i) => {
        const hit = el("rect", {
            x: x(i) - slot / 2, y: pad.top, width: slot, height: plot, fill: "transparent",
        });
        hoverable(hit, [p.label, `${comma(p.value)} ${options.unit}`]);
        hit.addEventListener("mouseenter", () => {
            marker.setAttribute("cx", x(i));
            marker.setAttribute("cy", y(p.value));
            marker.setAttribute("visibility", "visible");
        });
        hit.addEventListener("mouseleave", () => marker.setAttribute("visibility", "hidden"));
        chart.appendChild(hit);
    });

    chart.appendChild(marker);
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
    const barWidth = Math.min(60, Math.max(1, (span / Math.max(columns.length, 1)) * 0.7));

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
            hoverable(rect, [`Week of ${longDate(column)}`, `${bucket}: ${comma(value)}`]);
            chart.appendChild(rect);
        });
    });

    drawXLabels(chart, columns.map(shortDate), width, height, pad);

    target.replaceChildren(chart);
}

function arc(cx, cy, outer, inner, from, to) {
    const point = (angle, radius) => [
        cx + radius * Math.cos(angle - Math.PI / 2),
        cy + radius * Math.sin(angle - Math.PI / 2),
    ];
    const large = to - from > Math.PI ? 1 : 0;
    const [x1, y1] = point(from, outer);
    const [x2, y2] = point(to, outer);
    const [x3, y3] = point(to, inner);
    const [x4, y4] = point(from, inner);

    return `M${x1},${y1} A${outer},${outer} 0 ${large} 1 ${x2},${y2}`
        + ` L${x3},${y3} A${inner},${inner} 0 ${large} 0 ${x4},${y4} Z`;
}

function pieChart(target, slices) {
    const size = 220;
    const centre = size / 2;
    const outer = 90;
    const inner = 58;
    const chart = svg(size, size);
    const total = slices.reduce((sum, slice) => sum + slice.value, 0);

    let start = 0;
    slices.forEach((slice, i) => {
        if (!slice.value) return;
        const color = PALETTE[i % PALETTE.length];
        const sweep = total ? (slice.value / total) * Math.PI * 2 : 0;
        // A full turn has identical endpoints, which draws an arc of nothing.
        const shape = slice.value === total
            ? el("circle", {cx: centre, cy: centre, r: (outer + inner) / 2,
                fill: "none", stroke: color, "stroke-width": outer - inner})
            : el("path", {d: arc(centre, centre, outer, inner, start, start + sweep), fill: color});

        hoverable(shape, [slice.label, `${comma(slice.value)} (${percent(slice.value, total)})`]);
        chart.appendChild(shape);
        start += sweep;
    });

    const lead = slices.reduce((a, b) => (b.value > a.value ? b : a), {value: 0, label: ""});
    chart.appendChild(el("text", {class: "pie-value", x: centre, y: centre + 2}, percent(lead.value, total)));
    chart.appendChild(el("text", {class: "pie-label", x: centre, y: centre + 20}, lead.label));

    target.replaceChildren(chart);
}

function clockHour(hour) {
    return `${String(hour).padStart(2, "0")}:00`;
}

function clockChart(target, hours) {
    const size = 260;
    const centre = size / 2;
    const hub = 40;
    const rim = 102;
    const chart = svg(size, size);
    const total = hours.reduce((sum, entry) => sum + entry.commands, 0);
    const max = Math.max(...hours.map(entry => entry.commands), 1);
    const step = (Math.PI * 2) / 24;
    const peak = hours.reduce((a, b) => (b.commands > a.commands ? b : a), hours[0]);

    for (const fraction of [0.5, 1]) {
        chart.appendChild(el("circle", {
            class: "grid-line", cx: centre, cy: centre, fill: "none",
            r: hub + (rim - hub) * fraction,
        }));
    }

    hours.forEach(entry => {
        // Midnight straddles the top of the dial, so each wedge is centred on its own tick.
        const from = entry.hour * step - step / 2;
        const outer = hub + (rim - hub) * (entry.commands / max);

        if (entry.commands) {
            chart.appendChild(el("path", {
                d: arc(centre, centre, outer, hub, from, from + step),
                fill: entry.hour === peak.hour ? "#f2cc60" : "#58a6ff",
                stroke: "#010626", "stroke-width": "0.5", "pointer-events": "none",
            }));
        }

        const hit = el("path", {d: arc(centre, centre, rim, hub, from, from + step), fill: "transparent"});
        hoverable(hit, [
            `${clockHour(entry.hour)} - ${clockHour((entry.hour + 1) % 24)} UTC`,
            `${comma(entry.commands)} commands (${percent(entry.commands, total)})`,
        ]);
        chart.appendChild(hit);
    });

    for (let hour = 0; hour < 24; hour += 3) {
        const angle = hour * step - Math.PI / 2;
        chart.appendChild(el("text", {
            class: "axis-label", "text-anchor": "middle",
            x: centre + (rim + 15) * Math.cos(angle),
            y: centre + (rim + 15) * Math.sin(angle) + 3,
        }, String(hour).padStart(2, "0")));
    }

    chart.appendChild(el("text", {class: "dial-value", x: centre, y: centre + 1}, total ? clockHour(peak.hour) : "--"));
    chart.appendChild(el("text", {class: "dial-label", x: centre, y: centre + 14}, "busiest"));

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

function legend(target, entries) {
    target.replaceChildren(...entries.map((entry, i) => {
        const item = document.createElement("span");
        item.className = "legend-item";

        const swatch = document.createElement("span");
        swatch.className = "legend-swatch";
        swatch.style.backgroundColor = PALETTE[i % PALETTE.length];

        const label = document.createElement("span");
        label.textContent = entry;

        item.append(swatch, label);
        return item;
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
        tile(
            percent(concentration.commands, totals.commands),
            `Top ${concentration.users} users`,
            `${comma(concentration.commands)} commands`,
        ),
    );
}

function renderDaily(days) {
    const rows = stats.daily.filter(d => within(d.day, days));

    lineChart(document.getElementById("daily-chart"), rows.map(d => ({
        label: longDate(d.day), short: shortDate(d.day), value: d.commands,
    })), {unit: "commands"});
}

function renderActive(days) {
    const rows = stats.daily.filter(d => within(d.day, days));

    lineChart(document.getElementById("active-chart"), rows.map(d => ({
        label: longDate(d.day), short: shortDate(d.day), value: d.users,
    })), {unit: "users", color: "#7ee787", height: 220});
}

function renderOrigin() {
    const {totals} = stats;
    const slices = [
        {label: "Servers", value: totals.commands - totals.dm},
        {label: "DMs", value: totals.dm},
    ];

    pieChart(document.getElementById("origin-chart"), slices);
    legend(document.getElementById("origin-legend"), slices.map(s => `${s.label} (${comma(s.value)})`));
}

function renderMix(days) {
    const {weeks, buckets, series} = stats.mix;
    const keep = weeks.map((week, i) => i).filter(i => within(weeks[i], days));

    stackedChart(
        document.getElementById("mix-chart"),
        keep.map(i => weeks[i]),
        buckets,
        Object.fromEntries(buckets.map(b => [b, keep.map(i => series[b][i])])),
    );

    legend(document.getElementById("mix-legend"), buckets);
}

function renderNewUsers(days) {
    const rows = stats.newUsers.filter(r => within(r.week, days));

    stackedChart(
        document.getElementById("new-users-chart"),
        rows.map(r => r.week),
        ["users"],
        {users: rows.map(r => r.users)},
        220,
    );
}

// Ranges

function rangeButtons(id, initial, render) {
    const container = document.getElementById(id);

    container.replaceChildren(...RANGES.map(range => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = range.label;
        if (range.days === initial) button.className = "active";
        button.addEventListener("click", () => {
            container.querySelectorAll("button").forEach(b => b.classList.remove("active"));
            button.classList.add("active");
            if (stats) render(range.days);
        });
        return button;
    }));

    return () => render(initial);
}

const panels = [
    rangeButtons("daily-range", 90, renderDaily),
    rangeButtons("active-range", 90, renderActive),
    rangeButtons("mix-range", 365, renderMix),
    rangeButtons("new-users-range", 365, renderNewUsers),
];

function render() {
    renderTiles();
    renderOrigin();
    clockChart(document.getElementById("clock-chart"), stats.hourly);
    barChart(document.getElementById("top-commands"), stats.topCommands.map(
        row => ({label: row.command, total: row.total}),
    ));
    barChart(document.getElementById("top-servers"), stats.topServers.map(
        row => ({label: `${row.name} (${comma(row.users)} users)`, total: row.total}),
    ));
    panels.forEach(draw => draw());
    document.getElementById("updated").textContent =
        `Read at ${new Date(stats.generated * 1000).toLocaleString()}`;
}

async function load() {
    const response = await fetch("/dashboard/stats");
    if (!response.ok) {
        document.getElementById("updated").textContent = "Session expired. Run -dashboard in Discord.";
        return;
    }

    stats = await response.json();
    render();
}

load();
