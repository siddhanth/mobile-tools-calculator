"""
PDF Utilities for PMS Analyzer.
Helper functions for extracting text and tables from PDF files.
"""

import re
from datetime import datetime, date
from typing import List, Dict, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        Concatenated text from all pages
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")
    
    text_parts = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    
    return "\n".join(text_parts)


def extract_tables_from_pdf(pdf_path: str, page_numbers: List[int] = None) -> List[List[List[str]]]:
    """
    Extract tables from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        page_numbers: Optional list of specific page numbers (0-indexed)
    
    Returns:
        List of tables, where each table is a list of rows, and each row is a list of cells
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")
    
    all_tables = []
    
    with pdfplumber.open(pdf_path) as pdf:
        pages_to_process = pdf.pages
        if page_numbers:
            pages_to_process = [pdf.pages[i] for i in page_numbers if i < len(pdf.pages)]
        
        for page in pages_to_process:
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)
    
    return all_tables


def find_date_in_text(text: str, patterns: List[str] = None) -> Optional[date]:
    """
    Find and parse a date from text using common patterns.
    
    Args:
        text: Text to search for dates
        patterns: Optional list of regex patterns with named group 'date'
    
    Returns:
        Parsed date or None if not found
    """
    if patterns is None:
        # Common date patterns found in PMS reports
        patterns = [
            # "Holding Report as on 15-Dec-2025" or "Report as on 15-Dec-2025"
            r'(?:Holding\s+)?Report\s+as\s+(?:on\s+)?(?P<date>\d{1,2}[-/]\w{3}[-/]\d{2,4})',
            # "as on 15/12/2025" or "as on 15-12-2025"
            r'as\s+on\s+(?P<date>\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            # "Date: 15-Dec-2025" or "Date : 15/12/2025"
            r'Date\s*:\s*(?P<date>\d{1,2}[-/]\w{3}[-/]\d{2,4})',
            r'Date\s*:\s*(?P<date>\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            # "15 December 2025" or "December 15, 2025"
            r'(?P<date>\d{1,2}\s+\w+\s+\d{4})',
            r'(?P<date>\w+\s+\d{1,2},?\s+\d{4})',
        ]
    
    date_formats = [
        '%d-%b-%Y',  # 15-Dec-2025
        '%d-%b-%y',  # 15-Dec-25
        '%d/%m/%Y',  # 15/12/2025
        '%d/%m/%y',  # 15/12/25
        '%d-%m-%Y',  # 15-12-2025
        '%d-%m-%y',  # 15-12-25
        '%d %B %Y',  # 15 December 2025
        '%B %d, %Y', # December 15, 2025
        '%B %d %Y',  # December 15 2025
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group('date').strip()
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt).date()
                    logger.debug(f"Parsed date '{date_str}' with format '{fmt}'")
                    return parsed_date
                except ValueError:
                    continue
    
    logger.warning(f"Could not find valid date in text")
    return None


def clean_numeric_value(value: str) -> Optional[float]:
    """
    Clean and parse a numeric value from text.
    Handles commas, parentheses (negative), and currency symbols.
    
    Args:
        value: String value to parse
    
    Returns:
        Float value or None if parsing fails
    """
    if not value or not isinstance(value, str):
        return None
    
    # Remove common non-numeric characters
    cleaned = value.strip()
    cleaned = re.sub(r'[₹$€£,\s]', '', cleaned)
    
    # Handle parentheses as negative
    is_negative = False
    if cleaned.startswith('(') and cleaned.endswith(')'):
        is_negative = True
        cleaned = cleaned[1:-1]
    elif cleaned.startswith('-'):
        is_negative = True
        cleaned = cleaned[1:]
    
    # Handle percentage
    is_percentage = cleaned.endswith('%')
    if is_percentage:
        cleaned = cleaned[:-1]
    
    try:
        result = float(cleaned)
        if is_negative:
            result = -result
        return result
    except ValueError:
        return None


def normalize_stock_name(name: str) -> str:
    """
    Normalize a stock name for consistency.
    
    Args:
        name: Raw stock name
    
    Returns:
        Normalized stock name
    """
    if not name:
        return ""
    
    # Remove extra whitespace
    normalized = ' '.join(name.split())
    
    # Remove common suffixes
    suffixes_to_remove = [' LTD', ' LIMITED', ' PVT', ' PRIVATE', ' INC', ' CORP']
    upper_name = normalized.upper()
    for suffix in suffixes_to_remove:
        if upper_name.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            break
    
    return normalized.strip()


def find_section_in_text(text: str, section_marker: str, end_marker: str = None) -> Optional[str]:
    """
    Find a specific section in text based on markers.
    
    Args:
        text: Full text to search
        section_marker: Text that marks the beginning of the section
        end_marker: Optional text that marks the end of the section
    
    Returns:
        Section text or None if not found
    """
    start_idx = text.find(section_marker)
    if start_idx == -1:
        # Try case-insensitive search
        text_lower = text.lower()
        start_idx = text_lower.find(section_marker.lower())
    
    if start_idx == -1:
        return None
    
    section_start = start_idx + len(section_marker)
    
    if end_marker:
        end_idx = text.find(end_marker, section_start)
        if end_idx == -1:
            text_lower = text.lower()
            end_idx = text_lower.find(end_marker.lower(), section_start)
        
        if end_idx != -1:
            return text[section_start:end_idx]
    
    return text[section_start:]


def extract_table_after_header(
    tables: List[List[List[str]]],
    header_pattern: str
) -> Tuple[Optional[List[str]], Optional[List[List[str]]]]:
    """
    Find a table that contains a specific header pattern.
    
    Args:
        tables: List of tables extracted from PDF
        header_pattern: Regex pattern to match in header row
    
    Returns:
        Tuple of (header_row, data_rows) or (None, None) if not found
    """
    pattern = re.compile(header_pattern, re.IGNORECASE)
    
    for table in tables:
        if not table:
            continue
        
        # Check first few rows for header
        for i, row in enumerate(table[:3]):
            row_text = ' '.join(str(cell) for cell in row if cell)
            if pattern.search(row_text):
                header = row
                data = table[i+1:]
                return header, data
    
    return None, None

