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
            'codex', '--search', 'exec', '--model', model,
            '--skip-git-repo-check', '--sandbox', 'read-only', '-'))
        self.assertEqual(self.execute.call_args.kwargs['stdin'],
                         server.asyncio.subprocess.PIPE)
        self.process.communicate.assert_awaited_once_with(input=prompt.encode('utf-8'))
        self.assertFalse(self.workdirs[0].exists())

    async def test_templates_include_authored_styles_and_typography_without_codex(self):
        response = await self.client.get('/templates', headers={'X-API-Key': 'test-token'})
        self.assertEqual(response.status_code, 200)
        templates = response.json()['templates']
        self.assertTrue(templates)
        for item in templates:
            authored = server.load_template(item['id'], item['theme'])
            self.assertEqual(item['styles'], authored['styles'])
            self.assertEqual(item['typography'], authored['typography'])
            self.assertIn('name', item)
            self.assertIn('description', item)
        self.execute.assert_not_called()

    async def test_templates_use_new_structure_without_manifest(self):
        config = {
            'defaultTemplate': 'vnexpress',
            'defaultTheme': 'light',
            'templates': {
                'vnexpress': {
                    'name': 'VnExpress',
                    'path': 'vnexpress',
                    'themes': ['light', 'dark'],
                },
            },
        }
        typography = {'fontFamily': 'Arial, Helvetica, sans-serif'}
        styles = {
            'light': {'colors': {'background': '#FFFFFF', 'text': '#222222'}},
            'dark': {'colors': {'background': '#1C1C26', 'text': '#E5E7EB'}},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'vnexpress'
            folder.mkdir()
            files = {'config.json': config, 'vnexpress/typography.json': typography}
            files.update({f'vnexpress/{theme}.json': value
                          for theme, value in styles.items()})
            for filename, value in files.items():
                (root / filename).write_text(json.dumps(value), encoding='utf-8')

            with patch.object(template_service, 'TEMPLATE_DIR', root):
                self.assertEqual(server.load_template(), {
                    'template': 'vnexpress', 'theme': 'light',
                    'typography': typography, 'styles': styles['light'],
                })
                response = await self.client.get(
                    '/templates', headers={'X-API-Key': 'test-token'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'templates': [
            {
                'id': 'vnexpress', 'theme': theme,
                'name': f'VnExpress - {theme.capitalize()}',
                'typography': typography, 'styles': value,
                'description': (f"Arial, nền {value['colors']['background']}, "
                                f"chữ {value['colors']['text']}"),
            }
            for theme, value in styles.items()
        ]})
        self.execute.assert_not_called()

    async def test_templates_require_authentication(self):
        for headers in ({}, {'X-API-Key': 'incorrect-token'}):
            response = await self.client.get('/templates', headers=headers)
            self.assertEqual(response.status_code, 401)
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


if __name__ == '__main__':
    unittest.main()
