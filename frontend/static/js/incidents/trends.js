(() => {
  "use strict";
  const panel = document.querySelector("[data-incident-trends]");
  if (!panel) return;
  const chart = panel.querySelector("[data-trend-chart]");
  const table = panel.querySelector("[data-trend-table]");
  const range = panel.querySelector("[data-trend-range]");
  const summary = panel.querySelector("[data-trend-summary]");
  const namespace = "http://www.w3.org/2000/svg";
  let pending = false;

  function svgElement(name, attributes = {}) {
    const node = document.createElementNS(namespace, name);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value)));
    return node;
  }

  function renderChart(series) {
    if (!chart) return;
    chart.replaceChildren();
    const width = 760;
    const height = 250;
    const margin = { top: 18, right: 20, bottom: 42, left: 38 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const maximum = Math.max(1, ...series.map((item) => item.count));
    const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": "Daily incident report volume" });
    const axis = svgElement("path", { d: `M ${margin.left} ${margin.top} V ${height - margin.bottom} H ${width - margin.right}`, class: "trend-axis" });
    svg.append(axis);
    const points = [];
    series.forEach((item, index) => {
      const x = margin.left + (series.length <= 1 ? plotWidth / 2 : index * plotWidth / (series.length - 1));
      const y = margin.top + plotHeight - (item.count / maximum) * plotHeight;
      points.push([x, y]);
      const barWidth = Math.max(3, Math.min(12, plotWidth / Math.max(series.length, 1) * 0.58));
      const bar = svgElement("rect", { x: x - barWidth / 2, y, width: barWidth, height: Math.max(1, height - margin.bottom - y), rx: 3, class: "trend-bar" });
      const title = svgElement("title");
      title.textContent = `${item.date}: ${item.count} reports`;
      bar.append(title);
      svg.append(bar);
    });
    if (points.length > 1) {
      const path = points.map(([x, y], index) => `${index ? "L" : "M"} ${x} ${y}`).join(" ");
      svg.append(svgElement("path", { d: path, class: "trend-line" }));
    }
    points.forEach(([x, y]) => svg.append(svgElement("circle", { cx: x, cy: y, r: 3.5, class: "trend-point" })));
    [0, 0.5, 1].forEach((fraction) => {
      const y = margin.top + plotHeight * fraction;
      const value = Math.round(maximum * (1 - fraction));
      svg.append(svgElement("line", { x1: margin.left, y1: y, x2: width - margin.right, y2: y, class: "trend-gridline" }));
      const label = svgElement("text", { x: 5, y: y + 4, class: "trend-axis-label" });
      label.textContent = String(value);
      svg.append(label);
    });
    chart.append(svg);
  }

  function renderTable(series) {
    if (!table) return;
    table.replaceChildren();
    const heading = document.createElement("caption");
    heading.textContent = "Daily community incident report counts";
    table.append(heading);
    const head = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["Date", "Reports"].forEach((label) => {
      const cell = document.createElement("th");
      cell.scope = "col";
      cell.textContent = label;
      headerRow.append(cell);
    });
    head.append(headerRow);
    const body = document.createElement("tbody");
    series.forEach((item) => {
      const row = document.createElement("tr");
      const day = document.createElement("th");
      day.scope = "row";
      day.textContent = item.date;
      const count = document.createElement("td");
      count.textContent = String(item.count);
      row.append(day, count);
      body.append(row);
    });
    table.append(head, body);
  }

  function renderSummary(data) {
    if (!summary) return;
    summary.replaceChildren();
    const values = [
      ["Period change", `${data.period_comparison.change_percent}%`],
      ["Severity-weighted signal", data.severity_weighted.score],
      ["Resolution rate", `${data.resolution.rate_percent}%`],
      ["Average daily volume", data.severity_weighted.average_per_day],
    ];
    values.forEach(([label, value]) => {
      const tile = document.createElement("div");
      tile.className = "trend-summary-tile";
      const title = document.createElement("span");
      title.textContent = label;
      const number = document.createElement("strong");
      number.textContent = String(value);
      tile.append(title, number);
      summary.append(tile);
    });
  }

  async function load() {
    if (pending) return;
    pending = true;
    const days = Number(range?.value || 30);
    panel.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(`/incidents/api/trends?days=${encodeURIComponent(days)}`, { headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Trend data unavailable.");
      renderChart(payload.trends.daily_volume);
      renderTable(payload.trends.daily_volume);
      renderSummary(payload.trends);
    } catch (error) {
      if (chart) chart.textContent = error.message || "Trend data unavailable.";
    } finally {
      pending = false;
      panel.removeAttribute("aria-busy");
    }
  }
  range?.addEventListener("change", load);
  load();
})();
