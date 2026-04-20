from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_MD = ROOT / "AGRS_BACKEND_CHAPTER_WISE_NOTES.md"
OUTPUT_PDF = ROOT / "AGRS_BACKEND_CHAPTER_WISE_NOTES.pdf"


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_text(text: str, max_chars: int) -> list[str]:
    if not text:
        return [""]
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _build_page_ops(lines: list[str], page_width: int = 612, page_height: int = 792) -> list[str]:
    left_margin = 54
    top_margin = 54
    bottom_margin = 54
    y = page_height - top_margin
    ops: list[str] = []

    def emit(text: str, font: str = "F1", size: int = 11, x: int = left_margin) -> None:
        nonlocal y
        if y < bottom_margin:
            raise RuntimeError("page overflow")
        ops.append(f"BT /{font} {size} Tf {x} {int(y)} Td ({_escape_pdf_text(text)}) Tj ET")
        y -= size + 4

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            y -= 8
            continue

        if line.startswith("# "):
            y -= 6
            for part in _wrap_text(line[2:].strip(), max_chars=72):
                emit(part, font="F2", size=18)
            y -= 4
            continue

        if line.startswith("## "):
            y -= 4
            for part in _wrap_text(line[3:].strip(), max_chars=74):
                emit(part, font="F2", size=14)
            y -= 2
            continue

        if line.startswith("### "):
            for part in _wrap_text(line[4:].strip(), max_chars=76):
                emit(part, font="F2", size=12)
            continue

        if line.startswith("- "):
            bullet_text = line[2:].strip()
            wrapped = _wrap_text(bullet_text, max_chars=78)
            for idx, part in enumerate(wrapped):
                prefix = "- " if idx == 0 else "  "
                emit(prefix + part, size=11)
            continue

        if re.match(r"^\d+\.\s+", line):
            wrapped = _wrap_text(line, max_chars=78)
            for idx, part in enumerate(wrapped):
                emit(part if idx == 0 else "   " + part, size=11)
            continue

        if line.startswith("```"):
            continue

        for part in _wrap_text(line, max_chars=80):
            emit(part, size=11)

    return ops


def _make_pdf_object(obj_num: int, body: str) -> bytes:
    return f"{obj_num} 0 obj\n{body}\nendobj\n".encode("ascii")


def _stream_object(obj_num: int, stream: str) -> bytes:
    stream_bytes = stream.encode("ascii")
    body = f"<< /Length {len(stream_bytes)} >>\nstream\n{stream}\nendstream"
    return _make_pdf_object(obj_num, body)


def build_pdf(source_text: str) -> bytes:
    text = _ascii(source_text)
    raw_lines = text.splitlines()

    page_width = 612
    page_height = 792
    usable_height = page_height - 54 - 54
    approx_lines_per_page = max(1, math.floor(usable_height / 15))

    pages: list[list[str]] = []
    current: list[str] = []
    line_count = 0
    for line in raw_lines:
        estimated = max(1, math.ceil(len(line) / 80)) if line else 1
        if line_count + estimated > approx_lines_per_page and current:
            pages.append(current)
            current = []
            line_count = 0
        current.append(line)
        line_count += estimated
    if current:
        pages.append(current)

    page_streams = []
    for page_lines in pages:
        ops = _build_page_ops(page_lines, page_width=page_width, page_height=page_height)
        page_streams.append("\n".join(ops))

    objects: list[bytes] = []
    objects.append(_make_pdf_object(1, "<< /Type /Catalog /Pages 2 0 R >>"))
    objects.append(_make_pdf_object(2, "<< /Type /Pages /Kids [] /Count 0 >>"))
    objects.append(_make_pdf_object(3, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))
    objects.append(_make_pdf_object(4, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"))

    page_kids_refs = []
    next_obj = 5
    for stream in page_streams:
        content_num = next_obj
        page_num = next_obj + 1
        next_obj += 2
        objects.append(_stream_object(content_num, stream))
        page_body = (
            "<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {page_width} {page_height}] "
            "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_num} 0 R >>"
        )
        objects.append(_make_pdf_object(page_num, page_body))
        page_kids_refs.append(f"{page_num} 0 R")

    objects[1] = _make_pdf_object(2, f"<< /Type /Pages /Kids [{' '.join(page_kids_refs)}] /Count {len(page_kids_refs)} >>")

    body = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(body))
        body += obj

    xref_start = len(body)
    xref_lines = ["xref", f"0 {len(objects)+1}", "0000000000 65535 f "]
    for offset in offsets[1:]:
        xref_lines.append(f"{offset:010d} 00000 n ")
    xref = "\n".join(xref_lines) + "\n"
    trailer = (
        "trailer\n"
        f"<< /Size {len(objects)+1} /Root 1 0 R >>\n"
        "startxref\n"
        f"{xref_start}\n"
        "%%EOF\n"
    )
    return body + xref.encode("ascii") + trailer.encode("ascii")


def main() -> None:
    source = SOURCE_MD.read_text(encoding="utf-8")
    OUTPUT_PDF.write_bytes(build_pdf(source))
    print(f"Created: {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
