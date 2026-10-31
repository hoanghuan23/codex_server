"""Kiểm tra hợp đồng skill của server với Codex được mock, không gọi AI thật."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException
from pydantic import ValidationError

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('skill_api_test_server', BASE / 'server.py')
server = importlib.util.module_from_spec(spec)
with patch.dict(os.environ, {'CODEX_API_TOKEN': 'test-token'}):
    spec.loader.exec_module(server)


class SkillAPITests(unittest.IsolatedAsyncioTestCase):
    def request(self, **changes):
        return server.Request(**{
            'skill': 'thematic-map-designer',
            'input': {'records': [{'Khu vực': 'Huế', 'Giá trị': 0}]},
            **changes,
        })

    async def invoke(self, data):
        captured = {}

        async def fake_exec(*command, **kwargs):
            captured['command'] = command
            captured['cwd'] = Path(kwargs['cwd'])
            invocation = command[-1]
            params = dict(line.split('=', 1) for line in invocation.splitlines()
                          if line.startswith(('input=', 'output=', 'mode=', 'output_format=')))
            if params:
                captured['params'] = params
                captured['input_path'] = Path(params['input'])
                captured['input'] = json.loads(captured['input_path'].read_text())
                captured['output_is_directory'] = Path(params['output']).is_dir()
            process = Mock(returncode=0)
            process.communicate = AsyncMock(return_value=(b'file blocks from skill', b''))
            captured['process'] = process
            captured['stdin_mode'] = kwargs.get('stdin')
            return process

        with patch.object(server, 'API_TOKEN', 'test-token'), \
                patch.object(server.asyncio, 'create_subprocess_exec', side_effect=fake_exec):
            captured['response'] = await server.analyze(data, x_api_key='test-token')
        return captured

    async def test_data_is_available_to_skill_in_server_owned_temporary_file(self):
        data = self.request(input={'records': [{'Tên': 'Một địa danh', 'Giá trị': 0,
                                               'Ghi chú': 'x' * 25000}]})
        captured = await self.invoke(data)
        self.assertEqual(captured['input'], data.input)
        self.assertEqual(captured['params']['mode'], 'analysis')
        self.assertEqual(captured['params']['output_format'], 'web')
        self.assertEqual(captured['input_path'].parent, captured['cwd'])
        self.assertTrue(captured['output_is_directory'])
        self.assertFalse(captured['cwd'].exists())
        self.assertLess(len(captured['command'][-1]), 2000)
        self.assertEqual(captured['response']['result'], 'file blocks from skill')
        self.assertIn(str(server.SKILLS['thematic-map-designer'] / 'SKILL.md'),
                      captured['command'][-1])
        self.assertIn('--search', captured['command'])
        sandbox = captured['command'].index('--sandbox')
        self.assertEqual(captured['command'][sandbox + 1], 'read-only')

    async def test_offline_option_is_passed_to_skill_without_enabling_search(self):
        data = self.request(input={'webOptions': {'allowOnlineLookup': False}, 'records': []})
        captured = await self.invoke(data)
        self.assertEqual(captured['input'], data.input)
        self.assertNotIn('--search', captured['command'])

    async def test_text_and_composition_modes_use_web_output(self):
        for mode, payload in [
            ('text_analysis', {'text': 'Huế có 3 cơ sở.'}),
            ('composition', {'layers': [{'id': 'area', 'records': []}]}),
        ]:
            with self.subTest(mode=mode):
                captured = await self.invoke(self.request(mode=mode, output_format='web',
                                                          input=payload))
                self.assertEqual(captured['params']['mode'], mode)
                self.assertEqual(captured['params']['output_format'], 'web')
                self.assertEqual(captured['input'], payload)
                self.assertTrue(captured['output_is_directory'])

    def test_configuration_output_and_standalone_layer_order_are_rejected(self):
        for changes in [{'output_format': 'json'}, {'mode': 'layer_order'}]:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.request(**changes)

    async def test_supported_chart_lists_reach_skill_without_defaulting_empty_list(self):
        for charts in [['point'], [], list(server.CHART_TYPES)]:
            with self.subTest(charts=charts):
                captured = await self.invoke(self.request(input={'supportedCharts': charts,
                                                                 'records': []}))
                self.assertEqual(captured['input']['supportedCharts'], charts)

    def test_supported_charts_rejects_slot_registry_and_invalid_names(self):
        for charts in [{'point': {'slots': {}}}, 'point', None, ['unknown'], [1], [{}]]:
            with self.subTest(charts=charts), self.assertRaises(ValidationError):
                self.request(input={'supportedCharts': charts})

    async def test_legacy_prompt_clients_continue_to_work(self):
        captured = await self.invoke(server.Request(prompt='Lời gọi cũ'))
        self.assertEqual(captured['command'][-1], '-')
        self.assertEqual(captured['stdin_mode'], server.asyncio.subprocess.PIPE)
        captured['process'].communicate.assert_awaited_once_with(input='Lời gọi cũ'.encode('utf-8'))
        self.assertNotIn('input_path', captured)

    async def test_large_excel_prompt_reaches_codex_without_truncation(self):
        # Vượt cả giới hạn 20.000 ký tự cũ và giới hạn kích thước một đối số CLI.
        prompt = 'DỮ LIỆU EXCEL:\n' + json.dumps([
            {'Điểm đi': f'Ga số {i}', 'Điểm đến': 'Ga đích', 'Lưu lượng': i}
            for i in range(2000)
        ], ensure_ascii=False)
        self.assertGreater(len(prompt), 20000)
        self.assertGreater(len(prompt.encode('utf-8')), 131072)
        captured = await self.invoke(server.Request(prompt=prompt))
        self.assertTrue(captured['response']['success'])
        self.assertEqual(captured['command'][-1], '-')
        self.assertNotIn(prompt, captured['command'])
        captured['process'].communicate.assert_awaited_once_with(input=prompt.encode('utf-8'))

    async def test_unknown_skill_is_rejected_before_running_codex(self):
        with patch.object(server, 'API_TOKEN', 'test-token'), \
                patch.object(server.asyncio, 'create_subprocess_exec') as execute:
            with self.assertRaises(HTTPException) as error:
                await server.analyze(self.request(skill='../../server.py'), x_api_key='test-token')
        self.assertEqual(error.exception.status_code, 404)
        execute.assert_not_called()

    async def test_missing_skill_installation_is_reported_before_running_codex(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(server, 'SKILLS', {'thematic-map-designer': Path(directory)}), \
                patch.object(server, 'API_TOKEN', 'test-token'), \
                patch.object(server.asyncio, 'create_subprocess_exec') as execute:
            with self.assertRaises(HTTPException) as error:
                await server.analyze(self.request(), x_api_key='test-token')
        self.assertEqual(error.exception.status_code, 503)
        execute.assert_not_called()

    async def test_authentication_still_precedes_skill_execution(self):
        with patch.object(server, 'API_TOKEN', 'test-token'), \
                patch.object(server.asyncio, 'create_subprocess_exec') as execute:
            with self.assertRaises(HTTPException) as error:
                await server.analyze(self.request(), x_api_key='incorrect-token')
        self.assertEqual(error.exception.status_code, 401)
        execute.assert_not_called()

    def test_ambiguous_or_incomplete_calls_are_rejected(self):
        for payload in [{}, {'skill': 'thematic-map-designer'}, {'input': {}},
                        {'prompt': 'Cũ', 'skill': 'thematic-map-designer', 'input': {}},
                        {'skill': 'thematic-map-designer', 'input': {}, 'mode': 'invalid'}]:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                server.Request(**payload)


if __name__ == '__main__':
    unittest.main()
