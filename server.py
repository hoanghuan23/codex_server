# uvicorn server:app --host 127.0.0.1 --port 8000
# cloudflared tunnel --url http://127.0.0.1:8000

import asyncio
import os
import shutil
import tempfile

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from template_service import load_config, load_template

load_dotenv()
app = FastAPI()

API_TOKEN = os.environ["CODEX_API_TOKEN"]


def resolve_codex_executable():
    configured = os.environ.get("CODEX_CLI_PATH")
    if configured:
        return configured

    command = "codex.cmd" if os.name == "nt" else "codex"
    executable = shutil.which(command)
    if executable:
        return executable
    raise HTTPException(503, "Codex CLI not found; set CODEX_CLI_PATH or PATH")


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1)
    model: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
    template: str = "mau_01"

@app.post("/analyze")
async def analyze(
    data: Request,
    x_api_key: str | None = Header(default=None)
):
    if x_api_key != API_TOKEN:
        raise HTTPException(401, "Unauthorized")

    with tempfile.TemporaryDirectory() as workdir:
        # Prompt chứa toàn bộ dữ liệu có thể vượt giới hạn đối số của hệ điều hành.
        prompt_input = data.prompt.encode("utf-8")
        try:
            process = await asyncio.create_subprocess_exec(
                resolve_codex_executable(),
                "--search",
                "exec",
                "--model",
                data.model,
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "-",
                cwd=workdir,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except OSError as exc:
            raise HTTPException(
                503, "Could not start Codex CLI; check CODEX_CLI_PATH or PATH"
            ) from exc

        stdout, _stderr = await process.communicate(input=prompt_input)

        if process.returncode != 0:
            raise HTTPException(
                500,
                "Codex execution failed"
            )

        return {
            "success": True,
            "result": stdout.decode(errors="replace")
        }

@app.get("/templates")
async def list_templates(
    x_api_key: str | None = Header(default=None)
):
    if x_api_key != API_TOKEN:
        raise HTTPException(401, "Unauthorized")

    config = load_config()
    return {"templates": [
        {"id": template_id, "name": info["name"]}
        for template_id, info in config["templates"].items()
    ]}


@app.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    x_api_key: str | None = Header(default=None)
):
    if x_api_key != API_TOKEN:
        raise HTTPException(401, "Unauthorized")

    try:
        return load_template(template_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
