import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config():
    return read_json(TEMPLATE_DIR / "config.json")


def load_template(template_id=None):
    config = load_config()

    template_id = template_id or config["defaultTemplate"]

    templates = config["templates"]

    if template_id not in templates:
        raise ValueError("Template không tồn tại")

    info = templates[template_id]

    folder = (TEMPLATE_DIR / info["path"]).resolve()

    if not folder.is_relative_to(TEMPLATE_DIR.resolve()):
        raise ValueError("Đường dẫn template không hợp lệ")

    files = {name: folder / filename for name, filename in (
        ("html", "index.html"), ("css", "style.css"), ("js", "app.js")
    )}
    if any(not path.is_file() for path in files.values()):
        raise ValueError("Template thiếu file HTML, CSS hoặc JS")

    return {
        "template": template_id,
        **{name: path.read_text(encoding="utf-8") for name, path in files.items()}
    }
