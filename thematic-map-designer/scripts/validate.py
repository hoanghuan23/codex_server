#!/usr/bin/env python3
"""Kiểm tra ba file web của skill thematic-map-designer.

Chạy: python3 scripts/validate.py --result output_directory

Kiểm tra file UTF-8 không rỗng, liên kết HTML/CSS/JS và cú pháp JS nếu có Node.
JSON phản hồi được caller kiểm tra bằng web_output.parse_web_files trước khi lưu.
Mã thoát: 0 = hợp lệ, 1 = đầu ra lỗi, 2 = sai tham số.
"""
import argparse
import sys

from web_output import validate_web


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.notes = []

    def err(self, path, message):
        self.errors.append(f'{path}: {message}')

    def warn(self, path, message):
        self.warnings.append(f'{path}: {message}')

    def note(self, message):
        self.notes.append(message)

    def finish(self):
        for message in self.notes:
            print('GHI CHÚ   ' + message)
        for message in self.warnings:
            print('CẢNH BÁO  ' + message)
        for message in self.errors:
            print('LỖI       ' + message)
        if self.errors:
            print(f'KẾT QUẢ: CÓ {len(self.errors)} LỖI, {len(self.warnings)} cảnh báo')
            return 1
        print(f'KẾT QUẢ: HỢP LỆ ({len(self.warnings)} cảnh báo)')
        return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--result', required=True,
                        help='thư mục chứa index.html, style.css, app.js')
    args = parser.parse_args()
    report = Report()
    validate_web(report, args.result)
    sys.exit(report.finish())


if __name__ == '__main__':
    main()
