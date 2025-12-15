# PMS Analyzer Module

Integrated PMS (Portfolio Management Service) analysis module for tracking and analyzing holdings from multiple PMS providers.

## Features

- **PDF Report Parsing**: Extract holdings data from PMS report PDFs
- **Multi-Provider Support**: Extensible architecture (currently supports Sameeksha)
- **SQLite Database**: Persistent storage for reports and holdings
- **Streamlit Integration**: Integrated into main app as a dedicated tab

## Directory Structure

```
pms/
├── database/
│   ├── __init__.py
│   ├── db_manager.py      # SQLite database operations
│   └── schema.sql         # Database schema
├── parsers/
│   ├── __init__.py
│   ├── base_parser.py     # Abstract base class for parsers
│   └── sameeksha_parser.py # Sameeksha PMS parser
├── utils/
│   ├── __init__.py
│   └── pdf_utils.py       # PDF extraction utilities
├── reports/               # Sample PDF reports
├── pms_data.db           # SQLite database (auto-created)
└── README.md             # This file
```

## Usage

### Via Streamlit App

1. Launch the main app: `streamlit run app.py`
2. Navigate to the **🏢 PMS** tab
3. Upload a PMS report PDF using the sidebar
4. View portfolio analytics, holdings, and returns

### Via CLI (Optional)

You can also use the standalone CLI from the parent pms_analyzer project:

```bash
cd pms_analyzer
python main.py parse reports/report.pdf --provider sameeksha
python main.py list-reports
python main.py show-holdings --report-id 1
```

## Database Schema

### pms_reports
- `id`: Primary key
- `pms_provider`: Provider name (e.g., "sameeksha")
- `report_date`: Report date
- `file_path`: Original file path
- `file_hash`: MD5 hash for duplicate detection
- `uploaded_at`: Import timestamp

### holdings
- `id`: Primary key
- `report_id`: Foreign key to pms_reports
- `stock_name`: Security name
- `isin`: ISIN code (optional)
- `quantity`: Number of units
- `market_value`: Current market value
- `portfolio_percentage`: % of portfolio
- `cost_price`: Average cost price
- `current_price`: Current market price
- `gain_loss`: Unrealized gain/loss
- `gain_loss_percentage`: Return percentage
- `sector`: Asset category
- `other_fields`: JSON for additional data

## Supported Providers

- **Sameeksha**: Parses reports with format "Security Name Qty AvgCost MktRate TotalCost MktValue %Portfolio"

## Adding New Providers

1. Create a parser in `parsers/` inheriting from `BaseParser`
2. Implement `extract_report_date()` and `extract_holdings()`
3. Register in `parsers/__init__.py` PARSER_REGISTRY
4. Test with sample PDF

Example:
```python
from parsers.base_parser import BaseParser

class NewProviderParser(BaseParser):
    PROVIDER_NAME = "new_provider"
    
    def extract_report_date(self):
        # Your implementation
        pass
    
    def extract_holdings(self):
        # Your implementation
        pass
```

## Dependencies

- pdfplumber>=0.10.0 - PDF parsing
- python-dateutil>=2.8.2 - Date parsing
- pandas - Data manipulation
- plotly - Visualizations

All dependencies are included in the main `requirements.txt`.

