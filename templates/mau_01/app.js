
const DEFAULT_CONFIG = {
  center: [106.2, 17.3],
  zoom: 5.2,
  style: "https://tiles.openfreemap.org/styles/liberty",
  metrics: [],
  nameField: "name",
  legendNote: "Dữ liệu tải lên",
  theme: {
    fontFamily: "Arial, Helvetica, sans-serif",
    bodySize: "14px",
    popupSize: "13px",
    headingSize: "16px",
    panel: "#152237",
    surface: "#203149",
    text: "#f2f6ff",
    muted: "#a9b7ca",
    border: "#405166",
    accent: "#00d984",
    chartGrid: "#53647a",
    chartSeries: ["#38bdf8", "#f59e0b"],
  },
};
// Preview is UI-only: no fabricated geographic features or metric values.
const PREVIEW_MODE = window.MAP_TEMPLATE_MODE !== "render";
const config = {
  ...DEFAULT_CONFIG,
  ...(window.MAP_CONFIG || {}),
  theme: { ...DEFAULT_CONFIG.theme, ...(window.MAP_CONFIG?.theme || {}) },
};
const data = window.MAP_DATA || { type: "FeatureCollection", features: [] };
const popupConfig = window.MAP_POPUP_CONFIG || { type: "info" };
const PREVIEW_CONTROLS = [
  { label: "Chỉ số 01", icon: "◉" },
  { label: "Chỉ số 02", icon: "◈" },
  { label: "Chỉ số 03", icon: "◍" },
  { label: "Chỉ số 04", icon: "◆" },
];
const el = (id) => document.getElementById(id);
const css = (name, value) =>
  document.documentElement.style.setProperty(name, value);
function applyTheme(t) {
  const keys = {
    fontFamily: "--font-family",
    bodySize: "--body-size",
    popupSize: "--popup-size",
    headingSize: "--heading-size",
    panel: "--panel",
    surface: "--surface",
    text: "--text",
    muted: "--muted",
    border: "--border",
    accent: "--accent",
    chartGrid: "--chart-grid",
  };
  Object.entries(keys).forEach(([k, v]) => {
    if (t[k] != null) css(v, t[k]);
  });
  (t.chartSeries || []).forEach((v, i) => css("--chart-series-" + (i + 1), v));
}
applyTheme(config.theme);
el("previewPopupBtn").onclick = openPreviewPopup;
const map = new maplibregl.Map({
  container: "map",
  style: config.style,
  center: config.center,
  zoom: config.zoom,
  attributionControl: { compact: true },
});
map.dragRotate.disable();
map.keyboard.disable();
map.touchZoomRotate.disableRotation();
function collapseAttribution() {
  const control = map
    .getContainer()
    .querySelector(".maplibregl-ctrl-attrib.maplibregl-compact");
  if (!control) return;
  control.classList.remove("maplibregl-compact-show");
  control.removeAttribute("open");
}
collapseAttribution();
map.once("load", collapseAttribution);
let activeMetric = config.metrics[0] || null;
function validMetric(m) {
  return (
    m &&
    Array.isArray(m.stops) &&
    Array.isArray(m.colors) &&
    m.stops.length === m.colors.length &&
    m.stops.length >= 2 &&
    m.stops.every(Number.isFinite)
  );
}
function colorExpression(m) {
  return [
    "interpolate",
    ["linear"],
    ["to-number", ["get", m.property], m.stops[0]],
    ...m.stops.flatMap((v, i) => [v, m.colors[i]]),
  ];
}
function renderMetrics() {
  const isPreview = PREVIEW_MODE && !config.metrics.length;
  const items = isPreview ? PREVIEW_CONTROLS : config.metrics;
  el("layerCount").textContent = isPreview ? "4" : String(items.length);
  const root = el("layerList");
  root.replaceChildren();
  items.forEach((m, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className =
      "layer-item" +
      (isPreview
        ? i === 0
          ? " active preview-active"
          : ""
        : m === activeMetric
          ? " active"
          : "");
    const label = document.createElement("span");
    label.textContent = m.label + (m.unit ? " " + m.unit : "");
    const icon = document.createElement("span");
    icon.className = "layer-icon";
    icon.textContent = m.icon || "◉";
    b.append(label, icon);
    if (isPreview) {
      b.title = "Xem giao diện nút (không có dữ liệu)";
      b.onclick = () => {
        root
          .querySelectorAll(".layer-item")
          .forEach((x) => x.classList.remove("active", "preview-active"));
        b.classList.add("active", "preview-active");
      };
    } else b.onclick = () => selectMetric(m);
    root.append(b);
  });
}
function selectMetric(m) {
  activeMetric = m;
  renderMetrics();
  renderLegend();
  if (map.getLayer("data-fill") && validMetric(m))
    map.setPaintProperty("data-fill", "fill-color", colorExpression(m));
}
function renderLegend() {
  const legend = el("legend");
  const preview = !validMetric(activeMetric);
  legend.classList.remove("hidden");
  if (preview) {
    el("legendTitle").textContent = "Chú giải bản đồ";
    el("gradient").style.background =
      "linear-gradient(to right,#e6eef7,#88b7d9,#245b9a)";
    el("ticks").replaceChildren();
    el("legendFoot").textContent = PREVIEW_MODE
      ? "Xem trước giao diện · Chưa có dữ liệu"
      : "Chưa có dữ liệu";
    return;
  }
  if (!validMetric(activeMetric)) return;
  const m = activeMetric;
  el("legendTitle").textContent = m.label + (m.unit ? " (" + m.unit + ")" : "");
  el("gradient").style.background =
    `linear-gradient(to right,${m.colors.join(",")})`;
  el("ticks").replaceChildren(
    ...m.stops.map((v) => {
      const s = document.createElement("span");
      s.textContent = String(v).replace(".", ",");
      return s;
    }),
  );
  el("legendFoot").textContent = config.legendNote;
}
function openPreviewPopup() {
  const host = el("popupHost");
  host.replaceChildren();
  const head = document.createElement("div");
  head.className = "popup-head";
  const title = document.createElement("h2");
  title.textContent = "Giao diện popup";
  const close = document.createElement("button");
  close.className = "popup-close";
  close.textContent = "×";
  close.setAttribute("aria-label", "Đóng popup");
  close.onclick = () => host.classList.add("hidden");
  head.append(title, close);
  host.append(head);
  const desc = document.createElement("p");
  desc.className = "popup-subtitle";
  desc.textContent =
    "Khung xem trước — AI sẽ quyết định nội dung và loại biểu đồ.";
  host.append(desc);
  const skeleton = document.createElement("div");
  skeleton.className = "preview-chart";
  skeleton.setAttribute("aria-label", "Vùng hiển thị biểu đồ chưa có dữ liệu");
  for (let i = 0; i < 4; i++) {
    const line = document.createElement("div");
    line.className = "preview-chart-line";
    skeleton.append(line);
  }
  host.append(skeleton);
  const note = document.createElement("div");
  note.className = "preview-note";
  note.textContent = "Font, màu nền, viền và cỡ chữ được kế thừa từ template.";
  host.append(note);
  host.classList.remove("hidden");
}
function featureCenter(f) {
  const g = f.geometry;
  if (!g) return null;
  if (g.type === "Point") return g.coordinates;
  const points = [];
  function walk(c) {
    if (typeof c?.[0] === "number") points.push(c);
    else if (Array.isArray(c)) c.forEach(walk);
  }
  walk(g.coordinates);
  if (!points.length) return null;
  return [
    points.reduce((a, p) => a + p[0], 0) / points.length,
    points.reduce((a, p) => a + p[1], 0) / points.length,
  ];
}
function flyToFeature(f) {
  const c = featureCenter(f);
  if (c) map.flyTo({ center: c, zoom: Math.max(map.getZoom(), 7) });
}
function showResults(q) {
  const root = el("results");
  root.replaceChildren();
  if (!q.trim()) {
    root.classList.add("hidden");
    return;
  }
  const matches = (data.features || []).filter((f) =>
    String(f.properties?.[config.nameField] || "")
      .toLocaleLowerCase("vi")
      .includes(q.toLocaleLowerCase("vi")),
  );
  root.classList.remove("hidden");
  if (!matches.length) {
    const d = document.createElement("div");
    d.className = "empty";
    d.textContent = "Không tìm thấy trong dữ liệu";
    root.append(d);
    return;
  }
  matches.forEach((f) => {
    const b = document.createElement("button");
    b.textContent = f.properties?.[config.nameField] || "Không tên";
    b.onclick = () => {
      flyToFeature(f);
      openPopup(f);
      el("search").value = b.textContent;
      root.classList.add("hidden");
    };
    root.append(b);
  });
}
const NS = "http://www.w3.org/2000/svg";
function svgNode(tag, attrs = {}, text) {
  const n = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, String(v)));
  if (text != null) n.textContent = String(text);
  return n;
}
function chartSeries(f, p) {
  if (Array.isArray(p.series)) return p.series;
  const rows = f.properties?.[p.dataField];
  if (Array.isArray(rows)) return rows;
  return [];
}
function drawChart(host, f, p) {
  const rows = chartSeries(f, p);
  const x = p.xField;
  const ys = (p.yFields || []).filter(Boolean);
  if (!rows.length || !x || !ys.length) {
    const d = document.createElement("div");
    d.className = "popup-empty";
    d.textContent = "Không có dữ liệu biểu đồ phù hợp";
    host.append(d);
    return;
  }
  const nums = rows.map((r) => ys.map((k) => Number(r[k])));
  if (nums.some((a) => a.some((n) => !Number.isFinite(n)))) {
    const d = document.createElement("div");
    d.className = "popup-empty";
    d.textContent = "Dữ liệu biểu đồ không hợp lệ";
    host.append(d);
    return;
  }
  const w = 340,
    h = 210,
    L = 36,
    R = 12,
    T = 12,
    B = 35,
    iw = w - L - R,
    ih = h - T - B;
  const svg = svgNode("svg", {
    viewBox: `0 0 ${w} ${h}`,
    class: "popup-chart",
    role: "img",
    "aria-label": p.title || "Biểu đồ dữ liệu",
  });
  if (p.type === "pie") {
    const values = rows.map((r) => Math.max(0, Number(r[ys[0]])));
    const total = values.reduce((a, b) => a + b, 0);
    if (!total) {
      host.textContent = "Không có giá trị để vẽ biểu đồ tròn";
      return;
    }
    let angle = -Math.PI / 2;
    values.forEach((v, i) => {
      const delta = (v / total) * Math.PI * 2;
      const a = angle,
        b = angle + delta;
      const cx = 125,
        cy = 100,
        rad = 76;
      const start = [cx + rad * Math.cos(a), cy + rad * Math.sin(a)],
        end = [cx + rad * Math.cos(b), cy + rad * Math.sin(b)];
      const path = svgNode("path", {
        d:
          delta >= Math.PI * 2 - 1e-7
            ? `M ${cx - rad} ${cy} A ${rad} ${rad} 0 1 0 ${cx + rad} ${cy} A ${rad} ${rad} 0 1 0 ${cx - rad} ${cy}`
            : `M ${cx} ${cy} L ${start.join(" ")} A ${rad} ${rad} 0 ${delta > Math.PI ? 1 : 0} 1 ${end.join(" ")} Z`,
        fill: `var(--chart-series-${(i % 2) + 1})`,
        opacity: i > 1 ? 0.6 : 1,
      });
      svg.append(path);
      angle = b;
    });
    rows
      .slice(0, 5)
      .forEach((r, i) =>
        svg.append(
          svgNode("text", { x: 230, y: 42 + i * 23 }, `${r[x]}: ${r[ys[0]]}`),
        ),
      );
    host.append(svg);
    return;
  }
  const values = nums.flat();
  const min = Math.min(0, ...values),
    max = Math.max(1, ...values),
    range = max - min || 1;
  const yPos = (v) => T + ih - ((v - min) / range) * ih;
  for (let i = 0; i <= 4; i++) {
    const v = min + (range * i) / 4,
      y = yPos(v);
    svg.append(
      svgNode("line", { x1: L, y1: y, x2: w - R, y2: y, class: "grid" }),
    );
    svg.append(svgNode("text", { x: 2, y: y + 4 }, Number(v.toFixed(1))));
  }
  rows.forEach((r, i) => {
    const px = L + ((i + 0.5) * iw) / rows.length;
    svg.append(
      svgNode(
        "text",
        { x: px, y: h - 13, "text-anchor": "middle" },
        String(r[x]).slice(0, 9),
      ),
    );
  });
  if (p.type === "line") {
    ys.forEach((key, j) => {
      const pts = rows.map((r, i) => [
        L + ((i + 0.5) * iw) / rows.length,
        yPos(Number(r[key])),
      ]);
      svg.append(
        svgNode("polyline", {
          points: pts.map((a) => a.join(",")).join(" "),
          fill: "none",
          stroke: `var(--chart-series-${(j % 2) + 1})`,
          "stroke-width": 2.5,
        }),
      );
      pts.forEach(([cx, cy]) =>
        svg.append(
          svgNode("circle", {
            cx,
            cy,
            r: 3.5,
            fill: `var(--chart-series-${(j % 2) + 1})`,
          }),
        ),
      );
    });
  } else {
    const slot = iw / rows.length;
    rows.forEach((r, i) =>
      ys.forEach((key, j) => {
        const bw = (slot * 0.75) / ys.length;
        const x0 = L + i * slot + slot * 0.125 + j * bw;
        const v = Number(r[key]);
        const y0 = Math.min(yPos(0), yPos(v));
        const bh = Math.max(1, Math.abs(yPos(v) - yPos(0)));
        svg.append(
          svgNode("rect", {
            x: x0,
            y: y0,
            width: bw - 2,
            height: bh,
            rx: 2,
            fill: `var(--chart-series-${(j % 2) + 1})`,
          }),
        );
      }),
    );
  }
  host.append(svg);
}
function openPopup(f) {
  const host = el("popupHost");
  host.replaceChildren();
  const p = popupConfig;
  const head = document.createElement("div");
  head.className = "popup-head";
  const title = document.createElement("h2");
  title.textContent = f.properties?.[config.nameField] || "Thông tin";
  const close = document.createElement("button");
  close.className = "popup-close";
  close.textContent = "×";
  close.setAttribute("aria-label", "Đóng popup");
  close.onclick = () => host.classList.add("hidden");
  head.append(title, close);
  host.append(head);
  if (p.title) {
    const sub = document.createElement("p");
    sub.className = "popup-subtitle";
    sub.textContent = p.title;
    host.append(sub);
  }
  if (["bar", "line", "pie"].includes(p.type)) drawChart(host, f, p);
  else {
    const dl = document.createElement("dl");
    dl.className = "popup-fields";
    const fields =
      p.fields ||
      Object.keys(f.properties || {}).filter((k) => k !== config.nameField);
    fields.forEach((k) => {
      const dt = document.createElement("dt"),
        dd = document.createElement("dd");
      dt.textContent = k;
      dd.textContent = String(f.properties?.[k] ?? "—");
      dl.append(dt, dd);
    });
    host.append(dl);
  }
  host.classList.remove("hidden");
}
map.on("load", () => {
  if (!data.features?.length) return;
  map.addSource("dataset", { type: "geojson", data });
  const polygon = data.features.some((f) =>
    /Polygon/.test(f.geometry?.type || ""),
  );
  const point = data.features.some((f) => /Point/.test(f.geometry?.type || ""));
  if (polygon) {
    map.addLayer({
      id: "data-fill",
      type: "fill",
      source: "dataset",
      filter: ["==", ["geometry-type"], "Polygon"],
      paint: {
        "fill-color": validMetric(activeMetric)
          ? colorExpression(activeMetric)
          : config.theme.accent,
        "fill-opacity": 0.64,
      },
    });
    map.addLayer({
      id: "data-outline",
      type: "line",
      source: "dataset",
      filter: ["==", ["geometry-type"], "Polygon"],
      paint: { "line-color": config.theme.accent, "line-width": 2 },
    });
  }
  if (point)
    map.addLayer({
      id: "data-points",
      type: "circle",
      source: "dataset",
      filter: ["==", ["geometry-type"], "Point"],
      paint: {
        "circle-radius": 7,
        "circle-color": config.theme.accent,
        "circle-stroke-color": "#fff",
        "circle-stroke-width": 1.5,
      },
    });
  ["data-fill", "data-points"].forEach((id) => {
    if (map.getLayer(id)) {
      map.on("click", id, (e) => {
        const f = e.features?.[0];
        if (f) openPopup(f);
      });
      map.on(
        "mouseenter",
        id,
        () => (map.getCanvas().style.cursor = "pointer"),
      );
      map.on("mouseleave", id, () => (map.getCanvas().style.cursor = ""));
    }
  });
});
el("zoomIn").onclick = () => map.zoomIn();
el("zoomOut").onclick = () => map.zoomOut();
el("fullscreen").onclick = () => {
  if (!document.fullscreenElement)
    document.documentElement.requestFullscreen?.();
  else document.exitFullscreen?.();
};
el("layerToggle").onclick = () => {
  const hidden = el("layerList").classList.toggle("hidden");
  el("layerToggle").setAttribute("aria-expanded", String(!hidden));
};
el("search").oninput = (e) => showResults(e.target.value);
el("searchBtn").onclick = () => showResults(el("search").value);
document.addEventListener("click", (e) => {
  if (!e.target.closest(".top-center")) el("results").classList.add("hidden");
});
renderMetrics();
renderLegend();
