# PMS Tab Specification

Last updated: 2025-12-15

## Overview

The PMS (Portfolio Management Service) tab provides a comprehensive interface for analyzing holdings from multiple PMS providers. Users can upload PMS reports in PDF format, and the system extracts, stores, and visualizes the holdings data.

## Features

### 1. Report Upload & Processing
- **Upload Interface**: Sidebar file uploader for PDF reports
- **Provider Selection**: Dropdown to select PMS provider (currently supports Sameeksha)
- **Automatic Parsing**: Extracts holdings data from PDF tables
- **Duplicate Detection**: Prevents re-importing the same report
- **Data Validation**: Validates extracted data before storage

### 2. Portfolio Overview
- **Key Metrics** (4 metric cards):
  - Total Portfolio Value (₹)
  - Number of Holdings
  - Average Return (%)
  - Total Gain/Loss (₹)
- **Holdings Table**: Sortable table with all holdings showing:
  - Stock name
  - Category/Sector
  - Quantity
  - Average Cost
  - Current Price
  - Market Value
  - Portfolio Weight (%)
  - Return (%)

### 3. Analysis & Visualizations
- **Portfolio Allocation Pie Chart**: Shows holdings by percentage
- **Top 10 Holdings Bar Chart**: Visual comparison of largest positions
- **Returns by Holding Chart**: Horizontal bar chart showing gains/losses
- Color-coded returns: Green for gains, Red for losses

### 4. Reports Management
- **Reports List**: Table of all imported reports with:
  - Report ID
  - Provider name
  - Report date
  - File name
  - Import timestamp
- **Delete Functionality**: Remove reports and associated holdings

## Sidebar Features

### Filters
- **Provider Filter**: Filter by PMS provider (All Providers / specific provider)
- **Report Selector**: Select specific report or view all reports combined

### Upload Section
- Expandable "Upload New PMS Report" section
- Provider selection dropdown
- PDF file uploader
- Process button to trigger parsing

## Data Flow

```
PDF Upload → Parser (provider-specific) → Data Extraction → Validation → Database Storage → Visualization
```

### Parsing Process
1. User uploads PDF and selects provider
2. System instantiates appropriate parser class
3. Parser extracts:
   - Report date from PDF content
   - Holdings table data (merged cells handled)
4. Data validated against schema
5. Report metadata stored in `pms_reports` table
6. Holdings stored in `holdings` table with foreign key

### Database Schema

**pms_reports**
```sql
CREATE TABLE pms_reports (
    id INTEGER PRIMARY KEY,
    pms_provider TEXT NOT NULL,
    report_date DATE NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pms_provider, report_date, file_hash)
);
```

**holdings**
```sql
CREATE TABLE holdings (
    id INTEGER PRIMARY KEY,
    report_id INTEGER NOT NULL,
    stock_name TEXT NOT NULL,
    isin TEXT,
    quantity REAL,
    market_value REAL,
    portfolio_percentage REAL,
    cost_price REAL,
    current_price REAL,
    gain_loss REAL,
    gain_loss_percentage REAL,
    sector TEXT,
    other_fields TEXT,
    FOREIGN KEY (report_id) REFERENCES pms_reports(id) ON DELETE CASCADE
);
```

## Provider Support

### Sameeksha PMS
- **Report Format**: PDF with table format
- **Section Marker**: "(iii) Holding Report as of DD/MM/YYYY"
- **Table Structure**: Security Name | Qty | Avg Cost | Market Rate | Total Cost | Market Value | % Portfolio
- **Asset Categories**: Shares, Mutual Funds, Futures, Cash/Bank, Other Assets
- **Date Format**: DD/MM/YYYY
- **Special Handling**: Merged table cells, multi-line stock names

## UI/UX Design

### Color Scheme
- Light theme matching main app
- Blue primary color (#1a73e8)
- Green for positive returns (#4caf50)
- Red for negative returns (#f44336)

### Layout
- **3 Tabs**: Overview | Analysis | Reports
- **Responsive**: Works on desktop and mobile
- **Metrics Cards**: Gradient backgrounds with borders
- **Charts**: White backgrounds with light gray gridlines
- **Tables**: Clean dataframe styling with formatting

### Formatting
- Currency: Indian format with Lakhs/Crores
  - ₹50,000 for values < 1L
  - ₹5.00 L for 5 lakhs
  - ₹5.00 Cr for 5 crores
- Percentages: 2 decimal places with + prefix for gains
- Quantities: Comma-separated (e.g., 1,000)

## Error Handling

### Upload Errors
- Invalid PDF format → Error message
- Parsing failure → Detailed error message
- Duplicate report → Warning message
- Missing data → Info message

### Display Errors
- No reports → Welcome message with instructions
- No holdings → Info message
- Empty filters → Appropriate messaging

## Future Enhancements

### Planned Features
1. **More Providers**: Support for other PMS providers
2. **Historical Comparison**: Compare holdings across multiple report dates
3. **Performance Analytics**: Calculate portfolio XIRR, TWR
4. **Alerts**: Set alerts for portfolio changes
5. **Export**: Export holdings data to Excel/CSV
6. **Benchmarking**: Compare against indices
7. **Sector Analysis**: Detailed sector allocation charts

### Technical Improvements
1. **Async Processing**: Background PDF parsing for large files
2. **Caching**: Cache parsed data for faster loads
3. **Batch Upload**: Upload multiple reports at once
4. **OCR Support**: Handle scanned PDFs
5. **Auto-refresh**: Fetch latest NAVs for holdings

## Testing

### Test Cases
1. ✅ Upload valid Sameeksha report
2. ✅ Detect duplicate report
3. ✅ Parse merged table cells
4. ✅ Extract date from various formats
5. ✅ Handle empty holdings
6. ✅ Calculate returns correctly
7. ✅ Delete report and cascade holdings
8. ✅ Filter by provider
9. ✅ Filter by report date
10. ✅ Display charts with valid data

### Sample Data
- Test report: `pms/reports/sameeksha_rt_report.pdf`
- Report date: 30-Nov-2025
- Holdings: 8 (Shares, Mutual Funds, Futures, Cash, Other Assets)
- Total value: ₹5.00 Cr

## Dependencies

Module-specific:
- `pdfplumber>=0.10.0` - PDF parsing
- `python-dateutil>=2.8.2` - Date parsing

Shared:
- `streamlit>=1.29.0` - UI framework
- `pandas>=2.0.0` - Data manipulation
- `plotly>=5.18.0` - Visualizations

## File Locations

- **Module**: `/pms/`
- **Tab**: `/tabs/pms.py`
- **Database**: `/pms/pms_data.db`
- **Reports**: `/pms/reports/`
- **Spec**: `/specs/pms_spec.md`

