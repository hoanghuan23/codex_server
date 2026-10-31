"""Kiểm thử API local và cả hai lời gọi AI, dùng upstream giả lập."""
import io
import json
import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from docx import Document
from fastapi.testclient import TestClient
from openpyxl import Workbook

from map_input import MapInput
from map_pipeline import (BASE, LIBERTY_STYLE_URL, MapClient, PipelineError, Settings,
                          parse_classification)
from ui_server import create_app


def classification(chart='point', sheet=None):
    return {'candidates': [chart] if chart else [], 'selectedChart': chart,
            'reason': 'Dữ liệu chứa vị trí và số liệu để dựng bản đồ kiểm thử.',
            'missingData': [] if chart else ['Cần bổ sung địa danh hoặc geometry.'],
            'selectedSheet': sheet}


FILES = {
    'index.html': '<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8">'
                  '<meta name="viewport" content="width=device-width, initial-scale=1">'
                  '<title>Bản đồ kiểm thử</title><link rel="stylesheet" href="./style.css">'
                  '<script src="./app.js" defer></script></head><body><div id="map"></div></body></html>',
    'style.css': 'body {margin: 0} #map {width: 100vw; height: 100vh}',
    'app.js': f'const style = "{LIBERTY_STYLE_URL}";\nconst records = [0, null, "Huế"];',
}


def response(raw, status=200):
    return Mock(ok=status < 400, status_code=status,
                json=Mock(return_value={'success': True, 'result': raw}))


class MapUITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.settings = Settings(api_token='test-only-secret', output_root=self.root)
        self.app = create_app(self.settings)
        self.client = TestClient(self.app, base_url='http://127.0.0.1')
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def submit(self, filename='dữ liệu.txt', contents='Huế có 0 điểm.'.encode()):
        return self.client.post('/api/jobs', files={'file': (filename, contents)})

    def wait(self, job_id):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            result = self.client.get(f'/api/jobs/{job_id}')
            self.assertEqual(result.status_code, 200)
            job = result.json()
            if job['status'] in ('completed', 'failed', 'needs_data'):
                return job
            time.sleep(.01)
        self.fail('Tác vụ giả lập không kết thúc trong 10 giây.')

    def fake_api(self, chart='point', sheet=None, files=None):
        return patch('map_pipeline.requests.post', side_effect=[
            response(json.dumps(classification(chart, sheet), ensure_ascii=False)),
            response(json.dumps(FILES if files is None else files, ensure_ascii=False))])

    def test_page_static_files_and_missing_jobs(self):
        page = self.client.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertIn('Chọn file. Tạo bản đồ.', page.text)
        self.assertNotIn(self.settings.api_token, page.text)
        self.assertEqual(self.client.get('/ui/style.css').status_code, 200)
        self.assertEqual(self.client.get('/ui/app.js').status_code, 200)
        self.assertEqual(self.client.get('/ui/.env').status_code, 404)
        self.assertEqual(self.client.get('/api/jobs/not-found').status_code, 404)

    def test_all_four_file_types_and_map_choices_reach_generation(self):
        workbook = Workbook()
        workbook.active.title = 'Bảng chính mới'
        workbook.active.append(['Nguồn', 'Đích', 'Lưu lượng'])
        workbook.active.append(['A', 'B', 0])
        reference = workbook.create_sheet('Tọa độ')
        reference.append(['Tên', 'lng', 'lat'])
        reference.append(['A', 107, 16])
        buffer = io.BytesIO()
        workbook.save(buffer)
        workbook.close()
        word = Document()
        word.add_paragraph('Số liệu kiểm thử: Việt Nam có giá trị 0 vào năm 2024.')
        docx = io.BytesIO()
        word.save(docx)
        line = {'type': 'LineString', 'coordinates': [[107, 16], [108, 17]]}
        fixtures = [
            ('bất kỳ.xlsx', buffer.getvalue(), 'arc_flow', 'Bảng chính mới', 'analysis'),
            ('báo cáo.docx', docx.getvalue(), 'choropleth', None, 'text_analysis'),
            ('tuyến.geojson', json.dumps(line).encode(), 'map_line', None, 'analysis'),
            ('điểm.TXT', 'Huế có 0 điểm.'.encode('utf-8-sig'), 'point', None, 'text_analysis'),
        ]
        for filename, contents, chart, sheet, mode in fixtures:
            with self.subTest(filename=filename), self.fake_api(chart, sheet) as upstream:
                created = self.submit(filename, contents)
                self.assertEqual(created.status_code, 202, created.text)
                job = self.wait(created.json()['job_id'])
                self.assertEqual(job['status'], 'completed', job)
                self.assertEqual(job['analysis']['selectedChart'], chart)
                self.assertEqual(upstream.call_count, 2)
                first = upstream.call_args_list[0].kwargs
                self.assertEqual(first['headers'], {'X-API-Key': 'test-only-secret'})
                self.assertEqual(first['timeout'], 900)
                self.assertEqual(set(first['json']), {'prompt'})
                generation = upstream.call_args_list[1].kwargs['json']
                self.assertEqual(generation['mode'], mode)
                self.assertEqual(generation['input']['supportedCharts'], [chart])
                self.assertEqual(generation['input']['source']['fileName'], filename)
                self.assertTrue(generation['input']['webOptions']['allowOnlineLookup'])
                if sheet:
                    self.assertEqual(generation['input']['source']['sheetName'], sheet)
                    self.assertEqual(len(generation['input']['sheets']), 2)
                    self.assertEqual(generation['input']['sheets'][0]['rows'][1][-1], 0)
                output = Path(job['output_dir'])
                self.assertEqual({p.name for p in output.iterdir()}, set(FILES))
                for name, content in FILES.items():
                    self.assertEqual((output / name).read_text(encoding='utf-8'), content)
                self.assertNotIn(self.settings.api_token, json.dumps(job))
                self.assertEqual(self.client.get(job['preview_url']).status_code, 200)
                self.assertEqual(self.client.get(job['preview_url'].replace('index.html', 'app.js')).status_code, 200)

    def test_repeated_filename_creates_distinct_outputs(self):
        outputs = []
        for _ in range(2):
            with self.fake_api():
                job = self.wait(self.submit().json()['job_id'])
                self.assertEqual(job['status'], 'completed', job)
                outputs.append(job['output_dir'])
        self.assertNotEqual(*outputs)
        self.assertTrue(all(Path(path).is_dir() for path in outputs))

    def test_missing_data_stops_before_generation_and_creates_no_output(self):
        with self.fake_api(chart=None) as upstream:
            job = self.wait(self.submit().json()['job_id'])
        self.assertEqual(job['status'], 'needs_data')
        self.assertIn('địa danh', job['error'])
        self.assertEqual(upstream.call_count, 1)
        self.assertIsNone(job['preview_url'])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_classification_and_artifacts_do_not_publish_output(self):
        cases = [
            [response('not JSON')],
            [response(json.dumps(classification())), response('{"app.js":"partial"}')],
            [response(json.dumps(classification())), response(json.dumps({**FILES, 'app.js': 'const = ; // ' + LIBERTY_STYLE_URL}))],
            [response(json.dumps(classification())), response(json.dumps({**FILES, 'app.js': 'const style="other";'}))],
            [response(json.dumps(classification())), response(json.dumps({**FILES, 'index.html': FILES['index.html'].replace('./style.css', './missing.css')}))],
        ]
        for responses in cases:
            with self.subTest(responses=len(responses)), patch('map_pipeline.requests.post', side_effect=responses):
                job = self.wait(self.submit().json()['job_id'])
                self.assertEqual(job['status'], 'failed', job)
                self.assertIsNone(job['output_dir'])
                self.assertEqual(list(self.root.iterdir()), [])
                self.assertEqual(self.client.get(f"/outputs/{job['job_id']}/index.html").status_code, 404)

    def test_upload_validation_and_origin_check(self):
        with patch('map_pipeline.requests.post') as upstream:
            self.assertEqual(self.submit('old.xls', b'file').status_code, 400)
            self.assertEqual(self.submit(contents=b'').status_code, 400)
            self.assertEqual(self.client.post('/api/jobs', files={'file': ('data.txt', b'text')},
                                             headers={'Origin': 'https://example.com'}).status_code, 403)
            self.assertEqual(self.client.get('/', headers={'Host': 'example.com'}).status_code, 400)
            upstream.assert_not_called()
        tiny_app = create_app(replace(self.settings, max_upload_bytes=3))
        with TestClient(tiny_app, base_url='http://localhost') as client:
            self.assertEqual(client.post('/api/jobs', files={'file': ('big.txt', b'1234')}).status_code, 413)
        no_token = create_app(replace(self.settings, api_token=''))
        with TestClient(no_token, base_url='http://localhost') as client:
            self.assertEqual(client.post('/api/jobs', files={'file': ('file.txt', b'text')}).status_code, 503)

    def test_reader_failure_never_calls_ai_and_next_job_can_run(self):
        with patch('map_pipeline.requests.post') as upstream:
            job = self.wait(self.submit('broken.xlsx', b'not Excel').json()['job_id'])
            self.assertEqual(job['status'], 'failed')
            upstream.assert_not_called()
        with self.fake_api():
            self.assertEqual(self.wait(self.submit().json()['job_id'])['status'], 'completed')

    def test_concurrent_upload_is_rejected_while_status_remains_available(self):
        entered, release = threading.Event(), threading.Event()

        def blocking_post(*args, **kwargs):
            if 'prompt' in kwargs['json']:
                entered.set()
                if not release.wait(5):
                    raise RuntimeError('Test did not release fake API')
                return response(json.dumps(classification()))
            return response(json.dumps(FILES))

        with patch('map_pipeline.requests.post', side_effect=blocking_post):
            try:
                created = self.submit()
                self.assertTrue(entered.wait(3))
                rejected = self.submit()
                self.assertEqual(rejected.status_code, 409)
                job_id = created.json()['job_id']
                self.assertEqual(rejected.json()['detail']['job_id'], job_id)
                self.assertEqual(self.client.get(f'/api/jobs/{job_id}').json()['status'], 'analyzing')
            finally:
                release.set()
            self.assertEqual(self.wait(job_id)['status'], 'completed')

    def test_upload_temporary_directories_are_cleaned_on_success_and_failure(self):
        original = tempfile.mkdtemp
        uploads = []

        def remember(*args, **kwargs):
            path = original(*args, **kwargs)
            if kwargs.get('prefix') == 'map-upload-':
                uploads.append(Path(path))
            return path

        with patch('ui_server.tempfile.mkdtemp', side_effect=remember):
            with self.fake_api():
                self.assertEqual(self.wait(self.submit().json()['job_id'])['status'], 'completed')
            self.assertEqual(self.wait(self.submit('broken.json', b'bad json').json()['job_id'])['status'], 'failed')
        self.assertEqual(len(uploads), 2)
        self.assertTrue(all(not path.exists() for path in uploads))

    def test_output_routes_never_serve_unapproved_files_or_symlinks(self):
        with self.fake_api():
            job = self.wait(self.submit().json()['job_id'])
        output = Path(job['output_dir'])
        (output / 'debug.txt').write_text('private', encoding='utf-8')
        prefix = f"/outputs/{job['job_id']}/"
        self.assertEqual(self.client.get(prefix + 'debug.txt').status_code, 404)
        self.assertEqual(self.client.get(prefix + '%2e%2e%2f.env').status_code, 404)
        (output / 'app.js').unlink()
        (output / 'app.js').symlink_to(BASE / '.env')
        self.assertEqual(self.client.get(prefix + 'app.js').status_code, 404)

    def test_api_errors_and_timeout_surface_without_token_exposure(self):
        for failure in [requests.Timeout('upstream timeout'), requests.ConnectionError('offline')]:
            with self.subTest(error=type(failure).__name__), patch('map_pipeline.requests.post', side_effect=failure):
                job = self.wait(self.submit().json()['job_id'])
                self.assertEqual(job['status'], 'failed')
                self.assertNotIn(self.settings.api_token, json.dumps(job))
        with patch('map_pipeline.requests.post', return_value=response('', 401)):
            job = self.wait(self.submit().json()['job_id'])
            self.assertIn('xác thực', job['error'])


class ClassificationTests(unittest.TestCase):
    def test_selection_must_match_candidates_and_real_sheet(self):
        document = MapInput('analysis', {'sheets': [{'sheet': 'Real', 'rows': [['Tên'], ['Huế']]}]})
        for value in [{**classification(), 'selectedSheet': 'Missing'},
                      {**classification(), 'selectedChart': 'map_line'},
                      {**classification(), 'candidates': ['point', 'point']},
                      {**classification(None), 'missingData': []}]:
            with self.subTest(value=value), self.assertRaises(PipelineError):
                parse_classification(json.dumps(value), document)

    def test_json_fence_and_geography_lookup_needed_are_accepted(self):
        document = MapInput('text_analysis', {'text': 'Dữ liệu theo vùng'})
        value = {**classification('choropleth'), 'missingData': ['Cần tra ranh giới địa lý.']}
        result = parse_classification('```json\n' + json.dumps(value) + '\n```', document)
        self.assertEqual(result.selectedChart, 'choropleth')

    def test_malformed_upstream_envelopes_are_rejected(self):
        client = MapClient(Settings(api_token='test-token'))
        for payload in [[], {}, {'success': False}, {'success': True, 'result': ''},
                        {'success': True, 'result': {'not': 'a string'}}]:
            with self.subTest(payload=payload), patch('map_pipeline.requests.post', return_value=Mock(ok=True, json=Mock(return_value=payload))):
                with self.assertRaises(PipelineError):
                    client.call({'prompt': 'test'})
