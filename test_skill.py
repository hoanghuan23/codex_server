"""Đọc Excel -> gửi dữ liệu + tên skill -> nhận JSON mã nguồn ba file web
-> kiểm tra lại đầu ra web bằng scripts/validate.py của skill.

Chạy: python3 test_skill.py [duong_dan_excel] [--sheet TEN_SHEET] [--no-samples] [--offline] [--debug]
Yêu cầu: pip install requests python-dotenv openpyxl

Biến môi trường (.env):
  CODEX_API_TOKEN  (bắt buộc)
  CODEX_API_URL    (mặc định http://127.0.0.1:8000/analyze)
  CODEX_MODEL      (mặc định gpt-5.6-luna)
  CODEX_TIMEOUT    (giây, mặc định 900)
  SKILL_DIR        (tùy chọn: đường dẫn thư mục skill nếu script không tự tìm thấy)

Đầu ra nằm trong output_skill_map/job_<thời gian>/:
  index.html, app.js, style.css: ứng dụng web
Chỉ khi --debug: lưu thêm input.json, request.json, raw_response.txt trong thư mục debug/.
--no-samples: chỉ gửi metadata; trang phải báo thiếu dữ liệu thay vì vẽ dữ liệu giả.
Mặc định: chỉ bản đồ tương tác; được tìm nguồn địa lý công khai trên mạng.
--offline: không tra cứu hay tự thêm tài nguyên mạng mới vào trang.
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, time
from pathlib import Path

import requests
from dotenv import load_dotenv
from openpyxl import load_workbook

load_dotenv()
BASE = Path(__file__).resolve().parent
OUTPUT = BASE / 'output_skill_map'
URL = os.getenv('CODEX_API_URL', 'http://127.0.0.1:8000/analyze')
MODEL = os.getenv('CODEX_MODEL', 'gpt-5.6-luna')
TIMEOUT = float(os.getenv('CODEX_TIMEOUT', '900'))

DEFAULT_SHEET = 'dữ liệu ô nhiễm'   # sheet ưu tiên nếu có; không có thì lấy sheet nhiều dòng nhất
HEAD_ROWS = 5            # số dòng đầu đưa vào profile.head
SAMPLE_N = 5             # số mẫu mỗi cột
DISTINCT_MAX = 300       # đưa distinctValues nếu số giá trị phân biệt <= ngưỡng này
CATEGORY_MAX = 12        # đưa categoryValues cho cột text nếu số nhóm <= ngưỡng này
UNIQUE_CAP = 1000        # uniqueCount tối đa báo cáo
COMMA_DECIMAL = re.compile(r'^-?\d+,\d+$')
SUPPORTED_CHARTS = ['choropleth', 'point', 'map_line', 'arc_flow']


# ---------------------------------------------------------------- tìm skill
def find_skill():
    """Tìm skill có hướng dẫn, validator và helper đầu ra web."""
    if os.getenv('SKILL_DIR'):
        roots = [Path(os.environ['SKILL_DIR'])]
    else:
        roots = [BASE] + [BASE / s for s in ('.agents/skills', '.codex/skills', 'skills')]
    for root in roots:
        if not root.is_dir():
            continue
        for d in [root] + sorted(p for p in root.iterdir() if p.is_dir()):
            if all((d / file).is_file() for file in
                   ('SKILL.md', 'scripts/validate.py', 'scripts/web_output.py')):
                return d.resolve()
    raise FileNotFoundError('Không tìm thấy skill hỗ trợ web (cần SKILL.md, scripts/validate.py, '
                            'scripts/web_output.py). '
                            'Đặt SKILL_DIR trong .env nếu skill nằm ở nơi khác.')


# ---------------------------------------------------------------- đọc Excel
def clean_headers(row):
    seen, out = {}, []
    for i, v in enumerate(row):
        h = str(v).strip().replace('\n', ' ') if v is not None and str(v).strip() else f'column_{i}'
        seen[h] = seen.get(h, 0) + 1
        out.append(h if seen[h] == 1 else f'{h} ({seen[h]})')
    return out


def has_value(v):
    return v is not None and not (isinstance(v, str) and not v.strip())


def read_table(path, sheet=None):
    """Trả (tên sheet, headers, các dòng dữ liệu). Hàng đầu là tên cột."""
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        names = wb.sheetnames
        if sheet:
            if sheet not in names:
                raise ValueError(f'Không có sheet "{sheet}". Các sheet: {names}')
            chosen = sheet
        elif DEFAULT_SHEET in names:
            chosen = DEFAULT_SHEET
        else:
            chosen = max(names, key=lambda n: sum(1 for r in wb[n].values if any(has_value(c) for c in r)))
        rows = [list(r) for r in wb[chosen].values]
    finally:
        wb.close()
    if not rows:
        raise ValueError(f'Sheet "{chosen}" rỗng')
    headers = clean_headers(rows[0])
    width = len(headers)
    data = [(r + [None] * width)[:width] for r in rows[1:] if any(has_value(c) for c in r)]
    return chosen, headers, data


# ------------------------------------------------------------------ profile
def jsonable(v):
    if isinstance(v, datetime):
        return v.date().isoformat() if v.time() == time(0) else v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


def to_dt(v):
    return v if isinstance(v, datetime) else datetime(v.year, v.month, v.day)


def temporal_granularity(vals):
    ds = {to_dt(v) for v in vals}
    if len(ds) > 1 and all(d.month == 1 and d.day == 1 for d in ds):
        return 'year'
    if len(ds) > 1 and all(d.day == 1 for d in ds):
        return 'month'
    return 'day'


def describe(name, values, with_samples):
    vals = [v for v in values if has_value(v)]
    n = len(values)
    is_num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    comma = False
    if vals and all(isinstance(v, date) for v in vals):          # datetime cũng là date
        typ = 'date'
    elif vals and all(is_num(v) for v in vals):
        typ = 'number'
    elif vals and all(isinstance(v, str) and COMMA_DECIMAL.match(v.strip()) for v in vals):
        typ, comma = 'number', True
    else:
        typ = 'text'

    distinct = list(dict.fromkeys(jsonable(v) for v in vals))
    col = {
        'name': name,
        'inferredType': typ,
        'nullPct': round(100 * (n - len(vals)) / n, 1) if n else 100.0,
        'uniqueCount': min(len(distinct), UNIQUE_CAP),
        'uniqueCountCapped': len(distinct) > UNIQUE_CAP,
        'commaDecimal': comma,
    }
    if typ == 'number':
        nums = [float(v.strip().replace(',', '.')) if comma else v for v in vals]
        col['min'], col['max'] = min(nums), max(nums)
    elif typ == 'date':
        col['min'], col['max'] = jsonable(min(vals, key=to_dt)), jsonable(max(vals, key=to_dt))
        col['temporalGranularity'] = temporal_granularity(vals)
    if with_samples:
        col['samples'] = distinct[:SAMPLE_N]
        if len(distinct) <= DISTINCT_MAX:
            col['distinctValues'] = distinct
        if typ == 'text' and len(distinct) <= CATEGORY_MAX:
            col['categoryValues'] = distinct
    return col


def build_profile(headers, data, with_samples):
    """Metadata cột giúp AI đọc records; không thay thế dữ liệu thực để vẽ."""
    profile = {
        'rowCount': len(data),
        'samplesIncluded': with_samples,
        'columns': [describe(h, [r[i] for r in data], with_samples) for i, h in enumerate(headers)],
    }
    if with_samples:
        profile['head'] = [{h: jsonable(r[i]) for i, h in enumerate(headers)} for r in data[:HEAD_ROWS]]
    return profile


# ------------------------------------------------------------- nhận và kiểm file
def load_web_helper(skill_dir):
    spec = importlib.util.spec_from_file_location('thematic_web_output',
                                                skill_dir / 'scripts' / 'web_output.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_local(skill_dir, output_dir):
    r = subprocess.run(
        [sys.executable, str(skill_dir / 'scripts' / 'validate.py'),
         '--result', str(output_dir)],
        capture_output=True, text=True, encoding='utf-8',
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    print(r.stdout.strip())
    if r.stderr.strip():
        print(r.stderr.strip())
    return r.returncode == 0


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description='Excel -> HTML/JS/CSS qua skill thematic-map-designer')
    ap.add_argument('excel', nargs='?', default=str(BASE / 'test dữ liệu khu vực.xlsx'))
    ap.add_argument('--sheet', help='tên sheet dữ liệu (mặc định: tự chọn)')
    ap.add_argument('--no-samples', action='store_true', help='không gửi giá trị mẫu (samplesIncluded=false)')
    ap.add_argument('--offline', action='store_true', help='tắt tìm nguồn địa lý và thêm tài nguyên mạng')
    ap.add_argument('--debug', action='store_true', help='lưu input, request JSON, phản hồi vào debug/')
    a = ap.parse_args()

    excel = Path(a.excel).resolve()
    if not excel.is_file():
        raise FileNotFoundError(f'Không tìm thấy Excel: {excel}')
    token = os.getenv('CODEX_API_TOKEN')
    if not token:
        raise RuntimeError('Thiếu CODEX_API_TOKEN trong môi trường/.env')
    skill_dir = find_skill()

    sheet, headers, data = read_table(excel, a.sheet)
    profile = build_profile(headers, data, with_samples=not a.no_samples)

    job = OUTPUT / ('job_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    job.mkdir(parents=True, exist_ok=True)
    helper = load_web_helper(skill_dir)
    input_data = {'profile': profile, 'supportedCharts': SUPPORTED_CHARTS,
                  'webOptions': {'layout': 'map-only', 'allowOnlineLookup': not a.offline},
                  'source': {'fileName': excel.name, 'sheetName': sheet}}
    if not a.no_samples:
        input_data['records'] = [{h: jsonable(row[i]) for i, h in enumerate(headers)} for row in data]
    input_json = json.dumps(input_data, ensure_ascii=False, indent=2)
    request_data = {'skill': 'thematic-map-designer', 'mode': 'analysis',
                    'output_format': 'web', 'input': input_data, 'model': MODEL}

    print('Nguồn :', excel)
    print('Sheet :', sheet, f'({len(data)} dòng, {len(headers)} cột)')
    print('Skill :', skill_dir)
    print('Job   :', job)
    if a.no_samples:
        print('Chỉ gửi metadata; đầu ra không có bản ghi để vẽ bản đồ đầy đủ.')
    if a.debug:
        debug_dir = job / 'debug'
        debug_dir.mkdir()
        (debug_dir / 'input.json').write_text(input_json, encoding='utf-8')
        (debug_dir / 'request.json').write_text(
            json.dumps(request_data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Gọi skill:', request_data['skill'])
    response = requests.post(URL, headers={'X-API-Key': token},
                             json=request_data, timeout=TIMEOUT)
    print('HTTP status:', response.status_code)
    print('Response body:', response.text)
    response.raise_for_status()
    payload = response.json()
    if not payload.get('success'):
        raise RuntimeError('Codex thất bại: ' + str(payload)[:1200])
    raw = payload.get('result', '')
    if not isinstance(raw, str):
        raise ValueError('Trường result từ server phải là chuỗi.')
    if a.debug:
        (debug_dir / 'raw_response.txt').write_text(raw, encoding='utf-8')
    try:
        files = helper.parse_web_files(raw)
    except ValueError as exc:
        raise ValueError(f'Codex chưa tạo đủ file web: {exc} '
                         'Chạy với --debug để lưu phản hồi phục vụ kiểm tra.') from exc
    for name in helper.WEB_FILES:
        (job / name).write_text(files[name], encoding='utf-8')
    print('Đã lưu ba file web từ phản hồi của Codex.')
    print('\n== Kiểm tra đầu ra web ==')
    if not validate_local(skill_dir, job):
        raise RuntimeError(f'Đầu ra web chưa hợp lệ. Xem {job}')
    for name in helper.WEB_FILES:
        print('Đã tạo:', job / name)
    print('\nMở trang:', job / 'index.html')


if __name__ == '__main__':
    main()
