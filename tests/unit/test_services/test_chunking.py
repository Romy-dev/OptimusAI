"""Tests for document chunking logic."""

import pytest

from app.workers.document_ingestion import chunk_text, parse_faq_csv


class TestChunkText:
    def test_basic_chunking(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunk_text(text, chunk_size=1000)
        assert len(chunks) >= 1
        assert chunks[0]["content"]
        assert chunks[0]["index"] == 0

    def test_empty_text(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_section_detection(self):
        text = "# Products\n\nWe sell textiles.\n\n# Services\n\nWe deliver."
        chunks = chunk_text(text, chunk_size=1000)
        assert len(chunks) >= 1

    def test_large_text_splits(self):
        # Create text that exceeds chunk_size
        paragraphs = [f"This is paragraph number {i} with enough content." * 5 for i in range(20)]
        text = "\n\n".join(paragraphs)
        chunks = chunk_text(text, chunk_size=50)
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk["content"]
            assert isinstance(chunk["index"], int)

    def test_chunks_have_sequential_indices(self):
        text = "\n\n".join([f"Paragraph {i}. " * 20 for i in range(10)])
        chunks = chunk_text(text, chunk_size=30)
        indices = [c["index"] for c in chunks]
        assert indices == list(range(len(chunks)))


class TestParseFaqCsv:
    def test_basic_faq(self):
        csv_content = "Quel est le prix?,3500 FCFA\nLivrez-vous?,Oui à Ouaga"
        chunks = parse_faq_csv(csv_content)
        assert len(chunks) == 2
        assert "3500 FCFA" in chunks[0]["content"]
        assert chunks[0]["section_title"] == "Quel est le prix?"

    def test_empty_csv(self):
        assert parse_faq_csv("") == []

    def test_skips_incomplete_rows(self):
        csv_content = "Question only\nQ,A\nAnother"
        chunks = parse_faq_csv(csv_content)
        assert len(chunks) == 1  # Only "Q,A" is valid
