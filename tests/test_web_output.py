"""Kiểm tra hợp đồng file và luồng Excel -> file web, không gọi API thật."""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from openpyxl import Workbook

BASE = Path(__file__).resolve().parents[1]
SKILL = BASE / 'thematic-map-designer'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


web = load_module('web_output_test', SKILL / 'scripts' / 'web_output.py')
runner = load_module('skill_runner_test', BASE / 'test_skill.py')
FILES = {
    'index.html': '<!DOCTYPE html>\n<html lang="vi"><head><meta charset="utf-8">'
                  '<title>Bản đồ</title><link rel="stylesheet" href="./style.css">'
                  '<script src="./app.js" defer></script></head><body><main id="map">'
                  'Chưa có geometry</main></body></html>\n',
    'app.js': 'const records = [{"Khu vực": "Huế", "Giá trị": 0}, {"Khu vực": "Đà Nẵng", "Giá trị": null}];\n'
              'document.querySelector("#map").textContent = `Có ${records.length} bản ghi`;\n',
    'style.css': 'body { margin: 0; font-family: sans-serif; }\n',
}


def file_blocks(files):
    return '\n'.join(f'```{web.FILE_LANGUAGES[name]} filename={name}\n{content}```'
                     for name, content in files.items())


class FileContractTests(unittest.TestCase):
    def test_json_round_trip_preserves_code_and_unicode(self):
        self.assertEqual(web.parse_web_files(json.dumps(FILES, ensure_ascii=False)), FILES)

    def test_json_parser_preserves_legacy_file_block_support(self):
        self.assertEqual(web.parse_web_files(file_blocks(FILES)), FILES)

    def test_json_rejects_invalid_file_packages(self):
        valid = json.dumps(FILES)
        invalid = [None, '', '[]', '{"suggestions": []}',
                   valid + '\nGiải thích', 'Giải thích\n' + valid,
                   json.dumps({**FILES, 'extra.txt': 'extra'}),
                   json.dumps({k: v for k, v in FILES.items() if k != 'app.js'}),
                   json.dumps({**FILES, 'app.js': None}),
                   json.dumps({**FILES, 'app.js': 3}),
                   json.dumps({**FILES, 'style.css': '  '}),
                   valid.replace('"app.js":', '"../app.js":'),
                   '{"app.js":"duplicate",' + valid[1:]]
        for raw in invalid:
            with self.subTest(raw=str(raw)[:80]), self.assertRaises(ValueError):
                web.parse_web_files(raw)

    def test_response_round_trip_preserves_code_and_unicode(self):
        self.assertEqual(web.parse_file_blocks(file_blocks(FILES)), FILES)
        self.assertEqual(web.parse_file_blocks(file_blocks(FILES).replace('\n', '\r\n')), FILES)

    def test_rejects_incomplete_ambiguous_or_unsafe_responses(self):
        valid = file_blocks(FILES)
        invalid = [json.dumps(FILES), valid + '\nGiải thích', 'Giải thích\n' + valid,
                   valid + '\n' + valid, file_blocks({'index.html': FILES['index.html']}),
                   valid.replace('filename=app.js', 'filename=../app.js'),
                   valid.replace('```javascript', '```css'),
                   valid.replace(FILES['style.css'], '\n')]
        for raw in invalid:
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                web.parse_file_blocks(raw)

    def validate(self, files):
        with tempfile.TemporaryDirectory() as output:
            for name, content in files.items():
                (Path(output) / name).write_text(content, encoding='utf-8')
            return subprocess.run([sys.executable, str(SKILL / 'scripts' / 'validate.py'),
                                   '--result', output],
                                  capture_output=True, text=True)

    def test_validator_accepts_complete_web_output(self):
        result = self.validate(FILES)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_rejects_broken_artifacts(self):
        cases = [
            {k: v for k, v in FILES.items() if k != 'style.css'},
            {**FILES, 'style.css': ''},
            {**FILES, 'app.js': 'const = ;'},
            {**FILES, 'index.html': FILES['index.html'].replace('./style.css', './missing.css')},
            {**FILES, 'index.html': FILES['index.html'].replace(' defer', '')},
            {**FILES, 'index.html': FILES['index.html'].replace('</body>', '<script>alert(1)</script></body>')},
            {**FILES, 'index.html': FILES['index.html'].replace('</body>', '<img src="http://[" /></body>')},
        ]
        for files in cases:
            with self.subTest(files=list(files)):
                result = self.validate(files)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_validator_rejects_configuration_file_instead_of_web_directory(self):
        with tempfile.TemporaryDirectory() as output:
            result = Path(output) / 'result.json'
            result.write_text('{"suggestions": []}', encoding='utf-8')
            checked = subprocess.run([sys.executable, str(SKILL / 'scripts' / 'validate.py'),
                                      '--result', str(result)],
                                     capture_output=True, text=True)
            self.assertEqual(checked.returncode, 1, checked.stdout + checked.stderr)

    def test_validator_rejects_removed_configuration_flags(self):
        with tempfile.TemporaryDirectory() as output:
            checked = subprocess.run([sys.executable, str(SKILL / 'scripts' / 'validate.py'),
                                      '--format', 'json', '--result', output],
                                     capture_output=True, text=True)
            self.assertEqual(checked.returncode, 2, checked.stdout + checked.stderr)


class ExcelOutputTests(unittest.TestCase):
    def run_pipeline(self, root, flags=(), raw=None):
        excel = root / 'dữ liệu.xlsx'
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['Khu vực', 'Giá trị'])
        sheet.append(['Huế', 0])
        sheet.append(['Đà Nẵng', None])
        workbook.save(excel)
        workbook.close()
        captured = {}

        def fake_post(url, *, headers, timeout, **kwargs):
            captured['request'] = kwargs['json']
            captured['input'] = captured['request']['input']
            captured['job'] = next((root / 'output').iterdir())
            response = Mock(status_code=200)
            response.json.return_value = {'success': True, 'result': raw if raw is not None else
                                          json.dumps(FILES, ensure_ascii=False)}
            return response

        with patch.object(runner, 'OUTPUT', root / 'output'), \
                patch.object(runner, 'find_skill', return_value=SKILL), \
                patch.object(runner.requests, 'post', side_effect=fake_post), \
                patch.dict(os.environ, {'CODEX_API_TOKEN': 'offline-test-token'}), \
                patch.object(sys, 'argv', ['test_skill.py', str(excel), *flags]), \
                contextlib.redirect_stdout(io.StringIO()):
            runner.main()
        return captured

    def test_read_only_server_response_becomes_three_real_files(self):
        with tempfile.TemporaryDirectory() as directory:
            captured = self.run_pipeline(Path(directory))
            job = captured['job']
            self.assertEqual({p.name for p in job.iterdir()}, set(web.WEB_FILES))
            for name, content in FILES.items():
                self.assertEqual((job / name).read_text(encoding='utf-8'), content)
            self.assertEqual(captured['input']['records'], [
                {'Khu vực': 'Huế', 'Giá trị': 0}, {'Khu vực': 'Đà Nẵng', 'Giá trị': None}])
            self.assertEqual(captured['input']['webOptions'],
                             {'layout': 'map-only', 'allowOnlineLookup': True})
            self.assertEqual(captured['input']['supportedCharts'],
                             ['choropleth', 'point', 'map_line', 'arc_flow'])

    def test_legacy_file_block_response_still_becomes_three_files(self):
        with tempfile.TemporaryDirectory() as directory:
            captured = self.run_pipeline(Path(directory), raw=file_blocks(FILES))
            for name, content in FILES.items():
                self.assertEqual((captured['job'] / name).read_text(encoding='utf-8'), content)

    def test_offline_keeps_records_but_disables_online_lookup(self):
        with tempfile.TemporaryDirectory() as directory:
            captured = self.run_pipeline(Path(directory), flags=['--offline'])
            self.assertEqual(captured['input']['webOptions'],
                             {'layout': 'map-only', 'allowOnlineLookup': False})
            self.assertEqual(len(captured['input']['records']), 2)

    def test_client_sends_skill_and_data_without_prompt_or_local_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            captured = self.run_pipeline(Path(directory))
            request = captured['request']
            self.assertEqual(set(request), {'skill', 'mode', 'output_format', 'input', 'model'})
            self.assertEqual(request['skill'], 'thematic-map-designer')
            self.assertEqual(request['mode'], 'analysis')
            self.assertEqual(request['output_format'], 'web')
            self.assertNotIn(str(directory), json.dumps(request, ensure_ascii=False))

    def test_no_samples_omits_records_and_values(self):
        with tempfile.TemporaryDirectory() as directory:
            captured = self.run_pipeline(Path(directory), flags=['--no-samples'])
            data = captured['input']
            self.assertNotIn('records', data)
            self.assertFalse(data['profile']['samplesIncluded'])
            self.assertNotIn('head', data['profile'])
            self.assertNotIn('Huế', json.dumps(data, ensure_ascii=False))

    def test_debug_files_are_opt_in_and_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            captured = self.run_pipeline(Path(directory), flags=['--debug'])
            job = captured['job']
            self.assertEqual({p.name for p in job.iterdir()}, set(web.WEB_FILES) | {'debug'})
            self.assertEqual({p.name for p in (job / 'debug').iterdir()},
                             {'input.json', 'request.json', 'raw_response.txt'})
            self.assertEqual(json.loads((job / 'debug/request.json').read_text()),
                             captured['request'])

    def test_configuration_json_is_not_treated_as_successful_web_output(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                self.run_pipeline(Path(directory), raw='{"suggestions": []}')
            jobs = list((Path(directory) / 'output').iterdir())
            self.assertEqual(len(jobs), 1)
            self.assertEqual(list(jobs[0].iterdir()), [])


if __name__ == '__main__':
    unittest.main()
