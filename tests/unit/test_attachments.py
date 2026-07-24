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


@pytest.mark.asyncio
async def test_rejects_unsupported_binary_attachment() -> None:
    with pytest.raises(AttachmentError, match="Unsupported"):
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
