"""
Base Parser for PMS Reports.
Abstract base class defining the interface for all PMS report parsers.
"""

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """
    Abstract base class for PMS report parsers.
    
    All PMS-specific parsers should inherit from this class and implement
    the abstract methods to ensure a consistent interface.
    """
    
    # Provider name - should be overridden by subclasses
    PROVIDER_NAME: str = "base"
    
    def __init__(self, pdf_path: str):
        """
        Initialize the parser with a PDF file path.
        
        Args:
            pdf_path: Path to the PDF file to parse
        
        Raises:
            FileNotFoundError: If the PDF file doesn't exist
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self._text_content: Optional[str] = None
        self._tables: Optional[List] = None
    
    @property
    def text_content(self) -> str:
        """Lazy-load text content from PDF."""
        if self._text_content is None:
            from utils.pdf_utils import extract_text_from_pdf
            self._text_content = extract_text_from_pdf(str(self.pdf_path))
        return self._text_content
    
    @property
    def tables(self) -> List:
        """Lazy-load tables from PDF."""
        if self._tables is None:
            from utils.pdf_utils import extract_tables_from_pdf
            self._tables = extract_tables_from_pdf(str(self.pdf_path))
        return self._tables
    
    @abstractmethod
    def extract_report_date(self) -> Optional[date]:
        """
        Extract the report date from the PDF.
        
        Returns:
            The report date, or None if not found
        """
        pass
    
    @abstractmethod
    def extract_holdings(self) -> List[Dict[str, Any]]:
        """
        Extract holdings data from the PDF.
        
        Returns:
            List of holding dictionaries with standardized keys:
            - stock_name: str (required)
            - isin: str (optional)
            - quantity: float (optional)
            - market_value: float (optional)
            - portfolio_percentage: float (optional)
            - cost_price: float (optional)
            - current_price: float (optional)
            - gain_loss: float (optional)
            - gain_loss_percentage: float (optional)
            - sector: str (optional)
            - other_fields: dict (optional, for provider-specific data)
        """
        pass
    
    def validate_holdings(self, holdings: List[Dict[str, Any]]) -> bool:
        """
        Validate extracted holdings data.
        
        Args:
            holdings: List of holding dictionaries to validate
        
        Returns:
            True if all holdings are valid
        
        Raises:
            ValueError: If validation fails with details
        """
        if not holdings:
            raise ValueError("No holdings extracted from the report")
        
        errors = []
        for i, holding in enumerate(holdings):
            # Check required field
            if not holding.get('stock_name'):
                errors.append(f"Holding {i+1}: Missing stock_name")
            
            # Validate numeric fields
            numeric_fields = [
                'quantity', 'market_value', 'portfolio_percentage',
                'cost_price', 'current_price', 'gain_loss', 'gain_loss_percentage'
            ]
            for field in numeric_fields:
                value = holding.get(field)
                if value is not None and not isinstance(value, (int, float)):
                    errors.append(f"Holding {i+1}: {field} must be numeric, got {type(value)}")
            
            # Validate portfolio percentage range
            pct = holding.get('portfolio_percentage')
            if pct is not None and not (0 <= pct <= 100):
                errors.append(f"Holding {i+1}: portfolio_percentage {pct} out of range [0, 100]")
        
        if errors:
            raise ValueError(f"Validation failed:\n" + "\n".join(errors))
        
        return True
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse the PDF and return structured data.
        
        Returns:
            Dictionary with:
            - provider: str
            - report_date: date
            - holdings: List[Dict]
            - summary: Dict with totals/statistics
        
        Raises:
            ValueError: If parsing fails
        """
        logger.info(f"Parsing {self.PROVIDER_NAME} report: {self.pdf_path}")
        
        report_date = self.extract_report_date()
        if report_date is None:
            raise ValueError(f"Could not extract report date from {self.pdf_path}")
        
        holdings = self.extract_holdings()
        self.validate_holdings(holdings)
        
        # Calculate summary
        total_value = sum(h.get('market_value', 0) or 0 for h in holdings)
        total_gain_loss = sum(h.get('gain_loss', 0) or 0 for h in holdings)
        
        return {
            'provider': self.PROVIDER_NAME,
            'report_date': report_date,
            'holdings': holdings,
            'summary': {
                'total_stocks': len(holdings),
                'total_value': total_value,
                'total_gain_loss': total_gain_loss,
            }
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.pdf_path}')"

