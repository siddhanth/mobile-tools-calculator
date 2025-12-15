-- PMS Analyzer Database Schema

-- Table to store report metadata
CREATE TABLE IF NOT EXISTS pms_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pms_provider TEXT NOT NULL,
    report_date DATE NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT,  -- For duplicate detection
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pms_provider, report_date, file_hash)
);

-- Table to store individual holdings
CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    other_fields TEXT,  -- JSON for provider-specific fields
    FOREIGN KEY (report_id) REFERENCES pms_reports(id) ON DELETE CASCADE
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_holdings_report_id ON holdings(report_id);
CREATE INDEX IF NOT EXISTS idx_holdings_stock_name ON holdings(stock_name);
CREATE INDEX IF NOT EXISTS idx_pms_reports_provider ON pms_reports(pms_provider);
CREATE INDEX IF NOT EXISTS idx_pms_reports_date ON pms_reports(report_date);

