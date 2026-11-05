"""Kiểm tra API server với tiến trình Codex giả lập."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from httpx import ASGITransport, AsyncClient

import template_service


BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('api_test_server', BASE / 'server.py')
server = importlib.util.module_from_spec(spec)
with patch.dict(os.environ, {'CODEX_API_TOKEN': 'test-token'}):
    spec.loader.exec_module(server)


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncClient(
            transport=ASGITransport(app=server.app), base_url="http://testserver")
        self.addAsyncCleanup(self.client.aclose)
        self.process = Mock(returncode=0)
        self.process.communicate = AsyncMock(return_value=('Xin chào'.encode(), b''))
        self.workdirs = []

        async def execute(*command, **kwargs):
            directory = Path(kwargs['cwd'])
            self.assertTrue(directory.is_dir())
            self.assertEqual(list(directory.iterdir()), [])
            self.workdirs.append(directory)
            return self.process

        execute_patch = patch.object(server.asyncio, 'create_subprocess_exec',
                                     side_effect=execute)
        self.execute = execute_patch.start()
        self.addCleanup(execute_patch.stop)
        executable_patch = patch.object(server, 'resolve_codex_executable',
                                        return_value='codex-test.exe')
        self.executable = executable_patch.start()
        self.addCleanup(executable_patch.stop)
        token_patch = patch.object(server, 'API_TOKEN', 'test-token')
        token_patch.start()
        self.addCleanup(token_patch.stop)

    async def post(self, payload):
        return await self.client.post('/analyze', json=payload,
                                headers={'X-API-Key': 'test-token'})

    async def test_prompt_runs_with_client_model_and_cleans_temporary_directory(self):
        prompt = 'Phân tích nội dung tiếng Việt'
        model = 'client-selected-model'
        response = await self.post({'prompt': prompt, 'model': model})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'success': True, 'result': 'Xin chào'})
        command = self.execute.call_args.args
        self.assertEqual(command, (
            'codex-test.exe', '--search', 'exec', '--model', model,
            '--skip-git-repo-check', '--sandbox', 'read-only', '-'))
        self.assertEqual(self.execute.call_args.kwargs['stdin'],
                         server.asyncio.subprocess.PIPE)
        self.process.communicate.assert_awaited_once_with(input=prompt.encode('utf-8'))
        self.assertFalse(self.workdirs[0].exists())

    async def test_templates_list_and_fetch_mau_01_files_without_codex(self):
        response = await self.client.get('/templates', headers={'X-API-Key': 'test-token'})
        self.assertEqual(response.status_code, 200)
        catalog = response.json()['templates']
        self.assertEqual([item['id'] for item in catalog], ['mau_01', 'mau_02', 'mau_03'])
        self.assertEqual([item['navigation'] for item in catalog], ['pan_zoom', 'rotate_3d', 'rotate_3d'])
        self.assertTrue(all(item['description'] for item in catalog))
        response = await self.client.get('/templates/mau_01',
                                         headers={'X-API-Key': 'test-token'})
        self.assertEqual(response.status_code, 200)
        template = response.json()
        self.assertEqual(set(template), {'template', 'html', 'css', 'js'})
        self.assertEqual(template['template'], 'mau_01')
        for field, filename in (('html', 'index.html'),
                                ('css', 'style.css'), ('js', 'app.js')):
            self.assertEqual(template[field],
                             (BASE / 'templates' / 'mau_01' / filename)
                             .read_text(encoding='utf-8'))
        self.execute.assert_not_called()

    async def test_template_loader_uses_configured_directory(self):
        config = {
            'defaultTemplate': 'mau_01',
            'templates': {
                'mau_01': {
                    'name': 'Bản đồ mẫu 01',
                    'path': 'mau_01',
                },
            },
        }
        assets = {'html': '<main id="map"></main>',
                  'css': '#map { height: 100%; }',
                  'js': 'const map = true;'}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'mau_01'
            folder.mkdir()
            (root / 'config.json').write_text(json.dumps(config), encoding='utf-8')
            for field, filename in (('html', 'index.html'),
                                    ('css', 'style.css'), ('js', 'app.js')):
                (folder / filename).write_text(assets[field], encoding='utf-8')

            with patch.object(template_service, 'TEMPLATE_DIR', root):
                self.assertEqual(server.load_template(), {
                    'template': 'mau_01', **assets,
                })
                response = await self.client.get(
                    '/templates/mau_01', headers={'X-API-Key': 'test-token'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'template': 'mau_01', **assets})
        self.execute.assert_not_called()

    async def test_templates_require_authentication(self):
        for headers in ({}, {'X-API-Key': 'incorrect-token'}):
            for path in ('/templates', '/templates/mau_01'):
                response = await self.client.get(path, headers=headers)
                self.assertEqual(response.status_code, 401)
        response = await self.client.get('/templates/khong_co',
                                         headers={'X-API-Key': 'test-token'})
        self.assertEqual(response.status_code, 404)
        self.execute.assert_not_called()

    async def test_large_prompt_is_sent_in_full_through_stdin(self):
        prompt = 'Dữ liệu tiếng Việt\n' * 10000
        self.assertGreater(len(prompt.encode('utf-8')), 131072)
        response = await self.post({'prompt': prompt, 'model': 'client-selected-model'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(prompt, self.execute.call_args.args)
        self.process.communicate.assert_awaited_once_with(input=prompt.encode('utf-8'))

    async def test_missing_or_incorrect_token_does_not_start_codex(self):
        for headers in ({}, {'X-API-Key': 'incorrect-token'}):
            with self.subTest(headers=headers):
                response = await self.client.post('/analyze', json={
                    'prompt': 'Hello', 'model': 'client-selected-model'},
                                            headers=headers)
                self.assertEqual(response.status_code, 401)
        self.execute.assert_not_called()

    async def test_invalid_requests_do_not_start_codex(self):
        for payload in ({}, {'prompt': 'Hello'},
                        {'model': 'client-selected-model'},
                        {'prompt': '', 'model': 'client-selected-model'},
                        {'prompt': None, 'model': 'client-selected-model'},
                        {'prompt': 123, 'model': 'client-selected-model'},
                        {'prompt': 'Hello', 'model': ''},
                        {'prompt': 'Hello', 'model': None},
                        {'prompt': 'Hello', 'model': 123},
                        {'prompt': 'Hello', 'model': 'x" & whoami'},
                        {'prompt': 'Hello', 'model': 'client-selected-model',
                         'unexpected': {}}):
            with self.subTest(payload=payload):
                self.assertEqual((await self.post(payload)).status_code, 422)
        self.execute.assert_not_called()

    async def test_codex_failure_returns_generic_error_and_cleans_directory(self):
        self.process.returncode = 1
        self.process.communicate.return_value = (b'', b'private diagnostic output')
        response = await self.post({'prompt': 'Hello', 'model': 'client-selected-model'})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {'detail': 'Codex execution failed'})
        self.assertFalse(self.workdirs[0].exists())

    async def test_missing_codex_returns_service_error(self):
        self.executable.side_effect = server.HTTPException(
            503, 'Codex CLI not found; set CODEX_CLI_PATH or PATH')
        response = await self.post({'prompt': 'Hello', 'model': 'client-selected-model'})
        self.assertEqual(response.status_code, 503)
        self.execute.assert_not_called()
        self.assertEqual(response.json()['detail'],
                         'Codex CLI not found; set CODEX_CLI_PATH or PATH')

    async def test_codex_spawn_failure_returns_service_error(self):
        self.execute.side_effect = FileNotFoundError('codex.cmd')
        response = await self.post({'prompt': 'Hello', 'model': 'client-selected-model'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['detail'],
                         'Could not start Codex CLI; check CODEX_CLI_PATH or PATH')
        self.execute.assert_awaited_once()


class CodexExecutableTests(unittest.TestCase):
    def test_windows_uses_npm_command(self):
        with patch.object(server.os, 'name', 'nt'), \
                patch.object(server.shutil, 'which',
                             side_effect=lambda name: {
                                 'codex.cmd': r'C:\\npm\\codex.cmd',
                             }.get(name)) as which, \
                patch.dict(server.os.environ, {'CODEX_CLI_PATH': ''}):
            self.assertEqual(server.resolve_codex_executable(),
                             r'C:\\npm\\codex.cmd')
        which.assert_called_once_with('codex.cmd')

    def test_windows_does_not_fall_back_to_exe(self):
        with patch.object(server.os, 'name', 'nt'), \
                patch.object(server.shutil, 'which',
                             side_effect=lambda name: {
                                 'codex.exe': r'C:\\extension\\codex.exe',
                             }.get(name)) as which, \
                patch.dict(server.os.environ, {'CODEX_CLI_PATH': ''}):
            with self.assertRaises(server.HTTPException) as error:
                server.resolve_codex_executable()
        self.assertEqual(error.exception.status_code, 503)
        which.assert_called_once_with('codex.cmd')

    def test_configured_path_takes_priority(self):
        with patch.dict(server.os.environ,
                        {'CODEX_CLI_PATH': r'C:\\custom\\codex.cmd'}), \
                patch.object(server.shutil, 'which') as which:
            self.assertEqual(server.resolve_codex_executable(),
                             r'C:\\custom\\codex.cmd')
        which.assert_not_called()


if __name__ == '__main__':
    unittest.main()
