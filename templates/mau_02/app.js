/* MAU_02 — Minimal map shell only.
 * No fabricated GeoJSON, no map feature click handlers, no popup creation,
 * no chart drawing, no AI-specific data processing.
 * Existing application core can mount its own data and interactions later.
 */
const map = new maplibregl.Map({
  container: 'map',
  style: 'https://tiles.openfreemap.org/styles/liberty',
  center: [106.2, 16.4],
  zoom: 4.5,
  attributionControl: true
});

document.getElementById('zoomIn').addEventListener('click', () => map.zoomIn());
document.getElementById('zoomOut').addEventListener('click', () => map.zoomOut());
document.getElementById('fullscreen').addEventListener('click', async () => {
  if (document.fullscreenElement) await document.exitFullscreen();
  else await document.documentElement.requestFullscreen();
});

// UI-only selection; no layer data, filtering, or map interaction is implemented.
document.querySelectorAll('.layer').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.layer').forEach(item => item.classList.remove('active'));
    button.classList.add('active');
  });
});
