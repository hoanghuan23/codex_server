'use strict';

const form = document.querySelector('#upload-form');
const fileInput = document.querySelector('#data-file');
const fileZone = document.querySelector('#file-zone');
const fileTitle = document.querySelector('#file-title');
const fileHint = document.querySelector('#file-hint');
const button = document.querySelector('#create-button');
const buttonLabel = document.querySelector('#button-label');
const spinner = document.querySelector('#button-spinner');
const arrow = document.querySelector('#button-arrow');
const progress = document.querySelector('#progress');
const statusText = document.querySelector('#status-text');
const errorBox = document.querySelector('#error');
const result = document.querySelector('#result');
const labels = {choropleth: 'Polygon', point: 'Point', map_line: 'Line', arc_flow: 'Arc Flow 3D'};
const stages = ['reading', 'analyzing', 'generating', 'validating', 'completed'];
let activeJob = null;
let busy = false;
let lastStage = -1;

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = !message;
}

function setBusy(value) {
  busy = value;
  fileInput.disabled = value || Boolean(activeJob);
  fileZone.classList.toggle('busy', fileInput.disabled);
  button.disabled = value || (!activeJob && !fileInput.files.length);
  buttonLabel.textContent = value ? 'Đang xử lý…' : activeJob ? 'Kiểm tra lại' : 'Tạo bản đồ';
  spinner.hidden = !value;
  arrow.hidden = value;
  form.setAttribute('aria-busy', String(value));
}

function updateFile() {
  const file = fileInput.files[0];
  fileTitle.textContent = file ? file.name : 'Chọn file dữ liệu';
  fileHint.textContent = file ? `${new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 1}).format(file.size / 1024)} KB · Nhấn để chọn file khác` : 'hoặc kéo thả một file vào đây';
  if (!activeJob) {
    showError('');
    result.hidden = true;
    progress.hidden = true;
  }
  setBusy(false);
}

fileInput.addEventListener('change', updateFile);
for (const name of ['dragenter', 'dragover']) {
  fileZone.addEventListener(name, event => {
    event.preventDefault();
    if (!fileInput.disabled) fileZone.classList.add('dragging');
  });
}
for (const name of ['dragleave', 'drop']) {
  fileZone.addEventListener(name, event => {
    event.preventDefault();
    fileZone.classList.remove('dragging');
  });
}
fileZone.addEventListener('drop', event => {
  if (fileInput.disabled) return;
  if (event.dataTransfer.files.length !== 1) {
    showError('Vui lòng chọn một file mỗi lần.');
    return;
  }
  fileInput.files = event.dataTransfer.files;
  updateFile();
});

function render(job) {
  progress.hidden = false;
  statusText.textContent = job.message;
  const index = stages.indexOf(job.status);
  if (index !== -1) lastStage = index;
  for (const [i, step] of [...document.querySelectorAll('.steps li')].entries()) {
    step.classList.toggle('done', i < lastStage || job.status === 'completed');
    step.classList.toggle('current', i === lastStage && job.status !== 'completed');
  }
  if (job.analysis) {
    result.hidden = false;
    document.querySelector('#reason').textContent = job.analysis.reason;
    const label = document.querySelector('#chart-label');
    label.textContent = labels[job.analysis.selectedChart] || '';
    label.hidden = !label.textContent;
    document.querySelector('#result-title').textContent = job.status === 'completed'
      ? 'Bản đồ đã sẵn sàng' : job.status === 'needs_data' ? 'Cần bổ sung dữ liệu' : 'Kết quả phân tích';
    const missing = document.querySelector('#missing-data');
    missing.replaceChildren(...job.analysis.missingData.map(text => {
      const item = document.createElement('li');
      item.textContent = text;
      return item;
    }));
    missing.hidden = job.status !== 'needs_data' || !missing.childElementCount;
  }
  document.querySelector('#output-details').hidden = job.status !== 'completed';
  if (job.status === 'completed') {
    document.querySelector('#output-directory').textContent = job.output_dir;
    document.querySelector('#open-map').href = job.preview_url;
  }
  if (job.status === 'failed') showError(job.error || 'Không tạo được bản đồ.');
}

async function readResponse(response) {
  let data;
  try { data = await response.json(); }
  catch { throw new Error('Ứng dụng trả phản hồi không hợp lệ. Kiểm tra terminal rồi thử lại.'); }
  if (!response.ok) {
    // Nếu trang được tải lại khi đang chạy, tiếp tục theo dõi tác vụ cũ.
    if (response.status === 409 && data.detail && data.detail.job_id) return {job_id: data.detail.job_id};
    const detail = data.detail;
    const error = new Error(typeof detail === 'string' ? detail : detail?.message || `Có lỗi HTTP ${response.status}.`);
    error.status = response.status;
    throw error;
  }
  return data;
}

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function watchJob() {
  let failures = 0;
  while (activeJob) {
    let job;
    try {
      job = await readResponse(await fetch(`/api/jobs/${encodeURIComponent(activeJob)}`, {cache: 'no-store'}));
      failures = 0;
    } catch (error) {
      if (error.status === 404) {
        activeJob = null;
        throw error;
      }
      failures += 1;
      if (failures >= 3) throw error;
      statusText.textContent = 'Đang kết nối lại để kiểm tra tiến độ…';
      await delay(1500);
      continue;
    }
    render(job);
    if (['completed', 'failed', 'needs_data'].includes(job.status)) {
      activeJob = null;
      return;
    }
    await delay(1000);
  }
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (busy || (!activeJob && !fileInput.files.length)) return;
  showError('');
  setBusy(true);
  try {
    if (!activeJob) {
      lastStage = -1;
      result.hidden = true;
      document.querySelector('#output-details').hidden = true;
      progress.hidden = false;
      statusText.textContent = 'Đang tải file lên…';
      for (const step of document.querySelectorAll('.steps li')) step.classList.remove('done', 'current');
      const body = new FormData();
      body.append('file', fileInput.files[0]);
      const data = await readResponse(await fetch('/api/jobs', {method: 'POST', body}));
      activeJob = data.job_id;
    }
    await watchJob();
  } catch (error) {
    showError(error.message + (activeJob ? '\nNhấn “Kiểm tra lại” để tiếp tục theo dõi tác vụ.' : ''));
  } finally {
    setBusy(false);
  }
});
