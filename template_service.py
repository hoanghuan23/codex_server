import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config():
    return read_json(TEMPLATE_DIR / "config.json")


def load_template(template_id=None, theme=None):
    config = load_config()

    template_id = template_id or config["defaultTemplate"]
    theme = theme or config["defaultTheme"]

    templates = config["templates"]

    if template_id not in templates:
        raise ValueError("Template không tồn tại")

    info = templates[template_id]

    if theme not in info["themes"]:
        raise ValueError("Theme không hỗ trợ")

    folder = (TEMPLATE_DIR / info["path"]).resolve()

    if not folder.is_relative_to(TEMPLATE_DIR.resolve()):
        raise ValueError("Đường dẫn template không hợp lệ")

    return {
        "template": template_id,
        "theme": theme,
        "typography": read_json(folder / "typography.json"),
        "styles": read_json(folder / f"{theme}.json")
    }
