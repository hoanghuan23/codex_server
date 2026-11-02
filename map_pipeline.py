"""Client hai bước: phân loại dữ liệu, gọi skill, kiểm tra và công bố ba file web."""
import importlib.util
import json
import math
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

import requests
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from map_input import MapInput


BASE = Path(__file__).resolve().parent
LIBERTY_STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty'
CHART_LABELS = {'choropleth': 'Polygon', 'point': 'Point', 'map_line': 'Line',
                'arc_flow': 'Arc Flow 3D'}
Chart = Literal['choropleth', 'point', 'map_line', 'arc_flow']


class PipelineError(Exception):
    """Thông báo có thể hiển thị trực tiếp trên giao diện."""


@dataclass(frozen=True)
class Settings:
    api_url: str = 'http://127.0.0.1:8000/analyze'
    api_token: str = ''
    timeout: float = 900
    output_root: Path = BASE
    skill_dir: Path = BASE / 'thematic-map-designer'
    max_upload_bytes: int = 10 * 1024 * 1024

    @classmethod
    def from_env(cls):
        timeout = float(os.getenv('CODEX_TIMEOUT', '900'))
        upload_mb = float(os.getenv('MAP_MAX_UPLOAD_MB', '10'))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('CODEX_TIMEOUT phải là số giây lớn hơn 0.')
        if not math.isfinite(upload_mb) or upload_mb <= 0:
            raise ValueError('MAP_MAX_UPLOAD_MB phải lớn hơn 0.')
        return cls(api_url=os.getenv('CODEX_API_URL', cls.api_url),
                   api_token=os.getenv('CODEX_API_TOKEN', ''), timeout=timeout,
                   output_root=Path(os.getenv('MAP_OUTPUT_DIR', str(BASE))).resolve(),
                   skill_dir=Path(os.getenv('SKILL_DIR', str(cls.skill_dir))).resolve(),
                   max_upload_bytes=int(upload_mb * 1024 * 1024))


class Classification(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    candidates: list[Chart]
    selectedChart: Chart | None
    reason: str
    missingData: list[str]
    selectedSheet: str | None = None

    @model_validator(mode='after')
    def check_selection(self):
        if not self.reason:
            raise ValueError('Thiếu lý do chọn loại bản đồ.')
        if len(set(self.candidates)) != len(self.candidates):
            raise ValueError('Danh sách loại bản đồ bị lặp.')
        if self.selectedChart is not None and self.selectedChart not in self.candidates:
            raise ValueError('Loại đã chọn không thuộc danh sách có thể dựng.')
        if self.selectedChart is None and not any(item.strip() for item in self.missingData):
            raise ValueError('Cần nêu dữ liệu thiếu khi không chọn được bản đồ.')
        return self


def parse_classification(raw, document):
    try:
        # Chấp nhận hàng rào JSON đơn giản, không chấp nhận văn xuôi kèm theo.
        raw = re.sub(r'^```(?:json)?\s*\n([\s\S]*?)\n```\s*$', r'\1', raw.strip(), flags=re.I)
        result = Classification.model_validate_json(raw)
    except (ValidationError, TypeError, ValueError) as exc:
        raise PipelineError('AI trả kết quả phân tích không hợp lệ. Hãy thử chạy lại.') from exc
    sheets = document.data.get('sheets')
    if sheets and result.selectedChart is not None:
        if result.selectedSheet not in {sheet['sheet'] for sheet in sheets}:
            raise PipelineError('AI chưa chọn đúng sheet dữ liệu trong Excel. Hãy thử chạy lại.')
    elif not sheets and result.selectedSheet is not None:
        raise PipelineError('AI trả tên sheet cho file không phải Excel.')
    selected_sheet = document.data.get('source', {}).get('sheetName')
    if selected_sheet and result.selectedChart is not None and result.selectedSheet != selected_sheet:
        raise PipelineError('AI chọn khác sheet bạn đã chỉ định. Hãy thử chạy lại.')
    return result


def generation_request(document, classification):
    # Chỉ bổ sung tùy chọn, không sửa records, geometry hoặc các ô Excel gốc.
    data = {**document.data, 'source': dict(document.data['source']),
            'supportedCharts': [classification.selectedChart],
            'webOptions': {'layout': 'map-only', 'allowOnlineLookup': True}}
    if classification.selectedSheet is not None:
        data['source']['sheetName'] = classification.selectedSheet
    return {'skill': 'thematic-map-designer', 'mode': document.mode,
            'output_format': 'web', 'input': data}


class MapClient:
    def __init__(self, settings):
        self.settings = settings

    def call(self, payload):
        if not self.settings.api_token:
            raise PipelineError('Thiếu CODEX_API_TOKEN trong môi trường hoặc file .env.')
        try:
            response = requests.post(self.settings.api_url,
                                     headers={'X-API-Key': self.settings.api_token},
                                     json=payload, timeout=self.settings.timeout)
        except requests.Timeout as exc:
            raise PipelineError(f'API hết thời gian chờ ({self.settings.timeout:g} giây).') from exc
        except requests.RequestException as exc:
            raise PipelineError('Không kết nối được API dựng bản đồ. Kiểm tra server và CODEX_API_URL.') from exc
        if not response.ok:
            message = ('API từ chối xác thực. Kiểm tra CODEX_API_TOKEN.' if response.status_code == 401
                       else f'API dựng bản đồ trả lỗi HTTP {response.status_code}.')
            raise PipelineError(message)
        try:
            payload = response.json()
        except ValueError as exc:
            raise PipelineError('API không trả JSON hợp lệ.') from exc
        if not isinstance(payload, dict) or payload.get('success') is not True:
            raise PipelineError('API báo không thực hiện được yêu cầu.')
        raw = payload.get('result')
        if not isinstance(raw, str) or not raw.strip():
            raise PipelineError('API trả kết quả rỗng hoặc sai định dạng.')
        return raw

    def classify(self, document):
        prompt = (BASE / 'prompts' / 'classify-input.txt').read_text(encoding='utf-8')
        raw = self.call({'prompt': prompt + '\n\nDỮ LIỆU FILE (JSON):\n' +
                         json.dumps(document.data, ensure_ascii=False, allow_nan=False)})
        return parse_classification(raw, document)

    def generate(self, document, classification):
        return self.call(generation_request(document, classification))


def load_web_helper(skill_dir):
    path = skill_dir / 'scripts' / 'web_output.py'
    if not path.is_file():
        raise PipelineError('Không tìm thấy scripts/web_output.py. Kiểm tra SKILL_DIR.')
    spec = importlib.util.spec_from_file_location('map_ui_web_output', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WebReport:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def err(self, path, message):
        self.errors.append(f'{path}: {message}')

    def warn(self, path, message):
        self.warnings.append(f'{path}: {message}')

    def note(self, message):
        pass


def output_slug(filename):
    stem = Path(filename).stem.replace('đ', 'd').replace('Đ', 'D')
    stem = unicodedata.normalize('NFKD', stem).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-zA-Z0-9]+', '_', stem).strip('_')[:60] or 'du_lieu'


def publish_output(raw, filename, job_id, settings):
    helper = load_web_helper(settings.skill_dir)
    try:
        files = helper.parse_web_files(raw)
    except ValueError as exc:
        raise PipelineError('Mã bản đồ không hợp lệ: ' + str(exc)) from exc
    if LIBERTY_STYLE_URL not in files['app.js']:
        raise PipelineError('Mã bản đồ chưa sử dụng nền Liberty theo yêu cầu. Hãy thử chạy lại.')
    settings.output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%Y%m%d_%H%M%S')
    output = settings.output_root / f'output_{output_slug(filename)}_{timestamp}_{job_id}'
    with tempfile.TemporaryDirectory(prefix='.map-build-', dir=settings.output_root) as temporary:
        staging = Path(temporary) / 'web'
        staging.mkdir()
        for name, content in files.items():
            (staging / name).write_text(content, encoding='utf-8')
        report = WebReport()
        helper.validate_web(report, staging)
        if report.errors:
            raise PipelineError('Kiểm tra mã bản đồ thất bại: ' + '\n'.join(report.errors))
        # Cùng filesystem: chỉ để lộ output_* sau khi kiểm tra toàn bộ thành công.
        staging.rename(output)
    return output, report.warnings
