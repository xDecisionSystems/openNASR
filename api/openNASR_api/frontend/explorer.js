"use strict";

const byId = (id) => document.getElementById(id);
const cycle = byId("cycle");
const status = byId("status");
const results = byId("results");
const canvas = byId("plot");
const form = byId("query-form");
const tabs = [...document.querySelectorAll("[role=tab]")];

const views = {
  airports: {
    title: "Find an airport",
    help: "Enter an FAA or ICAO airport identifier.",
    fields: [{ name: "identifier", label: "Airport identifier", example: "KABQ" }],
    caption: "Query an airport to plot its position.",
  },
  airspace: {
    title: "Find airspace at a point",
    help: "Enter latitude and longitude in decimal degrees.",
    fields: [
      { name: "lat", label: "Latitude", example: "35.0402", min: -90, max: 90 },
      { name: "lon", label: "Longitude", example: "-106.609", min: -180, max: 180 },
    ],
    caption: "The plot shows the query point. Matching regions appear below.",
  },
  routes: {
    title: "Resolve a route",
    help: "Enter an FAA route string to see its waypoints and diagnostics.",
    fields: [{ name: "route", label: "Flight plan route", example: "KABQ.DOOKK3.TXO..KTYR", multiline: true }],
    caption: "Resolved waypoints will appear here in flight order.",
  },
  arrivals: {
    title: "Find an arrival",
    help: "Enter a STAR name or computer code.",
    fields: [{ name: "identifier", label: "Arrival identifier", example: "GRNCH5" }],
    caption: "Published arrival branches and their point sequences appear below.",
  },
  departures: {
    title: "Find a departure",
    help: "Enter a departure procedure name or computer code.",
    fields: [{ name: "identifier", label: "Departure identifier", example: "DOOKK3" }],
    caption: "Published departure branches and their point sequences appear below.",
  },
};

let currentView = "airports";
let apiKey = "";
let request = null;
let cycleRequest = 0;
let plotPoints = [];
let partialRoute = false;
const savedInputs = new Map();
const savedResults = new Map();

function element(tag, text, cssClass) {
  const item = document.createElement(tag);
  if (text != null) item.textContent = text;
  if (cssClass) item.className = cssClass;
  return item;
}

async function api(path, options = {}) {
  const { headers, ...rest } = options;
  const response = await fetch(path, {
    ...rest,
    headers: { ...(apiKey ? { "X-API-Key": apiKey } : {}), ...headers },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) throw new Error("Enter your API key above and try again.");
    const detail = body.detail;
    throw new Error(typeof detail === "string" ? detail : `Request failed (HTTP ${response.status}).`);
  }
  return body;
}

async function loadCycles() {
  const load = ++cycleRequest;
  try {
    const data = await api("/v1/cycles");
    if (load !== cycleRequest) return;
    const selected = cycle.value;
    cycle.replaceChildren(new Option(data.default ? `In effect · ${data.default}` : "In effect", ""));
    for (const item of [...data.cycles].reverse()) {
      cycle.add(new Option(item.effective_date + (item.in_effect ? "" : " · upcoming"), item.effective_date));
    }
    if ([...cycle.options].some((option) => option.value === selected)) cycle.value = selected;
  } catch (error) {
    if (load === cycleRequest) setStatus(error.message, true);
  }
}

function setStatus(message, failed = false) {
  status.textContent = message;
  status.classList.toggle("error", failed);
}

function setView(name) {
  if (!views[name]) return;
  if (byId("fields").children.length) savedInputs.set(currentView, new FormData(form));
  request?.abort();
  currentView = name;
  const view = views[name];
  for (const tab of tabs) {
    const active = tab.dataset.tab === name;
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
  }
  byId("query-panel").setAttribute("aria-labelledby", `tab-${name}`);
  byId("query-title").textContent = view.title;
  byId("query-help").textContent = view.help;
  byId("example").textContent = `Try ${view.fields.map((field) => field.example).join(", ")}`;
  byId("plot-caption").textContent = view.caption;
  byId("fields").replaceChildren(...view.fields.map((field) => {
    const group = element("div");
    const label = element("label", field.label);
    label.htmlFor = `query-${field.name}`;
    const input = element(field.multiline ? "textarea" : "input");
    input.id = label.htmlFor;
    input.name = field.name;
    input.placeholder = field.example;
    input.value = savedInputs.get(name)?.get(field.name) || "";
    input.required = true;
    input.spellcheck = false;
    if (field.min != null) {
      input.type = "number";
      input.min = field.min;
      input.max = field.max;
      input.step = "any";
    } else {
      input.maxLength = field.multiline ? 4096 : 80;
      input.autocomplete = "off";
    }
    group.append(label, input);
    return group;
  }));
  resetResult();
  if (savedResults.has(name)) showResult(savedResults.get(name));
}

function resetResult() {
  setStatus("");
  byId("submit").disabled = false;
  results.replaceChildren(element("p", "Results will appear here after a query.", "empty"));
  byId("result-cycle").textContent = "";
  plotPoints = [];
  partialRoute = false;
  byId("plot-note").textContent = "WGS 84";
  canvas.setAttribute("aria-label", "Latitude and longitude grid");
  byId("plot-caption").textContent = views[currentView].caption;
  drawPlot();
}

function table(title, labels, rows) {
  const section = element("section", null, "result-block");
  section.append(element("h3", title));
  if (!rows.length) {
    section.append(element("p", "No records returned.", "empty"));
    return section;
  }
  const scroll = element("div", null, "table-scroll");
  const grid = element("table");
  const head = grid.createTHead().insertRow();
  for (const label of labels) {
    const column = element("th", label);
    column.scope = "col";
    head.append(column);
  }
  const body = grid.createTBody();
  for (const values of rows) {
    const row = body.insertRow();
    for (const value of values) row.insertCell().textContent = value || "—";
  }
  scroll.append(grid);
  section.append(scroll);
  return section;
}

function facts(values) {
  const list = element("dl", null, "facts");
  for (const [title, value] of values) {
    if (!value) continue;
    const group = element("div");
    group.append(element("dt", title), element("dd", value));
    list.append(group);
  }
  return list;
}

const coordinates = (point) => point ? `${point.lat.toFixed(4)}, ${point.lon.toFixed(4)}` : "";
const altitude = (limit) => limit ? [limit.value, limit.unit, limit.code].filter(Boolean).join(" ") : "";

function showResult(data) {
  byId("result-cycle").textContent = `Cycle ${data.cycle}`;
  results.replaceChildren();
  if (currentView === "airports") {
    const airport = data.airport;
    const base = airport.base;
    results.append(
      element("h3", base.ARPT_NAME || airport.icao_id || airport.id, "result-title"),
      facts([
        ["Airport", airport.icao_id || airport.id], ["City", [base.CITY, base.STATE_CODE].filter(Boolean).join(", ")],
        ["Position", coordinates(airport.position)], ["Elevation", base.ELEV && `${base.ELEV} ft`],
      ]),
      table("Runways", ["Runway", "Length (ft)", "Width (ft)", "Surface"], airport.runways.map(
        (row) => [row.RWY_ID, row.RWY_LEN, row.RWY_WIDTH, row.SURFACE_TYPE_CODE],
      )),
    );
    plotPoints = airport.position ? [{ ...airport.position, name: airport.icao_id || airport.id }] : [];
  } else if (currentView === "airspace") {
    results.append(
      table("Matching regions", ["Region", "Type", "Lower", "Upper"], data.regions.map(
        (row) => [row.name || row.id, row.local_type || [row.kind, row.level].filter(Boolean).join(" · "), altitude(row.lower), altitude(row.upper)],
      )),
      element("p", data.not_covered, "coverage"),
    );
    plotPoints = [{ ...data.position, name: "Query point" }];
  } else if (currentView === "routes") {
    plotPoints = data.points;
    partialRoute = !data.complete;
    results.append(
      element("h3", data.complete ? "Complete route" : "Partial route", "result-title"),
      table("Waypoints", ["Name", "Position", "Segment", "Via"], data.points.map(
        (point) => [point.name || point.kind, coordinates(point), point.segment, point.via],
      )),
    );
    if (data.diagnostics.length) results.append(table("Diagnostics", ["Severity", "Token", "Message"],
      data.diagnostics.map((note) => [note.severity, note.token, note.message])));
  } else {
    for (const procedure of data.procedures) {
      const section = element("section", null, "result-block");
      section.append(
        element("h3", procedure.name === procedure.id ? procedure.id : `${procedure.id} · ${procedure.name}`, "result-title"),
        facts([["ARTCC", procedure.base.ARTCC], ["Airports", [...new Set(
          procedure.airports.map((row) => row.ARPT_ID).filter(Boolean),
        )].join(", ") || procedure.base.SERVED_ARPT]]),
        table("Published points", ["Branch", "Transition", "Sequence", "Point"], procedure.points.map(
          (row) => [[row.ROUTE_PORTION_TYPE, row.ROUTE_NAME].filter(Boolean).join(" · "),
            row.TRANSITION_COMPUTER_CODE, row.POINT_SEQ, row.POINT],
        )),
      );
      results.append(section);
    }
  }
  const raw = element("details", null, "raw");
  raw.append(element("summary", "View response JSON"), element("pre", JSON.stringify(data, null, 2)));
  results.append(raw);
  if (plotPoints.length) {
    const label = plotPoints.length === 1
      ? `${plotPoints[0].name || "Position"} · ${coordinates(plotPoints[0])}`
      : `${plotPoints.length} waypoints${partialRoute ? " · partial route" : ""}`;
    byId("plot-caption").textContent = label;
    canvas.setAttribute("aria-label", label);
  }
  drawPlot();
}

function drawPlot() {
  const rect = canvas.getBoundingClientRect();
  const pixelRatio = window.devicePixelRatio || 1;
  if (!rect.width || !rect.height) return;
  canvas.width = Math.round(rect.width * pixelRatio);
  canvas.height = Math.round(rect.height * pixelRatio);
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.scale(pixelRatio, pixelRatio);
  const width = rect.width, height = rect.height;
  const padding = 34;
  const points = plotPoints.filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lon));
  const reference = points[0]?.lon || 0;
  const outline = points.map((point) => ({
    ...point,
    x: reference + ((point.lon - reference + 540) % 360) - 180,
  }));
  const west = Math.min(...outline.map((point) => point.x));
  const east = Math.max(...outline.map((point) => point.x));
  const south = Math.min(...outline.map((point) => point.lat));
  const north = Math.max(...outline.map((point) => point.lat));
  const centerX = points.length ? (west + east) / 2 : -98;
  const centerY = points.length ? (south + north) / 2 : 38;
  const longitudeFactor = Math.max(.17, Math.cos(centerY * Math.PI / 180));
  const scale = points.length ? Math.min(
    (width - 2 * padding) / Math.max((east - west) * longitudeFactor, 1),
    (height - 2 * padding) / Math.max(north - south, 1),
  ) : Math.max(4, width / 90);
  const xy = (lon, lat) => [
    width / 2 + (lon - centerX) * scale * longitudeFactor,
    height / 2 - (lat - centerY) * scale,
  ];
  const gridStep = (pixels) => [0.25, 0.5, 1, 2, 5, 10, 20, 30].find(
    (step) => step * pixels >= 54,
  ) || 60;
  const lonStep = gridStep(scale * longitudeFactor);
  const latStep = gridStep(scale);
  ctx.strokeStyle = "#355264";
  ctx.fillStyle = "#8dafbd";
  ctx.font = "10px system-ui";
  const lonStart = centerX - width / (2 * scale * longitudeFactor);
  const lonEnd = centerX + width / (2 * scale * longitudeFactor);
  for (let lon = Math.ceil(lonStart / lonStep) * lonStep; lon <= lonEnd; lon += lonStep) {
    const [x] = xy(lon, centerY);
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke();
    if (x > 26 && x < width - 40) ctx.fillText(`${((lon + 540) % 360) - 180}°`, x + 4, 13);
  }
  const latStart = centerY - height / (2 * scale);
  const latEnd = centerY + height / (2 * scale);
  for (let lat = Math.ceil(latStart / latStep) * latStep; lat <= latEnd; lat += latStep) {
    const [, y] = xy(centerX, lat);
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
    if (y > 26 && y < height - 22) ctx.fillText(`${lat}°`, 5, y - 4);
  }
  // Dashes indicate a partial result whose published geometry has gaps.
  ctx.strokeStyle = "#76dfca";
  ctx.lineWidth = 2;
  ctx.setLineDash(partialRoute ? [5, 5] : []);
  ctx.beginPath();
  outline.forEach((point, index) => {
    const [x, y] = xy(point.x, point.lat);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  outline.forEach((point) => {
    const [x, y] = xy(point.x, point.lat);
    ctx.fillStyle = "#b8f6e7";
    ctx.beginPath(); ctx.arc(x, y, 3.5, 0, Math.PI * 2); ctx.fill();
  });
  const labels = [];
  const labelOrder = [outline[0], outline.at(-1), ...outline.slice(1, -1)];
  for (const point of new Set(labelOrder)) {
    if (!point?.name) continue;
    const [x, y] = xy(point.x, point.lat);
    const textWidth = ctx.measureText(point.name).width;
    const left = x + 7 + textWidth < width ? x + 7 : x - textWidth - 7;
    const top = Math.max(17, y - 17);
    const right = left + textWidth;
    if (labels.some((label) => left < label.right + 4 && right + 4 > label.left
        && Math.abs(top - label.top) < 13)) continue;
    labels.push({ left, right, top });
    ctx.fillText(point.name, left, top + 10);
  }
}

async function submit(event) {
  event.preventDefault();
  request?.abort();
  const activeRequest = new AbortController();
  request = activeRequest;
  const queriedView = currentView;
  savedResults.delete(queriedView);
  const values = Object.fromEntries(new FormData(form));
  const params = new URLSearchParams();
  if (cycle.value) params.set("cycle", cycle.value);
  let url, options = { signal: activeRequest.signal };
  if (currentView === "routes") {
    const body = { route: values.route.trim() };
    if (cycle.value) body.cycle = cycle.value;
    url = "/v1/route/resolve";
    options = { ...options, method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body) };
  } else if (currentView === "airspace") {
    params.set("lat", values.lat);
    params.set("lon", values.lon);
    url = `/v1/airspace/at?${params}`;
  } else {
    url = `/v1/${currentView}/${encodeURIComponent(values.identifier.trim())}?${params}`;
  }
  resetResult();
  setStatus("Searching…");
  byId("submit").disabled = true;
  try {
    const data = await api(url, options);
    if (!activeRequest.signal.aborted) {
      savedResults.set(queriedView, data);
      showResult(data);
      setStatus("Results shown below.");
    }
  } catch (error) {
    if (error.name !== "AbortError") setStatus(error.message, true);
  } finally {
    if (request === activeRequest) byId("submit").disabled = false;
  }
}

tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => setView(tab.dataset.tab));
  tab.addEventListener("keydown", (event) => {
    const next = { ArrowRight: (index + 1) % tabs.length,
      ArrowLeft: (index + tabs.length - 1) % tabs.length, Home: 0, End: tabs.length - 1 }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    tabs[next].focus();
    setView(tabs[next].dataset.tab);
  });
});
form.addEventListener("submit", submit);
cycle.addEventListener("change", () => {
  request?.abort();
  savedResults.clear();
  resetResult();
});
byId("example").addEventListener("click", () => {
  for (const field of views[currentView].fields) form.elements[field.name].value = field.example;
  form.requestSubmit();
});
byId("apply-key").addEventListener("click", () => {
  apiKey = byId("api-key").value.trim();
  byId("api-key").value = "";
  byId("apply-key").closest("details").open = false;
  request?.abort();
  savedResults.clear();
  resetResult();
  loadCycles();
});
new ResizeObserver(drawPlot).observe(canvas.parentElement);
setView(currentView);
loadCycles();
