# tests/test_provenance.py
from datetime import date

from memsearch.provenance import days_since, extract_file_date


def test_extract_file_date_from_dated_filename():
    assert extract_file_date("/x/.memsearch/memory/2026-06-19.md") == date(2026, 6, 19)


def test_extract_file_date_none_for_undated():
    assert extract_file_date("/x/.memsearch/memory/MEMORY.md") is None


def test_extract_file_date_invalid_date_returns_none():
    assert extract_file_date("/x/2026-13-45.md") is None


def test_days_since_counts_whole_days():
    assert days_since(date(2026, 6, 10), today=date(2026, 6, 19)) == 9


def test_days_since_none_for_undated():
    assert days_since(None, today=date(2026, 6, 19)) is None


def test_days_since_clamps_future_to_zero():
    assert days_since(date(2026, 6, 25), today=date(2026, 6, 19)) == 0
