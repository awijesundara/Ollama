from src.ui.pdf_export import (
    explicit_pdf_text,
    is_pdf_export_request,
    render_pdf,
)


def test_detects_natural_and_explicit_pdf_requests() -> None:
    assert is_pdf_export_request("Can you make this response a PDF file?")
    assert is_pdf_export_request("/pdf")
    assert explicit_pdf_text("/pdf A custom document") == "A custom document"
    assert not is_pdf_export_request("Explain how PDF files work")


def test_renders_valid_pdf_document() -> None:
    payload = render_pdf(
        "# Capabilities\n\n- Answer questions\n- Process documents",
        title="Capabilities",
    )

    assert payload.startswith(b"%PDF-")
    assert len(payload) > 500
