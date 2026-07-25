import base64
import io
from types import SimpleNamespace

import pytest
from PIL import Image

from src.chat.attachments import AttachmentError, process_attachments


@pytest.mark.asyncio
async def test_processes_plain_text_attachment() -> None:
    result = await process_attachments(
        [SimpleNamespace(name="notes.txt", mime="text/plain", content=b"hello")],
        max_files=2,
        max_file_bytes=1024,
        max_extracted_chars=100,
    )

    assert "Attachment: notes.txt" in result.text
    assert "hello" in result.text
    assert result.images == []


@pytest.mark.asyncio
async def test_validates_and_encodes_image() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buffer, format="PNG")

    result = await process_attachments(
        [
            SimpleNamespace(
                name="picture.png",
                mime="image/png",
                content=buffer.getvalue(),
            )
        ],
        max_files=2,
        max_file_bytes=1024,
        max_extracted_chars=100,
    )

    assert result.text == ""
    assert len(result.images) == 1
    with Image.open(io.BytesIO(base64.b64decode(result.images[0]))) as normalized:
        assert normalized.format == "JPEG"


@pytest.mark.asyncio
async def test_normalizes_webp_for_ollama_compatibility() -> None:
    buffer = io.BytesIO()
    Image.new("RGBA", (2, 2), color=(255, 0, 0, 128)).save(
        buffer, format="WEBP"
    )

    result = await process_attachments(
        [
            SimpleNamespace(
                name="atom.webp",
                mime="image/webp",
                content=buffer.getvalue(),
            )
        ],
        max_files=2,
        max_file_bytes=2048,
        max_extracted_chars=100,
    )

    with Image.open(io.BytesIO(base64.b64decode(result.images[0]))) as normalized:
        assert normalized.format in {"JPEG", "PNG"}


@pytest.mark.asyncio
async def test_rejects_unsupported_binary_attachment() -> None:
    with pytest.raises(AttachmentError, match="Could not read archive"):
        await process_attachments(
            [
                SimpleNamespace(
                    name="archive.zip",
                    mime="application/zip",
                    content=b"not a zip",
                )
            ],
            max_files=2,
            max_file_bytes=1024,
            max_extracted_chars=100,
        )


@pytest.mark.asyncio
async def test_extracts_readable_files_from_zip_archive() -> None:
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("notes/readme.md", "# Useful notes")
        archive.writestr("data/config.json", '{"enabled": true}')

    result = await process_attachments(
        [
            SimpleNamespace(
                name="project.zip",
                mime="application/zip",
                content=buffer.getvalue(),
            )
        ],
        max_files=2,
        max_file_bytes=4096,
        max_extracted_chars=1000,
    )

    assert "File: readme.md" in result.text
    assert "Useful notes" in result.text
    assert '"enabled": true' in result.text
