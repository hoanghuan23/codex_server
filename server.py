# uvicorn server:app --host 127.0.0.1 --port 8000
# cloudflared tunnel --url http://127.0.0.1:8000

import asyncio
import os
import tempfile

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()
app = FastAPI()

API_TOKEN = os.environ["CODEX_API_TOKEN"]
CODEX_MODEL = os.getenv("CODEX_MODEL", "gpt-5.6-luna")


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1)


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
        process = await asyncio.create_subprocess_exec(
            "codex",
            "--search",
            "exec",
            "--model",
            CODEX_MODEL,
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "-",
            cwd=workdir,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

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
