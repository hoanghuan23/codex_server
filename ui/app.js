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
const excelPanel = document.querySelector('#excel-selection');
const excelStatus = document.querySelector('#excel-status');
const sheetSelect = document.querySelector('#sheet-select');
const labels = {choropleth: 'Polygon', point: 'Point', map_line: 'Line', arc_flow: 'Arc Flow 3D'};
const stages = ['reading', 'analyzing', 'generating', 'validating', 'completed'];
let activeJob = null;
let busy = false;
let lastStage = -1;
let sheetNames = [];
let excelLoading = false;
let selectionReady = false;
let previewRequest = 0;
let previewController = null;

const isExcel = () => /\.xlsx$/i.test(fileInput.files[0]?.name || '');

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = !message;
}

function setBusy(value) {
  busy = value;
  fileInput.disabled = value || Boolean(activeJob);
  fileZone.classList.toggle('busy', fileInput.disabled);
  const pending = value || excelLoading;
  sheetSelect.disabled = value || Boolean(activeJob) || excelLoading || !sheetNames.length;
  button.disabled = pending || (!activeJob && (!fileInput.files.length || (isExcel() && !selectionReady)));
  buttonLabel.textContent = value ? 'Đang xử lý…' : activeJob ? 'Kiểm tra lại' : excelLoading ? 'Đang đọc sheet…' : 'Tạo bản đồ';
  spinner.hidden = !pending;
  arrow.hidden = pending;
  form.setAttribute('aria-busy', String(pending));
}

async function updateFile() {
  previewController?.abort();
  const requestId = ++previewRequest;
  sheetNames = [];
  selectionReady = false;
  excelLoading = false;
  sheetSelect.replaceChildren(new Option('Chọn sheet…', ''));
  excelStatus.hidden = true;
  excelPanel.hidden = !isExcel();
  const file = fileInput.files[0];
  fileTitle.textContent = file ? file.name : 'Chọn file dữ liệu';
  fileHint.textContent = file ? `${new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 1}).format(file.size / 1024)} KB · Nhấn để chọn file khác` : 'hoặc kéo thả một file vào đây';
  if (!activeJob) {
    showError('');
    result.hidden = true;
    progress.hidden = true;
  }
  setBusy(false);
  if (!isExcel()) return;
  excelLoading = true;
  excelStatus.textContent = 'Đang đọc tên sheet…';
  excelStatus.hidden = false;
  setBusy(false);
  previewController = new AbortController();
  try {
    const body = new FormData();
    body.append('file', file);
    const data = await readResponse(await fetch('/api/excel/sheets', {method: 'POST', body, signal: previewController.signal}));
    if (requestId !== previewRequest) return;
    if (!Array.isArray(data.sheets) || !data.sheets.length || data.sheets.some(name => typeof name !== 'string')) {
      throw new Error('File Excel không có sheet để chọn.');
    }
    sheetNames = data.sheets;
    sheetSelect.replaceChildren(new Option('Chọn sheet…', ''), ...sheetNames.map(name => new Option(name, name)));
  } catch (error) {
    if (requestId !== previewRequest || error.name === 'AbortError') return;
    showError(error.status === 404
      ? 'Không tải được tên sheet. Hãy khởi động lại giao diện và mở http://127.0.0.1:8001.'
      : error.message);
  } finally {
    if (requestId === previewRequest) {
      excelLoading = false;
      excelStatus.hidden = true;
      setBusy(busy);
    }
  }
}

sheetSelect.addEventListener('change', () => {
  showError('');
  result.hidden = true;
  progress.hidden = true;
  selectionReady = sheetNames.includes(sheetSelect.value);
  setBusy(busy);
});

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
  if (busy || excelLoading || (!activeJob && (!fileInput.files.length || (isExcel() && !selectionReady)))) return;
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
      if (isExcel()) {
        body.append('selected_sheet', sheetSelect.value);
      }
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
