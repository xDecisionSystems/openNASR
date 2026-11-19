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
    examples: [["KABQ"], ["KDEN"], ["KSEA"], ["KJFK"]],
    title: "Find an airport",
    help: "Search by identifier, airport name, or city.",
    fields: [{ name: "identifier", label: "Airport search" }],
    caption: "Query an airport to plot its runways, helipads, and ILS localizers.",
  },
  airspace: {
    title: "Select an ARTCC",
    help: "",
    caption: "All ARTCC boundaries.",
  },
  flightplan: {
    examples: [["KABQ.DOOKK3.TXO..KTYR"], ["KDEN..KCOS"], ["KSEA..KPDX"], ["KJFK..KBOS"]],
    title: "Resolve a flight plan",
    help: "Enter an FAA route string to see its waypoints and diagnostics.",
    fields: [{ name: "route", label: "Flight plan route", multiline: true }],
    caption: "Resolved waypoints will appear here in flight order.",
  },
  routes: {
    examples: [["J74"], ["V12"], ["V16"]],
    title: "Find a jetway or airway",
    help: "Enter a published route designation such as J74 or V12.",
    fields: [{ name: "identifier", label: "Route designation" }],
    caption: "Query a jetway or airway to plot its published segments.",
  },
  arrivals: {
    examples: [["GRNCH5"], ["MIERA.MIERA2"], ["HYDRR.HYDRR1"]],
    title: "Find an arrival",
    help: "Enter a STAR name or computer code.",
    fields: [{ name: "identifier", label: "Arrival identifier" }],
    caption: "Query an arrival to plot its published branches.",
  },
  departures: {
    examples: [["DOOKK3"], ["LARGO3.ABQ"], ["CHILY4.CHILY"]],
    title: "Find a departure",
    help: "Enter a departure procedure name or computer code.",
    fields: [{ name: "identifier", label: "Departure identifier" }],
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
let airportBoundaries = [];
let airportViewport = null;
let airspaceMap = null;
let airportProcedureRequest = null;
const ilsPlotNote = "ILS course wedges are illustrative · 700 ft at the runway end · ±2.5° · 20 NM.";
const airspaceLayers = [
  ["airports", "Airports", "#ffcb81"],
  ["departures", "Departures", "#87ddbf"],
  ["arrivals", "Arrivals", "#ffa7d4"],
  ["airways", "Jetways / airways", "#9bbaff"],
  ["fixes", "Fixes", "#f3f1ac"],
  ["vors", "VOR / VORTAC", "#80e9f8"],
  ["ndbs", "NDB", "#ffa47b"],
  ["other-navaids", "Other navaids", "#d7b7fc"],
];
const currentExamples = new Map();
const savedInputs = new Map();
const savedResults = new Map();
const selectedAirports = new Map();

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

function pickExample(view) {
  const previous = currentExamples.get(view);
  const options = views[view].examples.filter((example) => example !== previous);
  const example = options[Math.floor(Math.random() * options.length)];
  currentExamples.set(view, example);
  byId("example").textContent = `Try ${example.join(", ")}`;
  views[view].fields.forEach((field, index) => {
    form.elements[field.name].placeholder = example[index];
  });
}

function setView(name) {
  if (!views[name]) return;
  if (byId("fields").children.length) savedInputs.set(currentView, new FormData(form));
  request?.abort();
  currentView = name;
  byId("airport-tags").hidden = name !== "airports" || !selectedAirports.size;
  byId("airport-matches").replaceChildren();
  byId("airport-matches").hidden = true;
  const view = views[name];
  for (const tab of tabs) {
    const active = tab.dataset.tab === name;
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
  }
  byId("query-panel").setAttribute("aria-labelledby", `tab-${name}`);
  byId("query-title").textContent = view.title;
  byId("query-help").textContent = view.help;
  byId("plot-caption").textContent = view.caption;
  byId("submit").hidden = name === "airspace";
  byId("example").hidden = name === "airspace";
  if (name === "airspace") {
    const label = element("label", "ARTCC");
    label.htmlFor = "query-artcc";
    const select = element("select");
    select.id = label.htmlFor;
    select.name = "artcc";
    select.multiple = true;
    select.size = 5;
    const otherLabel = element("label", "Other Airspace");
    otherLabel.htmlFor = "query-other-airspace";
    const other = element("select");
    other.id = otherLabel.htmlFor;
    other.name = "other-airspace";
    other.multiple = true;
    other.size = 4;
    other.append(...boundaryLayers
      .filter(([kind]) => kind.length > 1)
      .map(([kind, name]) => new Option(name, kind)));
    const previousOther = savedInputs.get(name)?.getAll(other.name) || [];
    for (const option of other.options) option.selected = previousOther.includes(option.value);
    const hint = element("p", "Use Ctrl or ⌘ to select or clear multiple options. With no center selected, the map shows all ARTCCs.", "empty");
    byId("fields").replaceChildren(label, select, otherLabel, other, hint);
    resetResult();
    loadAirspaceOverview();
    return;
  }

  byId("fields").replaceChildren(...view.fields.map((field) => {
    const group = element("div");
    const label = element("label", field.label);
    label.htmlFor = `query-${field.name}`;
    const input = element(field.multiline ? "textarea" : "input");
    input.id = label.htmlFor;
    input.name = field.name;
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
  pickExample(name);
  resetResult();
  if (name === "airports" && selectedAirports.size) renderSelectedAirports();
  else if (savedResults.has(name)) showResult(savedResults.get(name));
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
  airportBoundaries = [];
  clearTimeout(airportViewport?.timer);
  airportViewport?.request?.abort();
  airportViewport = null;
  clearTimeout(airspaceMap?.classViewport.timer);
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
  const firstBranch = plotBranches.length;
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

  const airportBranches = plotBranches.slice(firstBranch);
  const runwayCount = airportBranches.filter((branch) => branch.kind === "runway").length;
  const padCount = airportBranches.length - runwayCount;
  const unavailable = airport.runways.length - airportBranches.length;
  if ((!airportBranches.length || selectedAirports.size > 1) && airport.position) {
    plotBranches.push({
      points: [{ ...airport.position, name: airport.icao_id || airport.id }],
      kind: "airport-reference", color: "#b8f6e7", visible: true,
    });
  }
  const hasReference = !airportBranches.length && airport.position;
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
        wedge: row.wedge, kind: "localizer", color: "#ffc0ee", visible: false,
      });
    }
    return [row.id, row.runway_end, coordinates(row.position),
      row.wedge.length ? "Available" : "Geometry unavailable"];
  });
  results.append(table("ILS localizers", ["Identifier", "Runway", "Transmitter position", "Course wedge"], localizers));
}

function addAirportProcedureLayers(airports, selectedCycle) {
  const controller = new AbortController();
  airportProcedureRequest = controller;
  const controls = byId("airport-procedure-layers");
  controls.hidden = false;
  const localizers = plotBranches.filter((branch) => branch.kind === "localizer");
  if (localizers.length) {
    const checkbox = element("input");
    checkbox.type = "checkbox";
    const label = element("label", "ILS");
    label.prepend(checkbox);
    controls.append(label);
    checkbox.addEventListener("change", () => {
      for (const branch of localizers) branch.visible = checkbox.checked;
      canvas.closest(".plot-card").classList.toggle("ils-plot",
        checkbox.checked && localizers.some((branch) => branch.wedge.length));
      drawPlot();
    });
  }
  const messages = [];
  const positions = airports.map((airport) => airport.position).filter(Boolean);
  if (positions.length) {
    const checkbox = element("input");
    checkbox.type = "checkbox";
    const label = element("label", "Airspace");
    label.prepend(checkbox);
    controls.append(label);
    const message = element("p", "", "layer-status");
    message.setAttribute("role", "status");
    messages.push(message);
    let boundaries;
    checkbox.addEventListener("change", async () => {
      message.textContent = "";
      if (!checkbox.checked || boundaries) {
        airportBoundaries = checkbox.checked ? boundaries : [];
        drawPlot();
        return;
      }
      checkbox.disabled = true;
      label.setAttribute("aria-busy", "true");
      try {
        const responses = await Promise.all(positions.map(({ lat, lon }) => {
          const params = new URLSearchParams({ cycle: selectedCycle, lat, lon, include_boundaries: true });
          return api(`/v1/airspace/at?${params}`, { signal: controller.signal });
        }));
        if (controller.signal.aborted) return;
        const unique = new Map();
        for (const boundary of responses.flatMap((response) => response.boundaries)) {
          unique.set(JSON.stringify(boundary), boundary);
        }
        boundaries = [...unique.values()];
        airportBoundaries = boundaries;
        if (!boundaries.length) message.textContent = "No published boundaries contain this airport.";
        drawPlot();
      } catch (error) {
        if (controller.signal.aborted) return;
        checkbox.checked = false;
        message.textContent = error.message;
      } finally {
        checkbox.disabled = false;
        label.removeAttribute("aria-busy");
      }
    });
  }
  const viewportCheckbox = element("input");
  viewportCheckbox.type = "checkbox";
  const viewportLabel = element("label", "Airspace in view");
  viewportLabel.prepend(viewportCheckbox);
  controls.append(viewportLabel);
  const viewportMessage = element("p", "", "layer-status");
  viewportMessage.setAttribute("role", "status");
  messages.push(viewportMessage);
  viewportCheckbox.addEventListener("change", () => {
    clearTimeout(airportViewport?.timer);
    airportViewport?.request?.abort();
    airportViewport = viewportCheckbox.checked
      ? { cycle: selectedCycle, message: viewportMessage, boundaries: [] } : null;
    viewportMessage.textContent = "";
    drawPlot();
  });
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
        const responses = await Promise.all(airports.map((airport) => {
          const identifier = encodeURIComponent(airport.icao_id || airport.id);
          return api(`/v1/airports/${identifier}/procedures/${kind}?${params}`, { signal: controller.signal });
        }));
        if (controller.signal.aborted) return;
        branches = responses.flatMap((data) => data.branches).map((branch) => ({
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
    controls.append(label);
    messages.push(message);
  }
  controls.append(...messages);
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
    if (active.signal.aborted) return;
    const select = byId("query-artcc");
    const previous = select.options.length ? [...select.selectedOptions].map((option) => option.value)
      : savedInputs.get("airspace")?.getAll("artcc") || [];
    const names = Object.entries(data.centers).sort(([a], [b]) => a.localeCompare(b));
    select.replaceChildren(...names.map(([id, name]) => new Option(name
        ? `${id}: ${name.toLowerCase().replace(/\b[a-z]/g, (letter) => letter.toUpperCase())}` : id, id)));
    for (const option of select.options) option.selected = previous.includes(option.value);
    const render = () => {
      resetResult();
      const selected = [...select.selectedOptions];
      const artcc = selected.map((option) => option.value);
      const label = selected.length === 1 ? selected[0].textContent : artcc.join(", ");
      const boundaries = artcc.length ? data.boundaries.filter((boundary) => artcc.includes(boundary.id)) : data.boundaries;
      addAirspaceMap({ cycle: data.cycle, artcc, label, artcc_boundaries: boundaries });
      results.replaceChildren(table("Published ARTCC boundaries", ["Center", "Altitude level"],
        boundaries.map((boundary) => [boundary.id, boundary.level])));
      byId("result-cycle").textContent = `Cycle ${data.cycle}`;
    };
    select.onchange = render;
    render();
  } catch (error) {
    if (!active.signal.aborted) setStatus(error.message, true);
  }
}

function addAirspaceMap(data) {
  const boundaries = data.artcc_boundaries;
  const caption = data.artcc.length ? data.label : "All ARTCC boundaries";
  byId("plot-caption").textContent = caption;
  canvas.setAttribute("aria-label", caption);
  const map = { boundaries, layers: new Map(), controller: new AbortController() };
  airspaceMap = map;
  const controls = byId("airspace-layers");
  controls.hidden = false;
  const message = element("p", "", "layer-status");
  message.setAttribute("role", "status");
  map.classViewport = { cycle: data.cycle, artcc: data.artcc, message, boundaries: [], controller: map.controller };
  const classLayers = boundaryLayers.filter(([kind]) => kind.length === 1);
  const choices = data.artcc.length ? [...classLayers, ...airspaceLayers] : classLayers;
  const other = byId("query-other-airspace");
  let otherRequest;
  const loadOtherAirspace = async () => {
    otherRequest?.abort();
    for (const [kind] of boundaryLayers) {
      if (kind.length > 1) map.layers.delete(kind);
    }
    other.removeAttribute("aria-busy");
    message.textContent = "";
    drawPlot();
    const kinds = [...other.selectedOptions].map((option) => option.value);
    if (!kinds.length) return;
    const active = new AbortController();
    otherRequest = active;
    const signal = AbortSignal.any([active.signal, map.controller.signal]);
    other.setAttribute("aria-busy", "true");
    try {
      const outcomes = await Promise.allSettled(kinds.map(async (kind) => {
        const params = new URLSearchParams({ kind, cycle: data.cycle });
        const response = await api(`/v1/airspace/boundaries?${params}`, { signal });
        return { kind, lines: response.boundaries.flatMap((boundary) => boundary.rings) };
      }));
      if (signal.aborted) return;
      const unavailable = [];
      outcomes.forEach((outcome, index) => {
        if (outcome.status === "rejected" || !outcome.value.lines.length) {
          unavailable.push(kinds[index]);
          return;
        }
        const { kind, lines } = outcome.value;
        const color = boundaryLayers.find(([key]) => key === kind)[2];
        map.layers.set(kind, { color, selected: true, data: { lines, points: [] } });
      });
      if (unavailable.length) message.textContent = `No outlines loaded for ${unavailable.join(", ")}.`;
      drawPlot();
    } finally {
      if (otherRequest === active && airspaceMap === map) other.removeAttribute("aria-busy");
    }
  };
  other.onchange = loadOtherAirspace;
  other.removeAttribute("aria-busy");
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
      if (isBoundary || !layer.selected || layer.data || layer.loading) return;
      layer.loading = true;
      label.setAttribute("aria-busy", "true");
      const params = new URLSearchParams();
      if (data.cycle || cycle.value) params.set("cycle", data.cycle || cycle.value);
      params.set("layer", key);
      for (const id of data.artcc) params.append("artcc", id);
      try {
        const response = await api(`/v1/airspace/layer?${params}`, { signal: map.controller.signal });
        if (airspaceMap !== map) return;
        layer.data = response;
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
  loadOtherAirspace();
}

function renderSelectedAirports() {
  resetResult();
  const tags = byId("airport-tags");
  tags.replaceChildren();
  tags.hidden = selectedAirports.size === 0;
  for (const [id] of selectedAirports) {
    const tag = element("span", id, "airport-tag");
    const remove = element("button", "×");
    remove.type = "button";
    remove.setAttribute("aria-label", `Remove ${id}`);
    remove.addEventListener("click", () => {
      selectedAirports.delete(id);
      renderSelectedAirports();
      (tags.querySelector("button") || byId("query-identifier")).focus();
    });
    tag.append(remove);
    tags.append(tag);
  }
  for (const match of byId("airport-matches").querySelectorAll("button")) {
    match.disabled = selectedAirports.has(match.dataset.airport);
  }
  if (!selectedAirports.size) return;

  const entries = [...selectedAirports.values()];
  const airports = entries.map(({ airport }) => airport);
  const selectedCycle = entries[0].cycle;
  results.replaceChildren();
  byId("result-cycle").textContent = `Cycle ${selectedCycle}`;
  byId("plot-title").textContent = airports.length === 1
    ? `${airports[0].icao_id || airports[0].id} airport layout` : "Airport layouts";
  const print = element("button", airports.length === 1 ? "Print airport" : "Print airports", "print-airport");
  print.type = "button";
  print.addEventListener("click", () => window.print());
  results.append(print);
  for (const airport of airports) {
    const base = airport.base;
    results.append(
      element("h3", base.ARPT_NAME || airport.icao_id || airport.id, "result-title"),
      facts([
        ["Airport", airport.icao_id || airport.id], ["City", [base.CITY, base.STATE_CODE].filter(Boolean).join(", ")],
        ["Position", coordinates(airport.position)], ["Elevation", base.ELEV && `${base.ELEV} ft`],
      ]),
    );
    addAirportLayout(airport);
  }
  if (airports.length > 1) airportCaption = `${airports.length} selected airports.`;
  addAirportProcedureLayers(airports, selectedCycle);
  const raw = element("details", null, "raw");
  raw.append(element("summary", "View response JSON"),
    element("pre", JSON.stringify(entries.length === 1 ? entries[0] : { cycle: selectedCycle, airports }, null, 2)));
  results.append(raw);
  drawPlot();
}

async function searchAirports(text, active) {
  const matches = byId("airport-matches");
  matches.replaceChildren();
  matches.hidden = true;
  const selectedCycle = selectedAirports.values().next().value?.cycle || cycle.value;
  const params = new URLSearchParams({ q: text });
  if (selectedCycle) params.set("cycle", selectedCycle);
  const data = await api(`/v1/airports/search?${params}`, { signal: active.signal });
  if (active.signal.aborted) return;
  for (const match of data.airports) {
    const place = [match.city, match.state].filter(Boolean).join(", ");
    const button = element("button", [match.id, match.name, place].filter(Boolean).join(" · "));
    button.type = "button";
    button.dataset.airport = match.id;
    button.disabled = selectedAirports.has(match.id);
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const selected = await api(`/v1/airports/${encodeURIComponent(match.id)}?cycle=${data.cycle}`, {
          signal: active.signal,
        });
        if (active.signal.aborted) return;
        selectedAirports.set(match.id, selected);
        renderSelectedAirports();
        byId("query-identifier").focus();
      } catch (error) {
        if (active.signal.aborted) return;
        button.disabled = false;
        setStatus(error.message, true);
      }
    });
    matches.append(button);
  }
  matches.hidden = !data.airports.length;
  setStatus(data.airports.length ? "Select an airport to add it." : "No airports match your search.");
}

function showResult(data) {
  byId("result-cycle").textContent = `Cycle ${data.cycle}`;
  results.replaceChildren();
  if (currentView === "flightplan") {
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

function updateBoundaryViewport(viewport, west, south, east, north, kinds = []) {
  if (!viewport) return;
  const normalizedWest = ((west + 180) % 360 + 360) % 360 - 180;
  const bounds = {
    west: normalizedWest.toFixed(5),
    south: Math.max(-90, south).toFixed(5),
    span: Math.min(360, east - west).toFixed(5),
    north: Math.min(90, north).toFixed(5),
  };
  const params = new URLSearchParams({ ...bounds, cycle: viewport.cycle });
  for (const kind of kinds) params.append("kind", kind);
  for (const id of viewport.artcc || []) params.append("artcc", id);
  const key = params.toString();
  if (key === viewport.key) return;
  viewport.key = key;
  clearTimeout(viewport.timer);
  viewport.request?.abort();
  if (Number(bounds.south) >= Number(bounds.north) || Number(bounds.span) <= 0) {
    viewport.boundaries = [];
    viewport.message.textContent = "";
    return;
  }
  viewport.timer = setTimeout(async () => {
    const active = new AbortController();
    viewport.request = active;
    const signal = viewport.controller ? AbortSignal.any([active.signal, viewport.controller.signal]) : active.signal;
    try {
      const data = await api(`/v1/airspace/viewport?${params}`, { signal });
      if (signal.aborted) return;
      viewport.boundaries = data.boundaries;
      viewport.message.textContent = data.boundaries.length ? "" : "No airspace outlines in view.";
      drawPlot();
    } catch (error) {
      if (signal.aborted) return;
      viewport.boundaries = [];
      viewport.message.textContent = error.message;
      drawPlot();
    }
  }, 220);
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
  const wedges = plotted.filter((branch) => branch.visible && branch.wedge?.length);
  const note = byId("plot-caption");
  if (currentView === "airports" && airportCaption) {
    const types = new Set(airportBoundaries.map(({ kind }) => kind.length === 1 ? `Class ${kind}` : kind));
    const airspaceNote = types.size ? `Airspace at airport · ${[...types].join(", ")}.` : "";
    const caption = [airportCaption, wedges.length ? ilsPlotNote : "", airspaceNote].filter(Boolean).join(" ");
    if (note.textContent !== caption) note.textContent = caption;
    canvas.setAttribute("aria-label", note.textContent);
  }
  const boundaries = airspaceMap?.boundaries || airportBoundaries;
  const boundaryRings = boundaries.flatMap((boundary) => boundary.rings);
  const points = [
    ...plotted.filter((branch) => currentView !== "airports" || branch.visible).flatMap((branch) => branch.points), ...wedges.flatMap((branch) => branch.wedge), ...boundaryRings.flat(),
  ].filter(available);
  // Keep both sides of the Aleutians west of the contiguous U.S.
  const reference = airspaceMap ? -120 : points[0]?.lon || 0;
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
  updateBoundaryViewport(airportViewport, lonStart, latStart, lonEnd, latEnd);
  const classViewport = airspaceMap?.classViewport;
  if (classViewport) {
    const kinds = ["B", "C", "D", "E"].filter((kind) => airspaceMap.layers.get(kind)?.selected);
    if (kinds.length) {
      updateBoundaryViewport(classViewport, lonStart, latStart, lonEnd, latEnd, kinds);
      classViewport.boundaries = classViewport.boundaries.filter((boundary) => kinds.includes(boundary.kind));
    } else if (classViewport.key) {
      clearTimeout(classViewport.timer);
      classViewport.request?.abort();
      classViewport.key = null;
      classViewport.boundaries = [];
    }
  }
  for (let lat = Math.ceil(latStart / latStep) * latStep; lat <= latEnd; lat += latStep) {
    const [, y] = xy(centerX, lat);
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
    if (y > 26 && y < height - 22) ctx.fillText(degreeLabel(lat), 5, y - 4);
  }
  // Dashes indicate a partial result whose published geometry has gaps.
  ctx.lineWidth = 2;
  ctx.setLineDash(partialRoute ? [5, 5] : []);
  const visible = new Map();
  const viewportBoundaries = airportViewport?.boundaries || classViewport?.boundaries || [];
  if (airspaceMap || airportBoundaries.length || viewportBoundaries.length) {
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
    for (const boundary of [...boundaries, ...viewportBoundaries]) {
      const color = boundaryLayers.find(([kind]) => kind === boundary.kind)?.[2];
      ctx.strokeStyle = printing ? (color ? "#524485" : "#12685e") : color || "#76dfca";
      ctx.beginPath();
      for (const ring of boundary.rings) trace(ring);
      ctx.setLineDash(boundary.level === "high" ? [5, 4] : []);
      ctx.stroke();
    }
    ctx.setLineDash([]);
    for (const layer of airspaceMap?.layers.values() || []) {
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
  const labelOrder = currentView === "airports" && selectedAirports.size > 1
    ? [...shown.filter((point) => point.kind === "airport-reference"),
      ...shown.filter((point) => point.kind !== "airport-reference")]
    : airspaceMap ? [shown.at(-1), ...shown.slice(0, -1)]
      : [shown[0], shown.at(-1), ...shown.slice(1, -1)];
  for (const point of new Set(labelOrder)) {
    if (!point?.name) continue;
    const [x, y] = xy(point.x, point.lat);
    if (x < 0 || x >= width || y < 0 || y >= height) continue;
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
  if (currentView === "airspace") return;
  request?.abort();
  const activeRequest = new AbortController();
  request = activeRequest;
  const queriedView = currentView;
  savedResults.delete(queriedView);
  const values = Object.fromEntries(new FormData(form));
  const params = new URLSearchParams();
  if (cycle.value) params.set("cycle", cycle.value);
  if (queriedView === "airports") {
    const text = values.identifier.trim();
    if (!text) return;
    setStatus("Searching…");
    byId("submit").disabled = true;
    try {
      await searchAirports(text, activeRequest);
    } catch (error) {
      if (!activeRequest.signal.aborted) setStatus(error.message, true);
    } finally {
      if (request === activeRequest) byId("submit").disabled = false;
    }
    return;
  }
  let url, options = { signal: activeRequest.signal };
  if (currentView === "flightplan") {
    const body = { route: values.route.trim() };
    if (cycle.value) body.cycle = cycle.value;
    url = "/v1/route/resolve";
    options = { ...options, method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body) };
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
  selectedAirports.clear();
  for (const id of ["airport-tags", "airport-matches"]) {
    byId(id).replaceChildren();
    byId(id).hidden = true;
  }
  resetResult();
  if (currentView === "airspace") loadAirspaceOverview();
});
byId("example").addEventListener("click", () => {
  const example = currentExamples.get(currentView);
  views[currentView].fields.forEach((field, index) => {
    form.elements[field.name].value = example[index];
  });
  form.requestSubmit();
  pickExample(currentView);
});
byId("apply-key").addEventListener("click", () => {
  apiKey = byId("api-key").value.trim();
  byId("api-key").value = "";
  byId("apply-key").closest("details").open = false;
  request?.abort();
  savedResults.clear();
  selectedAirports.clear();
  for (const id of ["airport-tags", "airport-matches"]) {
    byId(id).replaceChildren();
    byId(id).hidden = true;
  }
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

canvas.addEventListener("dblclick", (event) => {
  if (selectingArea || event.button !== 0) return;
  const factor = event.shiftKey ? 1 / 1.5 : 1.5;
  const nextZoom = Math.max(.25, Math.min(32, plotZoom * factor));
  const scale = nextZoom / plotZoom;
  const { width, height } = canvas.getBoundingClientRect();
  const point = plotPosition(event);
  const x = point.x - width / 2;
  const y = point.y - height / 2;
  plotPan.x = (plotPan.x - x) * scale;
  plotPan.y = (plotPan.y - y) * scale;
  plotZoom = nextZoom;
  drawPlot();
});

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
window.addEventListener("beforeprint", () => { printing = true; drawPlot(); });
window.addEventListener("afterprint", () => { printing = false; drawPlot(); });
setView(currentView);
loadCycles();
