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
    caption: "Query an airport to plot its runways, helipads, and ILS localizers.",
  },
  airspace: {
    title: "Find airspace at a point",
    help: "Enter latitude and longitude in decimal degrees.",
    fields: [
      { name: "lat", label: "Latitude", example: "35.0402", min: -90, max: 90 },
      { name: "lon", label: "Longitude", example: "-106.609", min: -180, max: 180 },
    ],
    caption: "All ARTCC boundaries. Search a point to focus the map.",
  },
  flightplan: {
    title: "Resolve a flight plan",
    help: "Enter an FAA route string to see its waypoints and diagnostics.",
    fields: [{ name: "route", label: "Flight plan route", example: "KABQ.DOOKK3.TXO..KTYR", multiline: true }],
    caption: "Resolved waypoints will appear here in flight order.",
  },
  routes: {
    title: "Find a jetway or airway",
    help: "Enter a published route designation such as J74 or V12.",
    fields: [{ name: "identifier", label: "Route designation", example: "J74" }],
    caption: "Query a jetway or airway to plot its published segments.",
  },
  arrivals: {
    title: "Find an arrival",
    help: "Enter a STAR name or computer code.",
    fields: [{ name: "identifier", label: "Arrival identifier", example: "GRNCH5" }],
    caption: "Query an arrival to plot its published branches.",
  },
  departures: {
    title: "Find a departure",
    help: "Enter a departure procedure name or computer code.",
    fields: [{ name: "identifier", label: "Departure identifier", example: "DOOKK3" }],
    caption: "Query a departure to plot its published branches.",
  },
};

let currentView = "airports";
let apiKey = "";
let request = null;
let cycleRequest = 0;
let plotPoints = [];
let plotBranches = [];
let partialRoute = false;
let plotZoom = 1;
let plotPan = { x: 0, y: 0 };
let printing = false;
let airportCaption = "";
let airspaceMap = null;
let airportProcedureRequest = null;
const ilsPlotNote = "ILS course wedges are illustrative · 700 ft at the runway end · ±2.5° · 20 NM.";
const airspaceLayers = [
  ["airports", "Airports", "#ffcb81"],
  ["departures", "Departures", "#87ddbf"],
  ["arrivals", "Arrivals", "#ffa7d4"],
  ["airways", "Jetways / airways", "#9bbaff"],
];
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
  else if (name === "airspace") loadAirspaceOverview();
}

function resetResult() {
  setStatus("");
  byId("submit").disabled = false;
  results.replaceChildren(element("p", "Results will appear here after a query.", "empty"));
  byId("result-cycle").textContent = "";
  plotPoints = [];
  plotBranches = [];
  partialRoute = false;
  setAreaSelection(false);
  plotZoom = 1;
  plotPan = { x: 0, y: 0 };
  airportCaption = "";
  airspaceMap?.controller.abort();
  airspaceMap = null;
  airportProcedureRequest?.abort();
  const airportLayers = byId("airport-procedure-layers");
  airportLayers.hidden = true;
  airportLayers.replaceChildren();
  const procedures = currentView === "arrivals" || currentView === "departures";
  canvas.closest(".plot-card").classList.toggle("procedure-plot", procedures);
  canvas.closest(".plot-card").classList.toggle("airspace-plot", currentView === "airspace");
  canvas.closest(".plot-card").classList.remove("ils-plot");
  byId("ils-toggle").hidden = true;
  byId("ils-wedges").checked = true;
  byId("plot-title").textContent = {
    airports: "Airport layout", airspace: "ARTCC boundaries", arrivals: "Procedure branches", departures: "Procedure branches",
  }[currentView] || "Coordinate plot";
  byId("plot-legend").hidden = true;
  byId("plot-legend").replaceChildren();
  byId("airspace-layers").hidden = true;
  byId("airspace-layers").replaceChildren();
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
const branchColors = ["#76dfca", "#ffc277", "#91bdff", "#ff9fca", "#d6ed91", "#bfb1ff", "#ffa299", "#76c8ef"];
const branchName = (branch) => branch.name || branch.transition || branch.kind || "Published branch";

function addProcedureBranches(procedure, multipleProcedures) {
  const section = element("section", null, "result-block");
  section.append(
    element("h3", procedure.name === procedure.id ? procedure.id : `${procedure.id} · ${procedure.name}`, "result-title"),
    facts([["ARTCC", procedure.base.ARTCC], ["Airports", [...new Set(
      procedure.airports.map((row) => row.ARPT_ID).filter(Boolean),
    )].join(", ") || procedure.base.SERVED_ARPT]]),
  );
  for (const branch of procedure.branches) {
    const label = branchName(branch);
    const repeated = procedure.branches.some((other) => other !== branch && branchName(other) === label);
    const legendLabel = [multipleProcedures ? procedure.id : "", label, repeated ? branch.sequence : ""]
      .filter(Boolean).join(" · ");
    const points = branch.waypoints.map((waypoint) => waypoint.position
      ? { ...waypoint.position, name: waypoint.name } : null);
    const color = branchColors[plotBranches.length % branchColors.length];
    const plotBranch = { points, color, visible: true };
    plotBranches.push(plotBranch);
    const button = element("button", legendLabel);
    const swatch = element("span", null, "branch-color");
    swatch.style.backgroundColor = color;
    swatch.setAttribute("aria-hidden", "true");
    button.prepend(swatch);
    button.type = "button";
    button.setAttribute("aria-pressed", "true");
    button.addEventListener("click", () => {
      plotBranch.visible = !plotBranch.visible;
      button.setAttribute("aria-pressed", String(plotBranch.visible));
      drawPlot();
    });
    byId("plot-legend").append(button);
    section.append(table(legendLabel, ["Sequence", "Waypoint", "Position"], branch.waypoints.map(
      (point) => [point.sequence, point.name, point.position ? coordinates(point.position) : point.issue],
    )));
  }
  if (!procedure.branches.length) section.append(element("p", "No published waypoints.", "empty"));
  results.append(section);
}

function addAirportLayout(airport) {
  const endsByRunway = new Map();
  for (const end of airport.runway_ends) {
    const lat = Number(end.LAT_DECIMAL);
    const lon = Number(end.LONG_DECIMAL);
    if (!end.LAT_DECIMAL?.trim() || !end.LONG_DECIMAL?.trim()
      || !Number.isFinite(lat) || Math.abs(lat) > 90
      || !Number.isFinite(lon) || Math.abs(lon) > 180) continue;
    if (!endsByRunway.has(end.RWY_ID)) endsByRunway.set(end.RWY_ID, new Map());
    endsByRunway.get(end.RWY_ID).set(end.RWY_END_ID, { lat, lon, name: end.RWY_END_ID });
  }

  const runwayRows = [];
  const padRows = [];
  for (const row of airport.runways) {
    const id = row.RWY_ID || "";
    const ends = endsByRunway.get(id);
    const pad = /^H(?:\d+[A-Z]?|-?[A-Z])$/i.test(id);
    const points = pad ? [ends?.get(id)] : id.split("/").map((end) => ends?.get(end));
    const canPlot = points.every(Boolean) && (pad || (points.length === 2
      && (points[0].lat !== points[1].lat || points[0].lon !== points[1].lon)));
    if (canPlot) {
      plotBranches.push({ points, kind: pad ? "pad" : "runway", color: pad ? "#ffc277" : "#b8f6e7", visible: true });
    }
    (pad ? padRows : runwayRows).push([
      id, row.RWY_LEN, row.RWY_WIDTH, row.SURFACE_TYPE_CODE,
      canPlot ? "Plotted" : "Geometry unavailable",
    ]);
  }
  const columns = ["Identifier", "Length (ft)", "Width (ft)", "Surface", "Map"];
  results.append(table("Runways", columns, runwayRows), table("Helipads", columns, padRows));

  const runwayCount = plotBranches.filter((branch) => branch.kind === "runway").length;
  const padCount = plotBranches.length - runwayCount;
  const unavailable = airport.runways.length - plotBranches.length;
  if (!plotBranches.length && airport.position) {
    plotBranches.push({
      points: [{ ...airport.position, name: airport.icao_id || airport.id }],
      color: "#b8f6e7", visible: true,
    });
  }
  const hasReference = plotBranches.some((branch) => !branch.kind);
  airportCaption = [
    `${runwayCount} of ${runwayRows.length} runways and ${padCount} of ${padRows.length} helipads plotted.`,
    unavailable ? "Some records lack usable geometry." : "",
    hasReference ? "Showing the airport reference point." : "",
  ].filter(Boolean).join(" ");
  byId("plot-caption").textContent = airportCaption;
  canvas.setAttribute("aria-label", airportCaption);

  const localizers = airport.localizers.map((row) => {
    const name = [row.id || "Localizer", row.runway_end && `RWY ${row.runway_end}`].filter(Boolean).join(" · ");
    if (row.position || row.wedge.length) {
      plotBranches.push({
        points: row.position ? [{ ...row.position, name }] : [],
        wedge: row.wedge, kind: "localizer", color: "#ffc0ee", visible: true,
      });
    }
    return [row.id, row.runway_end, coordinates(row.position),
      row.wedge.length ? "Plotted" : "Geometry unavailable"];
  });
  results.append(table("ILS localizers", ["Identifier", "Runway", "Transmitter position", "Course wedge"], localizers));
  if (airport.localizers.some((row) => row.wedge.length)) {
    canvas.closest(".plot-card").classList.add("ils-plot");
    byId("ils-toggle").hidden = false;
  }
}

function addAirportProcedureLayers(airport, selectedCycle) {
  const controller = new AbortController();
  airportProcedureRequest = controller;
  const controls = byId("airport-procedure-layers");
  controls.hidden = false;
  const identifier = encodeURIComponent(airport.icao_id || airport.id);
  for (const [kind, name, color] of airspaceLayers.filter(([kind]) => kind === "arrivals" || kind === "departures")) {
    const checkbox = element("input");
    checkbox.type = "checkbox";
    const label = element("label", name);
    const swatch = element("span", null, "branch-color");
    swatch.style.backgroundColor = color;
    swatch.setAttribute("aria-hidden", "true");
    label.prepend(checkbox, swatch);
    const message = element("p", "", "layer-status");
    message.setAttribute("role", "status");
    let branches = null;
    let loading = false;
    checkbox.addEventListener("change", async () => {
      if (branches) {
        for (const branch of branches) branch.visible = checkbox.checked;
        drawPlot();
        return;
      }
      if (!checkbox.checked || loading) return;
      loading = true;
      message.textContent = "";
      label.setAttribute("aria-busy", "true");
      try {
        const params = new URLSearchParams({ cycle: selectedCycle });
        const data = await api(`/v1/airports/${identifier}/procedures/${kind}?${params}`, { signal: controller.signal });
        if (controller.signal.aborted) return;
        branches = data.branches.map((branch) => ({
          kind: "airport-procedure", color, visible: checkbox.checked,
          points: branch.waypoints.map((waypoint) => waypoint.position
            ? { ...waypoint.position, name: waypoint.name } : null),
        }));
        if (!branches.some((branch) => branch.points.some(Boolean))) {
          message.textContent = `No plottable ${kind} for this airport.`;
        }
        plotBranches.push(...branches);
        drawPlot();
      } catch (error) {
        if (controller.signal.aborted) return;
        checkbox.checked = false;
        message.textContent = error.message;
      } finally {
        loading = false;
        label.removeAttribute("aria-busy");
      }
    });
    controls.append(label, message);
  }
}

const boundaryLayers = [
  ["FIR", "FIR", "#7fb5ff"], ["CTA", "CTA", "#f5be6d"],
  ["UTA", "UTA", "#c5a4ff"], ["CTA/FIR", "CTA/FIR", "#ffa7d4"],
  ["B", "Class B", "#82c8ff"], ["C", "Class C", "#e2a0ff"],
  ["D", "Class D", "#f8e28a"], ["E", "Class E", "#aadb8c"],
];

async function loadAirspaceOverview() {
  const active = new AbortController();
  request = active;
  const params = new URLSearchParams();
  if (cycle.value) params.set("cycle", cycle.value);
  try {
    const data = await api(`/v1/airspace/boundaries?${params}`, { signal: active.signal });
    if (!active.signal.aborted) addAirspaceMap({ cycle: data.cycle, artcc_boundaries: data.boundaries });
  } catch (error) {
    if (!active.signal.aborted) setStatus(error.message, true);
  }
}

function addAirspaceMap(data) {
  if (data.position) plotPoints = [{ ...data.position, name: "Query point" }];
  const boundaries = data.artcc_boundaries;
  const caption = !data.position ? "All ARTCC boundaries" : boundaries.length
    ? `ARTCC · ${boundaries.map((boundary) => [boundary.id, boundary.level].filter(Boolean).join(" ")).join(" · ")}`
    : "No ARTCC boundary covers this point.";
  byId("plot-caption").textContent = caption;
  canvas.setAttribute("aria-label", caption);
  const map = { overview: !data.position, boundaries, layers: new Map(), controller: new AbortController() };
  airspaceMap = map;
  const controls = byId("airspace-layers");
  controls.hidden = false;
  const message = element("p", "", "layer-status");
  message.setAttribute("role", "status");
  if (data.position) {
    const overview = element("button", "Show all ARTCC");
    overview.type = "button";
    overview.addEventListener("click", () => {
      savedResults.delete("airspace");
      resetResult();
      loadAirspaceOverview();
    });
    controls.append(overview);
  }
  const choices = data.position && boundaries.length ? [...boundaryLayers, ...airspaceLayers] : boundaryLayers;
  for (const [key, name, color] of choices) {
    const isBoundary = boundaryLayers.some(([kind]) => kind === key);
    const checkbox = element("input");
    checkbox.type = "checkbox";
    const label = element("label", name);
    const swatch = element("span", null, "branch-color");
    swatch.setAttribute("aria-hidden", "true");
    swatch.style.backgroundColor = color;
    label.prepend(checkbox, swatch);
    const layer = { color, data: null, selected: false, loading: false };
    map.layers.set(key, layer);
    checkbox.addEventListener("change", async () => {
      layer.selected = checkbox.checked;
      message.textContent = "";
      drawPlot();
      if (!layer.selected || layer.data || layer.loading) return;
      layer.loading = true;
      label.setAttribute("aria-busy", "true");
      const params = new URLSearchParams();
      if (data.cycle || cycle.value) params.set("cycle", data.cycle || cycle.value);
      let endpoint;
      if (isBoundary) {
        params.set("kind", key);
        endpoint = "boundaries";
      } else {
        params.set("layer", key);
        params.set("lat", data.position.lat);
        params.set("lon", data.position.lon);
        endpoint = "layer";
      }
      try {
        const response = await api(`/v1/airspace/${endpoint}?${params}`, { signal: map.controller.signal });
        if (airspaceMap !== map) return;
        layer.data = isBoundary ? { points: [], lines: response.boundaries.flatMap((boundary) => boundary.rings) } : response;
        if (layer.selected && !layer.data.points.length && !layer.data.lines.length) {
          message.textContent = `No ${name} outlines or features are available for this view.`;
        }
        drawPlot();
      } catch (error) {
        if (airspaceMap !== map) return;
        layer.selected = checkbox.checked = false;
        message.textContent = `${name} could not load. ${error.message}`;
        drawPlot();
      } finally {
        layer.loading = false;
        label.removeAttribute("aria-busy");
      }
    });
    controls.append(label);
  }
  controls.append(message);
  drawPlot();
}

function showResult(data) {
  byId("result-cycle").textContent = `Cycle ${data.cycle}`;
  results.replaceChildren();
  if (currentView === "airports") {
    const airport = data.airport;
    const base = airport.base;
    const print = element("button", "Print airport", "print-airport");
    print.type = "button";
    print.addEventListener("click", () => window.print());
    byId("plot-title").textContent = `${airport.icao_id || airport.id} airport layout`;
    results.append(
      element("h3", base.ARPT_NAME || airport.icao_id || airport.id, "result-title"),
      facts([
        ["Airport", airport.icao_id || airport.id], ["City", [base.CITY, base.STATE_CODE].filter(Boolean).join(", ")],
        ["Position", coordinates(airport.position)], ["Elevation", base.ELEV && `${base.ELEV} ft`],
      ]),
      print,
    );
    addAirportLayout(airport);
    addAirportProcedureLayers(airport, data.cycle);
  } else if (currentView === "airspace") {
    results.append(
      table("Matching regions", ["Region", "Type", "Lower", "Upper"], data.regions.map(
        (row) => [row.name || row.id, row.local_type || [row.kind, row.level].filter(Boolean).join(" · "), altitude(row.lower), altitude(row.upper)],
      )),
      element("p", data.not_covered, "coverage"),
    );
    addAirspaceMap(data);
  } else if (currentView === "flightplan") {
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
  } else if (currentView === "routes") {
    for (const airway of data.airways) {
      const details = [airway.base.AWY_LOCATION, airway.base.REGULATORY === "Y" ? "Regulatory" : ""]
        .filter(Boolean).join(" · ");
      results.append(element("h3", [airway.id, details].filter(Boolean).join(" · "), "result-title"));
      const rows = [];
      for (const segment of airway.plot_segments) {
        const convert = (point) => point?.position ? { ...point.position, name: point.name } : null;
        const start = convert(segment.start);
        const end = convert(segment.end);
        const points = segment.gap ? [start, null, end] : [start, end];
        plotBranches.push({ points, color: "#76dfca", visible: true });
        rows.push([segment.sequence, segment.start.name, segment.end?.name,
          segment.gap ? "Published gap" : "",
          [segment.start.issue, segment.end?.issue].filter(Boolean).join("; ")]);
      }
      results.append(table("Published segments", ["Sequence", "From", "To", "Gap", "Position issues"], rows));
    }
    const count = data.airways.reduce((sum, airway) => sum + airway.plot_segments.length, 0);
    const label = `${count} published segments · Gaps and unresolved waypoints are shown in the table.`;
    byId("plot-caption").textContent = label;
    canvas.setAttribute("aria-label", label);
  } else {
    for (const procedure of data.procedures) {
      addProcedureBranches(procedure, data.procedures.length > 1);
    }
    byId("plot-legend").hidden = !plotBranches.length;
    const label = plotBranches.length ? `${plotBranches.length} published branches · Select a branch to hide or show it.`
      : "No published branches to plot.";
    byId("plot-caption").textContent = label;
    canvas.setAttribute("aria-label", label);
  }
  const raw = element("details", null, "raw");
  raw.append(element("summary", "View response JSON"), element("pre", JSON.stringify(data, null, 2)));
  results.append(raw);
  if (plotPoints.length && currentView === "flightplan") {
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
  const available = (point) => point && Number.isFinite(point.lat) && Number.isFinite(point.lon);
  const plotted = plotBranches.length ? plotBranches : [{ points: plotPoints, color: "#76dfca", visible: true }];
  const showWedges = printing || byId("ils-wedges").checked;
  const wedges = showWedges ? plotted.filter((branch) => branch.wedge?.length) : [];
  const note = byId("plot-caption");
  if (!byId("ils-toggle").hidden) {
    const caption = wedges.length ? `${airportCaption} ${ilsPlotNote}` : airportCaption;
    if (note.textContent !== caption) note.textContent = caption;
    canvas.setAttribute("aria-label", note.textContent);
  }
  const boundaryRings = airspaceMap?.boundaries.flatMap((boundary) => boundary.rings) || [];
  const points = [
    ...plotted.filter((branch) => branch.kind !== "airport-procedure" || branch.visible).flatMap((branch) => branch.points), ...wedges.flatMap((branch) => branch.wedge), ...boundaryRings.flat(),
  ].filter(available);
  const reference = airspaceMap?.overview ? 0 : points[0]?.lon || 0;
  const project = (point) => ({
    ...point,
    x: reference + ((point.lon - reference + 540) % 360) - 180,
  });
  const outline = points.map(project);
  const west = Math.min(...outline.map((point) => point.x));
  const east = Math.max(...outline.map((point) => point.x));
  const south = Math.min(...outline.map((point) => point.lat));
  const north = Math.max(...outline.map((point) => point.lat));
  const baseX = points.length ? (west + east) / 2 : -98;
  const baseY = points.length ? (south + north) / 2 : 38;
  const longitudeFactor = Math.max(.17, Math.cos(baseY * Math.PI / 180));
  const minimumSpan = currentView === "airports" ? .003 : 1;
  const scale = plotZoom * (points.length ? Math.min(
    (width - 2 * padding) / Math.max((east - west) * longitudeFactor, minimumSpan),
    (height - 2 * padding) / Math.max(north - south, minimumSpan),
  ) : Math.max(4, width / 90));
  const centerX = baseX - plotPan.x / (scale * longitudeFactor);
  const centerY = baseY + plotPan.y / scale;
  const xy = (lon, lat) => [
    width / 2 + (lon - centerX) * scale * longitudeFactor,
    height / 2 - (lat - centerY) * scale,
  ];
  const gridStep = (pixels) => [.0005, .001, .002, .005, .01, .02, .05, .1, .25, .5, 1, 2, 5, 10, 20, 30].find(
    (step) => step * pixels >= 54,
  ) || 60;
  const lonStep = gridStep(scale * longitudeFactor);
  const latStep = gridStep(scale);
  const degreeLabel = (value) => `${Number(value.toFixed(4))}°`;
  ctx.strokeStyle = printing ? "#c5d1d8" : "#355264";
  ctx.fillStyle = printing ? "#425c6e" : "#8dafbd";
  ctx.font = "10px system-ui";
  const lonStart = centerX - width / (2 * scale * longitudeFactor);
  const lonEnd = centerX + width / (2 * scale * longitudeFactor);
  for (let lon = Math.ceil(lonStart / lonStep) * lonStep; lon <= lonEnd; lon += lonStep) {
    const [x] = xy(lon, centerY);
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke();
    if (x > 26 && x < width - 60) ctx.fillText(degreeLabel(((lon + 540) % 360) - 180), x + 4, 13);
  }
  const latStart = centerY - height / (2 * scale);
  const latEnd = centerY + height / (2 * scale);
  for (let lat = Math.ceil(latStart / latStep) * latStep; lat <= latEnd; lat += latStep) {
    const [, y] = xy(centerX, lat);
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
    if (y > 26 && y < height - 22) ctx.fillText(degreeLabel(lat), 5, y - 4);
  }
  // Dashes indicate a partial result whose published geometry has gaps.
  ctx.lineWidth = 2;
  ctx.setLineDash(partialRoute ? [5, 5] : []);
  const visible = new Map();
  if (airspaceMap) {
    const trace = (points) => {
      let previous;
      for (const point of points) {
        const lon = project(point).x;
        const [x, y] = xy(lon, point.lat);
        if (!previous) ctx.moveTo(x, y);
        else if (Math.abs(lon - previous.lon) > 180) {
          const offset = lon < previous.lon ? 360 : -360;
          const seam = reference + offset / 2;
          const fraction = (seam - previous.lon) / (lon + offset - previous.lon);
          const lat = previous.lat + fraction * (point.lat - previous.lat);
          ctx.lineTo(...xy(seam, lat));
          ctx.moveTo(...xy(seam - offset, lat));
          ctx.lineTo(x, y);
        } else ctx.lineTo(x, y);
        previous = { lon, lat: point.lat };
      }
    };
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = printing ? "#12685e" : "#76dfca";
    for (const boundary of airspaceMap.boundaries) {
      ctx.beginPath();
      for (const ring of boundary.rings) trace(ring);
      ctx.setLineDash(boundary.level === "high" ? [5, 4] : []);
      ctx.stroke();
    }
    ctx.setLineDash([]);
    for (const layer of airspaceMap.layers.values()) {
      if (!layer.selected || !layer.data) continue;
      ctx.strokeStyle = printing ? "#244b6b" : layer.color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (const line of layer.data.lines) trace(line);
      ctx.stroke();
      for (const point of layer.data.points) {
        visible.set(JSON.stringify([point.name, point.lat, point.lon]),
          { ...project(point), color: ctx.strokeStyle, kind: "map-airport" });
      }
    }
  }
  const plotColor = (branch) => {
    if (!printing) return branch.color;
    if (branch.kind === "localizer") return "#94236f";
    if (branch.kind === "pad") return "#985900";
    return "#12534f";
  };
  for (const branch of wedges) {
    ctx.beginPath();
    branch.wedge.forEach((vertex, index) => {
      const point = project(vertex);
      const [x, y] = xy(point.x, point.lat);
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.fillStyle = printing ? "#94236f20" : "#ffc0ee30";
    ctx.strokeStyle = plotColor(branch);
    ctx.lineWidth = 1.5;
    ctx.fill();
    ctx.stroke();
  }
  for (const branch of plotted.filter((item) => item.visible).sort((a, b) =>
    Number(b.kind === "airport-procedure") - Number(a.kind === "airport-procedure"))) {
    ctx.strokeStyle = plotColor(branch);
    ctx.lineWidth = branch.kind === "runway" ? 5 : 2;
    ctx.beginPath();
    let connected = false;
    for (const waypoint of branch.points) {
      if (!available(waypoint)) {
        connected = false;
        continue;
      }
      const point = project(waypoint);
      const [x, y] = xy(point.x, point.lat);
      if (connected) ctx.lineTo(x, y);
      else ctx.moveTo(x, y);
      connected = true;
      visible.set(JSON.stringify([point.name, point.lat, point.lon]), { ...point, kind: branch.kind, color: plotColor(branch) });
    }
    ctx.stroke();
  }
  ctx.setLineDash([]);
  const shown = [...visible.values()];
  shown.forEach((point) => {
    const [x, y] = xy(point.x, point.lat);
    if (point.kind === "localizer") {
      ctx.fillStyle = point.color;
      ctx.beginPath();
      ctx.moveTo(x, y - 5);
      ctx.lineTo(x + 5, y);
      ctx.lineTo(x, y + 5);
      ctx.lineTo(x - 5, y);
      ctx.closePath();
      ctx.fill();
      return;
    }
    if (point.kind === "pad") {
      ctx.strokeStyle = point.color;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(x - 5, y - 5, 10, 10);
      return;
    }
    ctx.fillStyle = point.kind === "map-airport" ? point.color : printing ? "#12534f" : "#b8f6e7";
    ctx.beginPath(); ctx.arc(x, y, point.kind === "map-airport" ? 2 : 3.5, 0, Math.PI * 2); ctx.fill();
  });
  const labels = [];
  const labelOrder = airspaceMap ? [shown.at(-1), ...shown.slice(0, -1)]
    : [shown[0], shown.at(-1), ...shown.slice(1, -1)];
  for (const point of new Set(labelOrder)) {
    if (!point?.name) continue;
    const [x, y] = xy(point.x, point.lat);
    const textWidth = ctx.measureText(point.name).width;
    const anchor = x + 7 + textWidth < width ? x + 7 : x - textWidth - 7;
    let left = anchor;
    let top = Math.max(17, y - 17);
    const collides = (tx, ty) => labels.some((label) => tx < label.right + 4
      && tx + textWidth + 4 > label.left && Math.abs(ty - label.top) < 13);
    if (collides(left, top)) {
      if (!plotBranches.length || point.kind === "airport-procedure") continue;
      for (let step = 1; step <= 10; step++) {
        const candidates = [[anchor, top + step * 13], [anchor, top - step * 13],
          [anchor + step * 17, top], [anchor - step * 17, top]];
        const free = candidates.find(([tx, ty]) => tx >= 4 && tx + textWidth <= width - 4
          && ty >= 17 && ty <= height - 32 && !collides(tx, ty));
        if (free) {
          [left, top] = free;
          ctx.strokeStyle = "#7294a2";
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(left, top + 7); ctx.stroke();
          break;
        }
      }
    }
    const right = left + textWidth;
    labels.push({ left, right, top });
    ctx.fillStyle = point.kind || printing ? point.color : "#b8f6e7";
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
  if (currentView === "flightplan") {
    const body = { route: values.route.trim() };
    if (cycle.value) body.cycle = cycle.value;
    url = "/v1/route/resolve";
    options = { ...options, method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body) };
  } else if (currentView === "airspace") {
    params.set("lat", values.lat);
    params.set("lon", values.lon);
    url = `/v1/airspace/at?${params}`;
  } else if (currentView === "routes") {
    url = `/v1/airways/${encodeURIComponent(values.identifier.trim())}?${params}`;
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
  if (currentView === "airspace") loadAirspaceOverview();
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
  if (currentView === "airspace") loadAirspaceOverview();
  loadCycles();
});
new ResizeObserver(drawPlot).observe(canvas.parentElement);
for (const [id, factor] of [["zoom-in", 1.5], ["zoom-out", 1 / 1.5]]) {
  byId(id).addEventListener("click", () => {
    plotZoom = Math.max(.25, Math.min(32, plotZoom * factor));
    drawPlot();
  });
}
byId("zoom-reset").addEventListener("click", () => {
  setAreaSelection(false);
  plotZoom = 1;
  plotPan = { x: 0, y: 0 };
  drawPlot();
});
const areaButton = byId("zoom-area");
const zoomBox = byId("zoom-box");
let selectingArea = false;
let drag = null;

function setAreaSelection(enabled) {
  selectingArea = enabled;
  drag = null;
  zoomBox.hidden = true;
  areaButton.setAttribute("aria-pressed", String(enabled));
  canvas.parentElement.classList.toggle("selecting", enabled);
}

function plotPosition(event) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: Math.max(0, Math.min(rect.width, event.clientX - rect.left)),
    y: Math.max(0, Math.min(rect.height, event.clientY - rect.top)),
  };
}

function selectionBounds(start, end) {
  return {
    left: Math.min(start.x, end.x), top: Math.min(start.y, end.y),
    width: Math.abs(end.x - start.x), height: Math.abs(end.y - start.y),
  };
}

areaButton.addEventListener("click", () => setAreaSelection(!selectingArea));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && selectingArea) setAreaSelection(false);
});
canvas.addEventListener("pointerdown", (event) => {
  if (event.button !== 0 || drag) return;
  drag = { id: event.pointerId, start: plotPosition(event) };
  canvas.setPointerCapture(event.pointerId);
});
canvas.addEventListener("pointermove", (event) => {
  if (drag?.id !== event.pointerId) return;
  const point = plotPosition(event);
  if (selectingArea) {
    const box = selectionBounds(drag.start, point);
    for (const [property, value] of Object.entries(box)) zoomBox.style[property] = `${value}px`;
    zoomBox.hidden = false;
    return;
  }
  plotPan.x += point.x - drag.start.x;
  plotPan.y += point.y - drag.start.y;
  drag.start = point;
  drawPlot();
});
canvas.addEventListener("pointerup", (event) => {
  if (drag?.id !== event.pointerId) return;
  const start = drag.start;
  drag = null;
  if (!selectingArea) return;

  const box = selectionBounds(start, plotPosition(event));
  zoomBox.hidden = true;
  if (box.width < 8 || box.height < 8) return;
  const { width, height } = canvas.getBoundingClientRect();
  const factor = Math.min(32 / plotZoom, width / box.width, height / box.height);
  plotPan.x = (plotPan.x + width / 2 - box.left - box.width / 2) * factor;
  plotPan.y = (plotPan.y + height / 2 - box.top - box.height / 2) * factor;
  plotZoom *= factor;
  setAreaSelection(false);
  drawPlot();
});
canvas.addEventListener("lostpointercapture", (event) => {
  if (drag?.id !== event.pointerId) return;
  drag = null;
  zoomBox.hidden = true;
});
byId("ils-wedges").addEventListener("change", drawPlot);
window.addEventListener("beforeprint", () => { printing = true; drawPlot(); });
window.addEventListener("afterprint", () => { printing = false; drawPlot(); });
setView(currentView);
loadCycles();
