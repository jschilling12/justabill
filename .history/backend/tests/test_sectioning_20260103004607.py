import pytest
from app.congress_client import BillSectionizer


def test_section_bill_with_sec_headings():
    """Test sectionizing bill with SEC. headings"""
    sectionizer = BillSectionizer()
    
    bill_text = """
PREAMBLE TEXT HERE

SEC. 1. SHORT TITLE
This Act may be cited as the Test Act.

SEC. 2. DEFINITIONS
In this Act:
(1) TERM 1 means something
(2) TERM 2 means something else

SEC. 3. AUTHORIZATION
The Secretary shall authorize something.
    """.strip()
    
    sections = sectionizer.section_bill(bill_text)
    
    assert len(sections) >= 3
    assert any(s['section_key'] == 'SEC. 1' for s in sections)
    assert any(s['section_key'] == 'SEC. 2' for s in sections)
    assert any(s['section_key'] == 'SEC. 3' for s in sections)


def test_section_bill_without_clear_sections():
    """Test sectionizing bill without clear sections"""
    sectionizer = BillSectionizer()
    
    bill_text = """
This is a bill with no clear section markers.
It just has paragraphs of text.
We should get one section for the full text.
    """.strip()
    
    sections = sectionizer.section_bill(bill_text)
    
    assert len(sections) == 1
    assert sections[0]['section_key'] == 'FULL_TEXT'


def test_chunk_long_section():
    """Test chunking a very long section"""
    sectionizer = BillSectionizer()
    
    # Create a long text (more than 4000 tokens worth)
    long_text = "This is a paragraph. " * 1000
    
    chunks = sectionizer.chunk_long_section(long_text, max_tokens=1000)
    
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) < 4000 * 4  # max_tokens * 4 chars per token
