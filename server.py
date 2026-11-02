# uvicorn server:app --host 127.0.0.1 --port 8000
# cloudflared tunnel --url http://127.0.0.1:8000

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Literal
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, model_validator

load_dotenv()
app = FastAPI()

API_TOKEN = os.environ["CODEX_API_TOKEN"]
CODEX_MODEL = os.getenv("CODEX_MODEL", "gpt-5.6-luna")
SKILLS = {
    "thematic-map-designer": Path(os.getenv(
        "SKILL_DIR", str(Path(__file__).resolve().parent / "thematic-map-designer"))).resolve(),
}
CHART_TYPES = ("choropleth", "point", "map_line", "arc_flow")

class Request(BaseModel):
    # prompt được giữ cho các client cũ; lời gọi skill chỉ gửi tên + dữ liệu.
    prompt: str | None = None
    skill: str | None = None
    input: dict[str, Any] | None = None
    mode: Literal["analysis", "text_analysis", "composition"] = "analysis"
    output_format: Literal["web"] = "web"

    @model_validator(mode="after")
    def validate_call(self):
        if self.prompt is not None:
            if self.skill is not None or self.input is not None:
                raise ValueError("Chọn prompt hoặc skill + input, không gửi đồng thời.")
        elif not self.skill or self.input is None:
            raise ValueError("Lời gọi skill cần skill và input.")
        if self.input is not None and "supportedCharts" in self.input:
            charts = self.input["supportedCharts"]
            if not isinstance(charts, list) or any(
                not isinstance(chart, str) or chart not in CHART_TYPES for chart in charts
            ):
                raise ValueError("supportedCharts phải là danh sách gồm choropleth, point, map_line hoặc arc_flow.")
        return self


def prepare_skill_call(data: Request, workdir: Path):
    skill_dir = SKILLS.get(data.skill)
    if skill_dir is None:
        raise HTTPException(404, "Skill chưa được đăng ký trên server")
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        raise HTTPException(503, "Không tìm thấy SKILL.md trên server")
    input_path = workdir / "input.json"
    input_path.write_text(json.dumps(data.input, ensure_ascii=False), encoding="utf-8")
    output_path = workdir / "output"
    output_path.mkdir()
    # Chỉ định skill và tham số; toàn bộ quy tắc thực thi nằm trong skill.
    return (
        f'Dùng skill ${data.skill} tại {json.dumps(str(skill_file), ensure_ascii=False)}.\n'
        f'mode={data.mode}\n'
        f'output_format={data.output_format}\n'
        f'input={input_path}\n'
        f'output={output_path}'
    )

@app.post("/analyze")
async def analyze(
    data: Request,
    x_api_key: str | None = Header(default=None)
):
    if x_api_key != API_TOKEN:
        raise HTTPException(401, "Unauthorized")

    with tempfile.TemporaryDirectory() as workdir:
        prompt = data.prompt
        allow_online = True
        if data.skill is not None:
            options = data.input.get("webOptions", {})
            if not isinstance(options, dict):
                raise HTTPException(400, "webOptions phải là object")
            allow_online = options.get("allowOnlineLookup", True) is not False
            prompt = prepare_skill_call(data, Path(workdir))
        command = ["codex"]
        if allow_online:
            command.append("--search")
        # Prompt chứa toàn bộ dữ liệu có thể vượt giới hạn đối số của hệ điều hành.
        prompt_input = prompt.encode("utf-8") if data.prompt is not None else None
        process = await asyncio.create_subprocess_exec(
            *command,
            "exec",
            "--model",
            CODEX_MODEL,
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "-" if prompt_input is not None else prompt,
            cwd=workdir,
            stdin=asyncio.subprocess.PIPE if prompt_input is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # try:
        #     stdout, stderr = await asyncio.wait_for(
        #         process.communicate(),
        #     )
        # except asyncio.TimeoutError:
        #     process.kill()
        #     await process.communicate()
        #     raise HTTPException(504, "Codex timeout")

        stdout, stderr = await process.communicate(input=prompt_input)

        if process.returncode != 0:
            raise HTTPException(
                500,
                "Codex execution failed"
            )

        return {
            "success": True,
            "result": stdout.decode(errors="replace")
        }
