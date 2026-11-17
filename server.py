# uvicorn server:app --host 127.0.0.1 --port 8000
# cloudflared tunnel --url http://127.0.0.1:8000

import asyncio
import base64
import os
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from template_service import load_config, load_template

load_dotenv()
app = FastAPI()

API_TOKEN = os.environ["CODEX_API_TOKEN"]
IMAGE_GENERATION_TIMEOUT = 600
MAX_IMAGE_BYTES = 20 * 1024 * 1024


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
    template: str | None = None


class GenerateRequest(BaseModel):
    """Content generation accepts the client's complete prompt and model."""
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1)
    model: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")


@app.post("/generate", tags=["generation"])
async def generate(
    data: GenerateRequest,
    x_api_key: str | None = Header(default=None)
):
    # The client supplies all content instructions and context.
    return await analyze(Request(prompt=data.prompt, model=data.model), x_api_key)


@app.post("/generate-image", tags=["generation"])
async def generate_image(
    data: GenerateRequest,
    x_api_key: str | None = Header(default=None)
):
    """Generate one PNG through the logged-in Codex CLI and return its base64."""
    if x_api_key != API_TOKEN:
        raise HTTPException(401, "Unauthorized")
    if not data.prompt.strip():
        raise HTTPException(422, "Image prompt must not be blank")

    with tempfile.TemporaryDirectory() as workdir:
        output = Path(workdir) / "output.png"
        prompt = (
             "$imagegen\n"
            "Generate exactly one image using the image generation tool.\n"
            "Do not use SVG, HTML, or drawing code.\n"
            "Save the generated PNG as output.png in the current directory.\n"
            "If generation fails, do not create output.png.\n\n"
            f"Prompt: {data.prompt}\n"
        )
        try:
            process = await asyncio.create_subprocess_exec(
                resolve_codex_executable(),
                "--ask-for-approval", "never",
                "--enable", "image_generation",
                "exec", "--model", data.model,
                "--skip-git-repo-check",
                "--sandbox", "workspace-write", "-",
                cwd=workdir,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except OSError as exc:
            raise HTTPException(
                503, "Could not start Codex CLI; check CODEX_CLI_PATH or PATH"
            ) from exc

        try:
            await asyncio.wait_for(
                process.communicate(input=prompt.encode("utf-8")),
                timeout=IMAGE_GENERATION_TIMEOUT
            )
        except (asyncio.TimeoutError, asyncio.CancelledError) as exc:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.communicate()
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise HTTPException(504, "Codex image generation timed out") from exc

        if process.returncode != 0:
            raise HTTPException(500, "Codex image generation failed")

        # Only read the fixed artifact in this request's directory, never a path
        # supplied by the client or extracted from the model's response text.
        try:
            if output.is_symlink() or not output.is_file():
                raise HTTPException(502, "Codex did not produce a PNG image")
            if output.stat().st_size > MAX_IMAGE_BYTES:
                raise HTTPException(502, "Generated image exceeds the 20 MiB limit")
            image_bytes = output.read_bytes()
        except OSError as exc:
            raise HTTPException(502, "Could not read the generated image") from exc
        if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(502, "Codex did not produce a PNG image")

        return {
            "success": True,
            "output_format": "png",
            "data": [{"b64_json": base64.b64encode(image_bytes).decode("ascii")}]
        }


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
        {"id": template_id, "name": info["name"], **({"navigation": info["navigation"], "description": info.get("description", "")} if info.get("navigation") else {})}
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
