"""Gọi /generate-image, lưu PNG và JSON để xem kết quả thực tế.

Chạy trong codex_server:
    python3 test_generate_image.py --model your-codex-model --open

Token lấy từ CODEX_API_TOKEN trong .env hoặc môi trường hiện tại.
Model lấy từ --model hoặc CODEX_MODEL; đây là model agent Codex.
"""

import argparse
import base64
import binascii
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import webbrowser

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
DEFAULT_PROMPT = (
    "Create one detailed editorial vector-style illustration of a towering cumulonimbus storm cloud, light 2.5D shading, multiple cloud layers, soft highlights, clearly recognizable silhouette, isolated object, transparent background, no text, no labels, no arrows."
)


def main(argv=None):
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=os.getenv(
        "CODEX_IMAGE_API_URL", "http://127.0.0.1:8000/generate-image"),
        help="URL đầy đủ của endpoint /generate-image.")
    parser.add_argument("--model", default=os.getenv("CODEX_MODEL"),
                        help="Model agent Codex, giống model gửi tới /generate.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT,
                        help="Mô tả ảnh cần tạo.")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "test_output" / "generated_image.png",
                        help="Đường dẫn PNG; JSON được lưu cùng tên với đuôi .response.json.")
    parser.add_argument("--open", action="store_true",
                        help="Mở ảnh bằng trình duyệt sau khi lưu.")
    args = parser.parse_args(argv)

    token = os.getenv("CODEX_API_TOKEN", "").strip()
    if not token:
        parser.error("Thiếu CODEX_API_TOKEN. Hãy đặt token trong .env hoặc biến môi trường.")
    if not args.model or not args.model.strip():
        parser.error("Thiếu model. Dùng --model MODEL hoặc đặt CODEX_MODEL trong .env.")
    if not args.prompt.strip():
        parser.error("Prompt không được để trống.")
    if args.output.suffix.lower() != ".png":
        parser.error("--output phải có đuôi .png.")

    payload = {"prompt": args.prompt, "model": args.model}
    request = Request(args.url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json", "X-API-Key": token},
                      method="POST")
    print(f"POST {args.url}\nModel: {args.model}\nPrompt: {args.prompt}", flush=True)
    print("Đang đợi Codex tạo ảnh (server giới hạn 600 giây)...", flush=True)
    try:
        with urlopen(request, timeout=660) as response:
            result = json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise ValueError(f"API trả HTTP {error.code}: {detail}") from error

    if not isinstance(result, dict) or result.get("success") is not True:
        raise ValueError("API không trả success=true.")
    images = result.get("data")
    if (result.get("output_format") != "png" or not isinstance(images, list)
            or len(images) != 1 or not isinstance(images[0], dict)
            or not isinstance(images[0].get("b64_json"), str)):
        raise ValueError("Phản hồi không đúng schema PNG data[0].b64_json.")
    encoded = images[0]["b64_json"]
    try:
        png = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("data[0].b64_json không phải base64 hợp lệ.") from error
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Ảnh giải mã không có chữ ký PNG.")

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(png)
    response_path = output.with_suffix(".response.json")
    response_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    preview = {**result, "data": [{**images[0], "b64_json": encoded[:60] + "..."}]}
    print("\nPhản hồi (base64 được rút gọn khi in):")
    print(json.dumps(preview, ensure_ascii=False, indent=2))
    print(f"\nẢnh PNG: {output} ({len(png):,} byte)")
    print(f"JSON đầy đủ: {response_path}")
    if args.open and not webbrowser.open(output.as_uri()):
        print("Không mở được trình duyệt tự động; hãy mở file PNG ở đường dẫn trên.",
              file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except (URLError, TimeoutError, ValueError, OSError) as error:
        raise SystemExit(f"Lỗi: {error}")
