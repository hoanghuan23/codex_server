const map = new maplibregl.Map({
  container: 'map',
  style: 'https://tiles.openfreemap.org/styles/liberty',
  center: [106.2, 17.1],
  zoom: 5,
  attributionControl: true
});

document.getElementById('zoomIn').addEventListener('click', () => map.zoomIn());
document.getElementById('zoomOut').addEventListener('click', () => map.zoomOut());
document.getElementById('fullscreen').addEventListener('click', async () => {
  if (document.fullscreenElement) await document.exitFullscreen();
  else await document.querySelector('.map-shell').requestFullscreen();
  map.resize();
});
document.addEventListener('fullscreenchange', () => map.resize());

const compassIcon = document.querySelector('.compass-icon');
const updateCompass = () => {
  compassIcon.style.transform = `rotate(${-map.getBearing()}deg)`;
};
map.on('rotate', updateCompass);
updateCompass();
document.getElementById('compass').addEventListener('click', () => map.resetNorth());

// Trạng thái chọn nút minh họa giao diện, không bật/tắt lớp dữ liệu.
document.querySelectorAll('.layer-chip').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.layer-chip').forEach(item => {
      const active = item === button;
      item.classList.toggle('active', active);
      item.setAttribute('aria-pressed', String(active));
    });
  });
});

// Tìm kiếm thực tế sẽ do lõi chương trình kết nối; không giả lập kết quả.
const search = document.getElementById('search');
const searchHint = document.getElementById('searchHint');
document.getElementById('searchButton').addEventListener('click', () => {
  searchHint.textContent = search.value.trim()
    ? 'Tìm kiếm dữ liệu sẽ được kết nối bởi chương trình chính.'
    : 'Nhập tên địa điểm để tìm trong dữ liệu bản đồ';
});
