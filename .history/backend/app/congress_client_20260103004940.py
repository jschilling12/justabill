import httpx
import hashlib
import re
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class CongressAPIClient:
    """Client for Congress.gov API"""
    
    def __init__(self):
        self.api_key = settings.CONGRESS_API_KEY
        self.base_url = "https://api.congress.gov/v3"
    
    async def get_bill(self, congress: int, bill_type: str, bill_number: int) -> Dict[str, Any]:
        """Fetch bill metadata from Congress.gov API"""
        url = f"{self.base_url}/bill/{congress}/{bill_type}/{bill_number}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                params={"api_key": self.api_key, "format": "json"}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("bill", {})
    
    async def get_bill_text_versions(self, congress: int, bill_type: str, bill_number: int) -> List[Dict[str, Any]]:
        """Fetch available text versions for a bill"""
        url = f"{self.base_url}/bill/{congress}/{bill_type}/{bill_number}/text"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                params={"api_key": self.api_key, "format": "json"}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("textVersions", [])
    
    async def get_recent_bills(self, days: int = 1, offset: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch bills updated in the last N days"""
        url = f"{self.base_url}/bill"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                params={
                    "api_key": self.api_key,
                    "format": "json",
                    "offset": offset,
                    "limit": limit,
                    "sort": "updateDate+desc"
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("bills", [])


class BillTextFetcher:
    """Fetches and processes bill text from various sources"""
    
    async def fetch_text(self, text_url: str) -> Tuple[str, str]:
        """
        Fetch bill text from a URL
        Returns: (text_content, content_hash)
        """
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(text_url)
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "")
            
            if "html" in content_type:
                text = self._extract_text_from_html(response.text)
            elif "xml" in content_type:
                text = self._extract_text_from_xml(response.text)
            elif "text/plain" in content_type:
                text = response.text
            else:
                # Try to parse as HTML anyway
                text = self._extract_text_from_html(response.text)
            
            # Compute hash
            content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
            
            return text, content_hash
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract text from HTML bill format"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Try to find the main bill content
        # Congress.gov typically uses specific divs/sections
        main_content = soup.find('div', class_='generated-html-container')
        if not main_content:
            main_content = soup.find('body')
        
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def _extract_text_from_xml(self, xml: str) -> str:
        """Extract text from XML bill format"""
        soup = BeautifulSoup(xml, 'lxml-xml')
        
        # Remove metadata elements
        for tag in soup.find_all(['metadata', 'dublinCore']):
            tag.decompose()
        
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)


class BillSectionizer:
    """Splits bill text into logical sections"""
    
    def section_bill(self, bill_text: str) -> List[Dict[str, Any]]:
        """
        Split bill text into sections
        Returns: List of {section_key, heading, text, order_index}
        """
        sections = []
        
        # Patterns for section identification
        section_patterns = [
            r'^SEC\.\s+(\d+)\.\s+(.+?)$',  # SEC. 101. HEADING
            r'^SECTION\s+(\d+)\.\s+(.+?)$',  # SECTION 1. HEADING
            r'^§\s*(\d+)\.\s+(.+?)$',  # § 101. HEADING
            r'^TITLE\s+([IVXLCDM]+)—(.+?)$',  # TITLE I—HEADING
        ]
        
        lines = bill_text.split('\n')
        current_section = None
        current_lines = []
        order_index = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check if this line is a section heading
            is_section_header = False
            section_key = None
            heading = None
            
            for pattern in section_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    is_section_header = True
                    if len(match.groups()) == 2:
                        section_key = f"SEC. {match.group(1)}"
                        heading = match.group(2).strip()
                    else:
                        section_key = match.group(0)
                        heading = ""
                    break
            
            if is_section_header:
                # Save previous section
                if current_section is not None:
                    section_text = '\n'.join(current_lines).strip()
                    if section_text:  # Only add non-empty sections
                        sections.append({
                            'section_key': current_section['section_key'],
                            'heading': current_section['heading'],
                            'text': section_text,
                            'order_index': order_index
                        })
                        order_index += 1
                
                # Start new section
                current_section = {
                    'section_key': section_key,
                    'heading': heading
                }
                current_lines = []
            else:
                # Add line to current section
                if current_section is None:
                    # Create a "Preamble" section for text before first section
                    current_section = {
                        'section_key': 'PREAMBLE',
                        'heading': 'Preamble'
                    }
                current_lines.append(line)
        
        # Add final section
        if current_section is not None:
            section_text = '\n'.join(current_lines).strip()
            if section_text:
                sections.append({
                    'section_key': current_section['section_key'],
                    'heading': current_section['heading'],
                    'text': section_text,
                    'order_index': order_index
                })
        
        # If no sections found, create one section with all text
        if not sections:
            sections.append({
                'section_key': 'FULL_TEXT',
                'heading': 'Full Bill Text',
                'text': bill_text,
                'order_index': 0
            })
        
        logger.info(f"Sectionized bill into {len(sections)} sections")
        return sections
    
    def chunk_long_section(self, section_text: str, max_tokens: int = 4000) -> List[str]:
        """
        Split a very long section into smaller chunks
        This is a fallback for sections that are too long for LLM context
        """
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        if len(section_text) <= max_chars:
            return [section_text]
        
        chunks = []
        paragraphs = section_text.split('\n\n')
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            if current_length + para_length > max_chars and current_chunk:
                # Save current chunk
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length
        
        # Add final chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
