import hashlib

import httpx
import pymupdf

from app.core.config import Settings, get_settings
from app.main import app
from app.models.document import Document, DocumentStatus
from app.models.evidence_chunk import EvidenceChunk


def make_pdf(pages: list[list[tuple[float, str]]]) -> bytes:
    pdf = pymupdf.open()
    for text_blocks in pages:
        page = pdf.new_page()
        for y_position, text in text_blocks:
            page.insert_text((72, y_position), text)
    content = pdf.tobytes()
    pdf.close()
    return content


async def upload_pdf(
    client: httpx.AsyncClient,
    content: bytes,
    *,
    filename: str = "report.pdf",
    content_type: str = "application/pdf",
) -> httpx.Response:
    return await client.post(
        "/api/documents",
        files={"file": (filename, content, content_type)},
    )


async def test_valid_pdf_parsing_hash_page_numbering_and_provenance(
    client: httpx.AsyncClient,
) -> None:
    pdf_bytes = make_pdf(
        [
            [(72, "Revenue was 42 million dollars")],
            [],
            [(72, "Headcount reached one hundred employees")],
        ]
    )

    response = await upload_pdf(client, pdf_bytes)

    assert response.status_code == 201
    payload = response.json()
    document = payload["document"]
    assert payload["already_existed"] is False
    assert document["content_hash"] == hashlib.sha256(pdf_bytes).hexdigest()
    assert document["status"] == "PROCESSED"
    assert document["page_count"] == 3
    assert document["evidence_chunk_count"] == 2

    evidence_response = await client.get(f"/api/documents/{document['id']}/evidence")
    assert evidence_response.status_code == 200
    evidence = evidence_response.json()
    assert evidence["total"] == 2
    assert [item["page_number"] for item in evidence["items"]] == [1, 3]
    assert all(item["document_id"] == document["id"] for item in evidence["items"])
    assert all(len(item["bbox"]) == 4 for item in evidence["items"])
    assert all(
        item["metadata"]["extraction_method"] == "pymupdf_blocks"
        for item in evidence["items"]
    )


async def test_rejects_invalid_file_type(client: httpx.AsyncClient) -> None:
    response = await upload_pdf(
        client,
        b"This is not a PDF",
        filename="notes.txt",
        content_type="text/plain",
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "invalid_file_type"
    assert await Document.count() == 0


async def test_rejects_zero_byte_pdf(client: httpx.AsyncClient) -> None:
    response = await upload_pdf(client, b"")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_file"
    assert await Document.count() == 0


async def test_rejects_pdf_over_configured_size(client: httpx.AsyncClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        max_upload_size_bytes=10,
        _env_file=None,
    )
    try:
        response = await upload_pdf(client, b"%PDF-1.7\nmore than ten bytes")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"
    assert await Document.count() == 0


async def test_corrupt_pdf_is_marked_failed(client: httpx.AsyncClient) -> None:
    response = await upload_pdf(client, b"%PDF-1.7\nthis file is corrupt")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "pdf_processing_failed"
    document = await Document.get(payload["error"]["details"]["document_id"])
    assert document is not None
    assert document.status is DocumentStatus.FAILED
    assert document.error_message is not None
    assert "PDF parsing failed" in document.error_message


async def test_duplicate_upload_returns_existing_document_without_duplicate_evidence(
    client: httpx.AsyncClient,
) -> None:
    pdf_bytes = make_pdf([[(72, "A reusable evidence statement")]])

    first_response = await upload_pdf(client, pdf_bytes)
    second_response = await upload_pdf(client, pdf_bytes, filename="renamed.pdf")

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    first_payload = first_response.json()
    second_payload = second_response.json()
    assert second_payload["already_existed"] is True
    assert second_payload["document"]["id"] == first_payload["document"]["id"]
    assert await Document.count() == 1
    assert await EvidenceChunk.count() == 1


async def test_evidence_ordering_page_filter_and_pagination(client: httpx.AsyncClient) -> None:
    pdf_bytes = make_pdf(
        [
            [
                (180, "This block appears second"),
                (80, "This block appears first"),
            ],
            [(72, "Evidence from page two")],
        ]
    )
    upload_response = await upload_pdf(client, pdf_bytes)
    document_id = upload_response.json()["document"]["id"]

    first_page = await client.get(
        f"/api/documents/{document_id}/evidence",
        params={"page": 1, "limit": 1},
    )
    second_item = await client.get(
        f"/api/documents/{document_id}/evidence",
        params={"page": 1, "limit": 1, "offset": 1},
    )

    assert first_page.status_code == 200
    assert first_page.json()["total"] == 2
    assert first_page.json()["items"][0]["text"] == "This block appears first"
    assert first_page.json()["items"][0]["block_index"] == 0
    assert second_item.json()["items"][0]["text"] == "This block appears second"
    assert second_item.json()["items"][0]["block_index"] == 1


async def test_list_detail_and_delete_cascade(client: httpx.AsyncClient) -> None:
    upload_response = await upload_pdf(
        client,
        make_pdf([[(72, "Evidence that will be deleted")]]),
    )
    document_id = upload_response.json()["document"]["id"]

    list_response = await client.get("/api/documents")
    detail_response = await client.get(f"/api/documents/{document_id}")

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["evidence_chunk_count"] == 1
    assert detail_response.status_code == 200
    assert detail_response.json()["original_filename"] == "report.pdf"

    delete_response = await client.delete(f"/api/documents/{document_id}")
    assert delete_response.status_code == 204
    assert await Document.count() == 0
    assert await EvidenceChunk.count() == 0

    missing_response = await client.get(f"/api/documents/{document_id}")
    assert missing_response.status_code == 404
    assert missing_response.json()["error"]["code"] == "document_not_found"
