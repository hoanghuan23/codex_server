# uvicorn server:app --host 127.0.0.1 --port 8000
# cloudflared tunnel --url http://127.0.0.1:8000

import asyncio
import os
import tempfile
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

load_dotenv()
app = FastAPI()

API_TOKEN = os.environ["CODEX_API_TOKEN"]

class Request(BaseModel):
    prompt: str

@app.post("/analyze")
async def analyze(
    data: Request,
    x_api_key: str | None = Header(default=None)
):
    if x_api_key != API_TOKEN:
        raise HTTPException(401, "Unauthorized")

    if len(data.prompt) > 20000:
        raise HTTPException(400, "Prompt too long")

    with tempfile.TemporaryDirectory() as workdir:
        process = await asyncio.create_subprocess_exec(
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            data.prompt,
            cwd=workdir,
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

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise HTTPException(
                500,
                "Codex execution failed"
            )

        return {
            "success": True,
            "result": stdout.decode(errors="replace")
        }