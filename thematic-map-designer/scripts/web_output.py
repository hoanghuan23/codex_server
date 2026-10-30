"""Tách phản hồi gồm ba khối file và kiểm tra đầu ra web, không thực thi mã ứng dụng."""
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

WEB_FILES = ('index.html', 'app.js', 'style.css')
FILE_LANGUAGES = {'index.html': 'html', 'app.js': 'javascript', 'style.css': 'css'}
FILE_BLOCK = re.compile(
    r'```(?P<language>html|javascript|css) filename=(?P<name>[^\n]+)\n'
    r'(?P<content>.*?)^```[ \t]*(?:\n|$)', re.M | re.S)


def parse_file_blocks(raw):
    """Chấp nhận đúng ba tên file đã biết; từ chối JSON, file thiếu/trùng và đường dẫn lạ."""
    if not isinstance(raw, str):
        raise ValueError('Phản hồi phải là chuỗi chứa ba khối file HTML/JS/CSS.')
    raw = raw.replace('\r\n', '\n').strip()
    files, end = {}, 0
    for match in FILE_BLOCK.finditer(raw):
        if raw[end:match.start()].strip():
            raise ValueError('Phản hồi chứa nội dung ngoài ba khối file.')
        name = match['name']
        if name not in FILE_LANGUAGES or match['language'] != FILE_LANGUAGES[name]:
            raise ValueError(f'Tên file hoặc ngôn ngữ không hợp lệ: {name}')
        if name in files:
            raise ValueError(f'File bị lặp trong phản hồi: {name}')
        if not match['content'].strip():
            raise ValueError(f'File rỗng: {name}')
        files[name] = match['content']
        end = match.end()
    if raw[end:].strip() or set(files) != set(WEB_FILES):
        raise ValueError('Cần đủ ba khối file index.html, app.js, style.css; không trả JSON/TXT.')
    return files


class WebHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.doctype = False
        self.tags = set()
        self.css = False
        self.js = False
        self.references = []
        self.errors = []
        self.in_script = False

    def handle_decl(self, decl):
        if decl.lower() == 'doctype html':
            self.doctype = True

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.add(tag)
        if tag == 'base':
            self.errors.append('Không dùng base URL; liên kết phải tương đối với index.html.')
        if tag == 'style':
            self.errors.append('Chuyển khối CSS trong HTML sang style.css.')
        if any(key.startswith('on') for key in attrs):
            self.errors.append('Chuyển event handler trong HTML sang app.js.')
        if tag == 'link' and 'stylesheet' in (attrs.get('rel') or '').lower().split():
            href = attrs.get('href') or ''
            self.css |= href in ('style.css', './style.css')
            self.references.append(href)
        if tag == 'script':
            self.in_script = True
            src = attrs.get('src') or ''
            self.references.append(src)
            if not src:
                self.errors.append('Chuyển JavaScript nhúng trong HTML sang app.js.')
            if src in ('app.js', './app.js'):
                self.js = True
                if 'defer' not in attrs or (attrs.get('type') or '').lower() == 'module':
                    self.errors.append('Nạp app.js bằng script thường có defer.')
        if tag in ('img', 'source') and attrs.get('src'):
            self.references.append(attrs['src'])

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False

    def handle_data(self, data):
        if self.in_script and data.strip():
            self.errors.append('Chuyển nội dung script sang app.js.')


def validate_web(rep, directory):
    directory = Path(directory)
    if not directory.is_dir():
        rep.err('output', 'đầu ra web phải là thư mục chứa index.html, app.js, style.css')
        return
    contents = {}
    for name in WEB_FILES:
        path = directory / name
        try:
            contents[name] = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError) as exc:
            rep.err(name, f'không đọc được file UTF-8: {exc}')
            continue
        if not contents[name].strip():
            rep.err(name, 'file rỗng')
    if rep.errors:
        return
    html = WebHTML()
    html.feed(contents['index.html'])
    html.close()
    if not html.doctype or not {'html', 'head', 'title', 'body'}.issubset(html.tags):
        rep.err('index.html', 'cần HTML hoàn chỉnh có DOCTYPE, html, head, title, body')
    if not html.css:
        rep.err('index.html', 'thiếu liên kết ./style.css')
    if not html.js:
        rep.err('index.html', 'thiếu script ./app.js')
    for error in dict.fromkeys(html.errors):
        rep.err('index.html', error)
    root = directory.resolve()
    for reference in html.references:
        try:
            url = urlsplit(reference)
        except ValueError:
            rep.err('index.html', f'URL tài nguyên không hợp lệ: {reference}')
            continue
        if url.scheme in ('http', 'https') or url.netloc:
            rep.warn('index.html', f'tài nguyên mạng chưa được kiểm tra: {reference}')
        elif url.scheme:
            rep.err('index.html', f'URL tài nguyên không được hỗ trợ: {reference}')
        elif url.path:
            path = (root / unquote(url.path)).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                rep.err('index.html', f'tài nguyên cục bộ bị thiếu hoặc ngoài output: {reference}')
    node = shutil.which('node') or shutil.which('nodejs')
    if node:
        try:
            checked = subprocess.run([node, '--check', str(root / 'app.js')],
                                     capture_output=True, text=True, timeout=30)
            if checked.returncode:
                rep.err('app.js', 'sai cú pháp JavaScript: ' + checked.stderr.strip())
        except (OSError, subprocess.TimeoutExpired) as exc:
            rep.err('app.js', f'không kiểm tra được cú pháp: {exc}')
    else:
        rep.warn('app.js', 'chưa kiểm cú pháp JavaScript vì không có Node.js')
    rep.note('Đã kiểm tra tĩnh; chưa kiểm giao diện, CSS, tương tác hoặc ghép geometry trong trình duyệt.')
