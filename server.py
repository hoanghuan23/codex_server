# uvicorn server:app --host 127.0.0.1 --port 8000
# cloudflared tunnel --url http://127.0.0.1:8000

import asyncio
import os
import tempfile

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from template_service import load_config, load_template

load_dotenv()
app = FastAPI()

API_TOKEN = os.environ["CODEX_API_TOKEN"]


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1)
    model: str = Field(min_length=1)
    template: str = "vnexpress"
    theme: str = "light"

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
    templates = []

    for template_id, info in config["templates"].items():
        for theme in info["themes"]:
            # Serve the authored files alongside catalog metadata; AI only
            # recommends data presentation and never supplies these styles.
            try:
                template = load_template(template_id, theme)
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
            styles = template["styles"]
            typography = template["typography"]

            templates.append({
                "id": template_id,
                "theme": theme,
                "name": f"{info['name']} - {theme.capitalize()}",
                "styles": styles,
                "typography": template["typography"],
                "description": (
                    f"{typography['fontFamily'].split(',')[0]}, "
                    f"nền {styles['colors']['background']}, "
                    f"chữ {styles['colors']['text']}"
                )
            })

    return {"templates": templates}
