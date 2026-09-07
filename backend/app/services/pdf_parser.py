import re
from dataclasses import dataclass
from typing import Any

import pymupdf


@dataclass(frozen=True, slots=True)
class ExtractedBlock:
    page_number: int
    block_index: int
    text: str
    bbox: list[float]
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ParsedPdf:
    page_count: int
    blocks: list[ExtractedBlock]


def _clean_block_text(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _is_useful_text(text: str) -> bool:
    tokens = re.findall(r"[\w%$€£¥]+", text, flags=re.UNICODE)
    return len(tokens) >= 2


def parse_pdf(pdf_bytes: bytes) -> ParsedPdf:
    blocks: list[ExtractedBlock] = []

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        if pdf.needs_pass:
            raise ValueError("Password-protected PDFs are not supported")

        for page_index, page in enumerate(pdf):
            page_number = page_index + 1
            page_blocks = page.get_text("blocks", sort=True)
            useful_block_index = 0

            for source_order, raw_block in enumerate(page_blocks):
                block_type = int(raw_block[6]) if len(raw_block) > 6 else 0
                if block_type != 0:
                    continue

                text = _clean_block_text(str(raw_block[4]))
                if not _is_useful_text(text):
                    continue

                blocks.append(
                    ExtractedBlock(
                        page_number=page_number,
                        block_index=useful_block_index,
                        text=text,
                        bbox=[float(value) for value in raw_block[:4]],
                        metadata={
                            "source_block_number": int(raw_block[5]),
                            "source_order": source_order,
                            "extraction_method": "pymupdf_blocks",
                            "page_width": float(page.rect.width),
                            "page_height": float(page.rect.height),
                        },
                    )
                )
                useful_block_index += 1

        return ParsedPdf(page_count=pdf.page_count, blocks=blocks)

