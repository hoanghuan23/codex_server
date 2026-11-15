# uvicorn server:app --host 127.0.0.1 --port 8000
# cloudflared tunnel --url http://127.0.0.1:8000

import asyncio
import base64
import binascii
import json
import os
import re
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


class GenerateImageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1)
    model: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
    session_id: str | None = Field(
        default=None, min_length=1, max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )


def image_mime_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    return None


def generated_images_dir(session_id: str) -> Path | None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", session_id):
        return None
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    root = (codex_home / "generated_images").resolve()
    directory = (root / session_id).resolve()
    return directory if directory.is_relative_to(root) else None


def generated_image_paths(session_id: str) -> set[Path]:
    directory = generated_images_dir(session_id)
    if directory is None or not directory.is_dir():
        return set()
    return {path.resolve() for path in directory.iterdir() if path.is_file()}


def newest_generated_image(session_id: str, existing: set[Path]) -> bytes | None:
    paths = generated_image_paths(session_id) - existing
    for path in sorted(paths, key=lambda candidate: candidate.stat().st_mtime_ns,
                       reverse=True):
        data = path.read_bytes()
        if image_mime_type(data):
            return data
    return None


def parse_image_events(output: bytes, workdir: str):
    session_id = None
    image_data = None
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "thread.started":
            session_id = event.get("thread_id")
        if event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") not in (
            "image_generation", "image_generation_call"
        ) or item.get("status") != "completed":
            continue
        candidate = None
        inline = item.get("result")
        if not inline and isinstance(item.get("image"), dict):
            inline = item["image"].get("result")
        if isinstance(inline, str) and inline:
            try:
                candidate = base64.b64decode(inline, validate=True)
            except (ValueError, binascii.Error):
                pass
        if image_mime_type(candidate or b"") is None and isinstance(item.get("saved_path"), str):
            path = Path(item["saved_path"])
            if not path.is_absolute():
                path = Path(workdir) / path
            path = path.resolve()
            # A CLI event must not make the server read an unrelated local file.
            allowed_roots = [Path(workdir).resolve()]
            codex_home = os.environ.get("CODEX_HOME")
            if codex_home:
                allowed_roots.append((Path(codex_home) / "generated_images").resolve())
            else:
                allowed_roots.append((Path.home() / ".codex" / "generated_images").resolve())
            if any(path.is_relative_to(root) for root in allowed_roots) and path.is_file():
                candidate = path.read_bytes()
        if image_mime_type(candidate or b"") is not None:
            image_data = candidate
    return image_data, session_id


@app.post("/generate-image", tags=["generation"])
async def generate_image(
    data: GenerateImageRequest,
    x_api_key: str | None = Header(default=None),
):
    if x_api_key != API_TOKEN:
        raise HTTPException(401, "Unauthorized")

    with tempfile.TemporaryDirectory() as workdir:
        existing_images = generated_image_paths(data.session_id) if data.session_id else set()
        if data.session_id:
            command = [
                resolve_codex_executable(), "exec", "resume",
                "--enable", "image_generation", "--json",
                "--model", data.model, "--skip-git-repo-check",
                data.session_id, "-",
            ]
        else:
            command = [
                resolve_codex_executable(), "exec",
                "--enable", "image_generation", "--json",
                "--model", data.model, "--skip-git-repo-check",
                "--sandbox", "workspace-write", "-",
            ]
        prompt = (
            "Use the image_generation tool to create the requested image. "
            "Return a real bitmap image (PNG, JPEG, WebP, or GIF), never SVG. "
            "Do not substitute text or code for the image.\n\n" + data.prompt
        )
        try:
            process = await asyncio.create_subprocess_exec(
                *command, cwd=workdir, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise HTTPException(
                503, "Could not start Codex CLI; check CODEX_CLI_PATH or PATH"
            ) from exc
        stdout, _stderr = await process.communicate(input=prompt.encode("utf-8"))
        if process.returncode != 0:
            raise HTTPException(502, "Codex image generation failed")
        image_data, session_id = parse_image_events(stdout, workdir)
        session_id = session_id or data.session_id
        if image_data is None and session_id:
            image_data = newest_generated_image(session_id, existing_images)
        mime_type = image_mime_type(image_data or b"")
        if mime_type is None:
            raise HTTPException(502, "Codex did not return a bitmap image")
        return {
            "success": True,
            "result": f"data:{mime_type};base64,{base64.b64encode(image_data).decode('ascii')}",
            "mime_type": mime_type,
            "session_id": session_id,
        }


@app.post("/generate", tags=["generation"])
async def generate(
    data: GenerateRequest,
    x_api_key: str | None = Header(default=None)
):
    # The client supplies all content instructions and context.
    return await analyze(Request(prompt=data.prompt, model=data.model), x_api_key)


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
