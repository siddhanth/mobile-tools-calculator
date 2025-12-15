"""
Sameeksha PMS Report Parser.
Parses holding reports from Sameeksha Portfolio Management Services.
"""

import re
from datetime import date
from typing import List, Dict, Any, Optional
import logging

from parsers.base_parser import BaseParser
from utils.pdf_utils import (
    find_date_in_text,
    clean_numeric_value,
    normalize_stock_name,
)

logger = logging.getLogger(__name__)


class SameekshaParser(BaseParser):
    """
    Parser for Sameeksha PMS holding reports.
    
    Expected report structure:
    - "(iii) Holding Report as of DD/MM/YYYY" section header
    - Sub-sections: Shares, Mutual Funds, Futures, Cash/Bank, Other Assets
    - Row format (merged cells): "Security Name QTY AVG_COST MKT_RATE TOTAL_COST MKT_VALUE %_PORTFOLIO"
    """
    
    PROVIDER_NAME = "sameeksha"
    
    # Asset type categories (these are section headers within holdings)
    ASSET_TYPE_HEADERS = ['shares', 'mutual funds', 'futures', 'cash / bank', 'cash', 'other assets']
    
    def extract_report_date(self) -> Optional[date]:
        """Extract the report date from Sameeksha PDF."""
        patterns = [
            r'Holding\s+Report\s+as\s+(?:of|on)\s+(?P<date>\d{1,2}/\d{1,2}/\d{4})',
            r'Market\s+Value\s+as\s+on\s+(?P<date>\d{1,2}/\d{1,2}/\d{4})',
            r'as\s+(?:of|on)\s+(?P<date>\d{1,2}/\d{1,2}/\d{4})',
        ]
        
        report_date = find_date_in_text(self.text_content, patterns)
        
        if report_date:
            logger.info(f"Extracted report date: {report_date}")
        else:
            logger.warning("Could not extract report date from Sameeksha report")
        
        return report_date
    
    def _is_holding_section_start(self, text: str) -> bool:
        """Check if this row marks the start of holding section."""
        return 'holding report' in text.lower()
    
    def _is_asset_type_header(self, text: str) -> Optional[str]:
        """Check if text is an asset type header, return normalized name."""
        text_lower = text.lower().strip()
        for asset_type in self.ASSET_TYPE_HEADERS:
            if text_lower == asset_type:
                return asset_type.title()
        return None
    
    def _is_column_header_row(self, text: str) -> bool:
        """Check if this is a column header row."""
        text_lower = text.lower()
        return 'security name' in text_lower and 'quantity' in text_lower
    
    def _parse_holding_row(self, row_text: str, asset_type: str) -> Optional[Dict[str, Any]]:
        """
        Parse a holding row where data is merged.
        
        Format: "Security Name QTY AVG_COST MKT_RATE TOTAL_COST MKT_VALUE %_PORTFOLIO"
        Example: "Coromandel International Ltd 40.00 2,245.79 2,382.10 89,831.57 95,284.00 0.19"
        """
        if not row_text:
            return None
        
        # Handle newlines
        row_text = row_text.replace('\n', ' ').strip()
        
        # Skip if it's a header or asset type
        if self._is_column_header_row(row_text):
            return None
        if self._is_asset_type_header(row_text):
            return None
        
        # Pattern to find numbers (with commas, decimals)
        number_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)'
        
        # Find all numbers
        numbers = re.findall(number_pattern, row_text)
        
        if len(numbers) < 6:
            # Need at least 6 numbers for a valid holding row
            # (Qty, AvgCost, MktRate, TotalCost, MktValue, %Portfolio)
            return None
        
        # Stock name is everything before the first number
        first_number_match = re.search(number_pattern, row_text)
        if not first_number_match:
            return None
        
        stock_name = row_text[:first_number_match.start()].strip()
        
        # Validate stock name
        if not stock_name or len(stock_name) < 2:
            return None
        
        # Parse numbers
        parsed_numbers = []
        for n in numbers:
            val = clean_numeric_value(n)
            if val is not None:
                parsed_numbers.append(val)
        
        if len(parsed_numbers) < 6:
            return None
        
        # Validate: the last number should be < 100 (percentage)
        if parsed_numbers[-1] > 100:
            return None
        
        holding = {
            'stock_name': normalize_stock_name(stock_name),
            'sector': asset_type,
            'quantity': parsed_numbers[0],
            'cost_price': parsed_numbers[1],      # Average Cost
            'current_price': parsed_numbers[2],   # Market Rate
            # parsed_numbers[3] is Total Cost
            'market_value': parsed_numbers[4],    # Market Value
            'portfolio_percentage': parsed_numbers[5],  # % to Portfolio
        }
        
        # Calculate gain/loss
        if holding['cost_price'] and holding['current_price'] and holding['cost_price'] > 0:
            cost = holding['cost_price']
            current = holding['current_price']
            holding['gain_loss_percentage'] = ((current - cost) / cost) * 100
            
            if holding['quantity']:
                holding['gain_loss'] = (current - cost) * holding['quantity']
        
        return holding
    
    def extract_holdings(self) -> List[Dict[str, Any]]:
        """
        Extract holdings from Sameeksha PDF.
        
        Only processes tables after "(iii) Holding Report" section.
        """
        holdings = []
        current_asset_type = 'Shares'
        in_holding_section = False
        
        for table in self.tables:
            if not table:
                continue
            
            for row in table:
                if not row:
                    continue
                
                # Get row text from first non-empty cell
                row_text = ''
                for cell in row:
                    if cell and str(cell).strip():
                        row_text = str(cell).strip()
                        break
                
                if not row_text:
                    continue
                
                # Check for holding section start
                if self._is_holding_section_start(row_text):
                    in_holding_section = True
                    logger.debug("Entered holding section")
                    continue
                
                # Only process rows after we're in the holding section
                if not in_holding_section:
                    continue
                
                # Check for asset type headers
                asset_type = self._is_asset_type_header(row_text)
                if asset_type:
                    current_asset_type = asset_type
                    logger.debug(f"Asset type: {current_asset_type}")
                    continue
                
                # Skip column headers
                if self._is_column_header_row(row_text):
                    continue
                
                # Parse the holding row
                holding = self._parse_holding_row(row_text, current_asset_type)
                if holding:
                    logger.debug(f"Parsed: {holding['stock_name']} - {holding.get('market_value', 0)}")
                    holdings.append(holding)
        
        logger.info(f"Extracted {len(holdings)} holdings from Sameeksha report")
        return holdings
