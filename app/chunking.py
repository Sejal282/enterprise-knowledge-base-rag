
import re


def split_text_into_chunks(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[str]:
    """Split text into overlapping chunks while preserving section headings."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = text.strip()

    if not text:
        return []

    # Recognize standalone headings in the sample handbook.
    headings = {
        "Purpose",
        "Working Hours",
        "Information Security",
        "Document Management",
    }

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    sections = []
    current_section = []

    for line in lines:
        if line in headings and current_section:
            sections.append("\n".join(current_section))
            current_section = [line]
        else:
            current_section.append(line)

    if current_section:
        sections.append("\n".join(current_section))

    chunks = []
    current_chunk = ""

    for section in sections:
        # Split unusually long sections into smaller word-safe pieces.
        if len(section) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            start = 0

            while start < len(section):
                end = min(start + chunk_size, len(section))

                if end < len(section):
                    boundary = section.rfind(" ", start, end)
                    if boundary > start:
                        end = boundary

                piece = section[start:end].strip()

                if piece:
                    chunks.append(piece)

                if end >= len(section):
                    break

                start = max(start + 1, end - overlap)

                while start < len(section) and not section[start].isspace():
                    start += 1

                while start < len(section) and section[start].isspace():
                    start += 1

            continue

        candidate = (
            current_chunk + "\n" + section
            if current_chunk
            else section
        )

        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk)

            current_chunk = section

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
