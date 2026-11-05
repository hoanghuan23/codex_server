// Template-only controls. No popup, chart, feature-click, or data-layer logic.
const map = new maplibregl.Map({ container: 'map', style: 'https://tiles.openfreemap.org/styles/dark', center: [105.84, 20.9], zoom: 5.5, attributionControl: true });
document.getElementById('zoomIn').addEventListener('click', () => map.zoomIn());
document.getElementById('zoomOut').addEventListener('click', () => map.zoomOut());
document.getElementById('fullscreen').addEventListener('click', () => { if (document.fullscreenElement) document.exitFullscreen(); else document.querySelector('.map-shell').requestFullscreen?.(); });
document.querySelectorAll('.chip').forEach(button => button.addEventListener('click', () => { document.querySelectorAll('.chip').forEach(item => item.classList.remove('active')); button.classList.add('active'); }));
