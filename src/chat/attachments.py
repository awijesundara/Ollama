import asyncio
import base64
import csv
import io
import json
import mimetypes
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from docx import Document
from PIL import Image
from pypdf import PdfReader

_TEXT_EXTENSIONS = {
    ".c",
    ".cfg",
    ".conf",
    ".cpp",
    ".cs",
    ".css",
    ".csv",
    ".go",
    ".h",
    ".hpp",
    ".htm",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".log",
    ".md",
    ".php",
    ".properties",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
_IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}


class AttachmentError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ProcessedAttachments:
    text: str
    images: list[str]
    names: list[str]


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.parts.append(stripped)


async def process_attachments(
    elements: list[Any],
    *,
    max_files: int,
    max_file_bytes: int,
    max_extracted_chars: int,
) -> ProcessedAttachments:
    if len(elements) > max_files:
        raise AttachmentError(f"Upload at most {max_files} files at a time.")

    sections: list[str] = []
    images: list[str] = []
    names: list[str] = []
    remaining = max_extracted_chars
    for element in elements:
        name = _element_name(element)
        payload = await _read_element(element, max_file_bytes)
        extension = Path(name).suffix.casefold()
        mime = str(getattr(element, "mime", "") or "")
        if extension in _IMAGE_EXTENSIONS or mime.startswith("image/"):
            encoded = await asyncio.to_thread(_validate_and_encode_image, payload)
            images.append(encoded)
            names.append(name)
            continue

        extracted = await asyncio.to_thread(_extract_text, name, mime, payload)
        if not extracted.strip():
            raise AttachmentError(f"No readable text was found in {name}.")
        excerpt = extracted[:remaining]
        sections.append(f"--- Attachment: {name} ---\n{excerpt}")
        names.append(name)
        remaining -= len(excerpt)
        if remaining <= 0:
            break

    return ProcessedAttachments(
        text="\n\n".join(sections),
        images=images,
        names=names,
    )


def _element_name(element: Any) -> str:
    name = str(getattr(element, "name", "") or "").strip()
    return Path(name).name or "attachment"


async def _read_element(element: Any, max_file_bytes: int) -> bytes:
    content = getattr(element, "content", None)
    if isinstance(content, bytes):
        payload = content
    else:
        path_value = getattr(element, "path", None)
        if not path_value:
            raise AttachmentError(f"Cannot access {_element_name(element)}.")
        path = Path(str(path_value))
        try:
            size = path.stat().st_size
        except OSError as error:
            raise AttachmentError(
                f"Cannot access {_element_name(element)}."
            ) from error
        if size > max_file_bytes:
            raise AttachmentError(
                f"{_element_name(element)} exceeds the upload size limit."
            )
        payload = await asyncio.to_thread(path.read_bytes)
    if len(payload) > max_file_bytes:
        raise AttachmentError(
            f"{_element_name(element)} exceeds the upload size limit."
        )
    return payload


def _extract_text(name: str, mime: str, payload: bytes) -> str:
    extension = Path(name).suffix.casefold()
    if extension == ".pdf" or mime == "application/pdf":
        try:
            reader = PdfReader(io.BytesIO(payload))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as error:
            raise AttachmentError(f"Could not read PDF {name}.") from error
    if (
        extension == ".docx"
        or mime
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        try:
            document = Document(io.BytesIO(payload))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
        except Exception as error:
            raise AttachmentError(f"Could not read DOCX file {name}.") from error

    guessed_mime = mimetypes.guess_type(name)[0] or mime
    if (
        extension not in _TEXT_EXTENSIONS
        and not guessed_mime.startswith("text/")
        and guessed_mime not in {"application/json", "application/xml"}
    ):
        raise AttachmentError(f"Unsupported attachment type: {name}.")
    text = payload.decode("utf-8-sig", errors="replace")
    if extension in {".html", ".htm"}:
        parser = _HTMLTextExtractor()
        parser.feed(text)
        return "\n".join(parser.parts)
    if extension == ".json":
        try:
            return json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return text
    if extension == ".csv":
        rows = csv.reader(io.StringIO(text))
        return "\n".join(" | ".join(cell for cell in row) for row in rows)
    return text


def _validate_and_encode_image(payload: bytes) -> str:
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.verify()
            if image.width * image.height > 40_000_000:
                raise AttachmentError("Image dimensions are too large.")
    except AttachmentError:
        raise
    except Exception as error:
        raise AttachmentError("The uploaded image is invalid.") from error
    return base64.b64encode(payload).decode("ascii")
