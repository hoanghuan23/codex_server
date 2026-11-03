"""Kiểm tra API server với tiến trình Codex giả lập."""
import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from httpx import ASGITransport, AsyncClient


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

    async def test_prompt_runs_with_server_model_and_cleans_temporary_directory(self):
        prompt = 'Phân tích nội dung tiếng Việt'
        with patch.object(server, 'CODEX_MODEL', 'configured-model'):
            response = await self.post({'prompt': prompt})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'success': True, 'result': 'Xin chào'})
        command = self.execute.call_args.args
        self.assertEqual(command, (
            'codex', '--search', 'exec', '--model', 'configured-model',
            '--skip-git-repo-check', '--sandbox', 'read-only', '-'))
        self.assertEqual(self.execute.call_args.kwargs['stdin'],
                         server.asyncio.subprocess.PIPE)
        self.process.communicate.assert_awaited_once_with(input=prompt.encode('utf-8'))
        self.assertFalse(self.workdirs[0].exists())

    async def test_large_prompt_is_sent_in_full_through_stdin(self):
        prompt = 'Dữ liệu tiếng Việt\n' * 10000
        self.assertGreater(len(prompt.encode('utf-8')), 131072)
        response = await self.post({'prompt': prompt})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(prompt, self.execute.call_args.args)
        self.process.communicate.assert_awaited_once_with(input=prompt.encode('utf-8'))

    async def test_missing_or_incorrect_token_does_not_start_codex(self):
        for headers in ({}, {'X-API-Key': 'incorrect-token'}):
            with self.subTest(headers=headers):
                response = await self.client.post('/analyze', json={'prompt': 'Hello'},
                                            headers=headers)
                self.assertEqual(response.status_code, 401)
        self.execute.assert_not_called()

    async def test_invalid_requests_do_not_start_codex(self):
        for payload in ({}, {'prompt': ''}, {'prompt': None}, {'prompt': 123},
                        {'prompt': 'Hello', 'unexpected': {}}):
            with self.subTest(payload=payload):
                self.assertEqual((await self.post(payload)).status_code, 422)
        self.execute.assert_not_called()

    async def test_codex_failure_returns_generic_error_and_cleans_directory(self):
        self.process.returncode = 1
        self.process.communicate.return_value = (b'', b'private diagnostic output')
        response = await self.post({'prompt': 'Hello'})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {'detail': 'Codex execution failed'})
        self.assertFalse(self.workdirs[0].exists())


if __name__ == '__main__':
    unittest.main()
