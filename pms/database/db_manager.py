"""
Database Manager for PMS Analyzer.
Handles all SQLite database operations for storing and retrieving PMS reports and holdings.
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for PMS reports and holdings."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file. Defaults to 'pms_data.db' in the project root.
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "pms_data.db"
        self.db_path = Path(db_path)
        self._connection: Optional[sqlite3.Connection] = None
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection
    
    def _initialize_database(self):
        """Initialize the database with schema."""
        schema_path = Path(__file__).parent / "schema.sql"
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            cursor.executescript(schema_sql)
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    @staticmethod
    def compute_file_hash(file_path: str) -> str:
        """Compute MD5 hash of a file for duplicate detection."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def insert_report(
        self,
        pms_provider: str,
        report_date: date,
        file_path: str,
        file_hash: str = None
    ) -> int:
        """
        Insert a new PMS report record.
        
        Args:
            pms_provider: Name of the PMS provider (e.g., 'sameeksha')
            report_date: Date of the report
            file_path: Path to the PDF file
            file_hash: Optional MD5 hash for duplicate detection
        
        Returns:
            The ID of the inserted report
        
        Raises:
            sqlite3.IntegrityError: If a duplicate report exists
        """
        if file_hash is None:
            file_hash = self.compute_file_hash(file_path)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO pms_reports (pms_provider, report_date, file_path, file_hash)
                VALUES (?, ?, ?, ?)
            """, (pms_provider, report_date.isoformat(), file_path, file_hash))
            conn.commit()
            report_id = cursor.lastrowid
            logger.info(f"Inserted report ID {report_id} for {pms_provider} dated {report_date}")
            return report_id
        except sqlite3.IntegrityError as e:
            logger.warning(f"Duplicate report detected: {e}")
            raise
    
    def insert_holdings(self, report_id: int, holdings: List[Dict[str, Any]]) -> int:
        """
        Insert multiple holdings for a report.
        
        Args:
            report_id: ID of the parent report
            holdings: List of holding dictionaries
        
        Returns:
            Number of holdings inserted
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        inserted_count = 0
        for holding in holdings:
            other_fields = holding.get('other_fields')
            if other_fields and isinstance(other_fields, dict):
                other_fields = json.dumps(other_fields)
            
            cursor.execute("""
                INSERT INTO holdings (
                    report_id, stock_name, isin, quantity, market_value,
                    portfolio_percentage, cost_price, current_price,
                    gain_loss, gain_loss_percentage, sector, other_fields
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_id,
                holding.get('stock_name'),
                holding.get('isin'),
                holding.get('quantity'),
                holding.get('market_value'),
                holding.get('portfolio_percentage'),
                holding.get('cost_price'),
                holding.get('current_price'),
                holding.get('gain_loss'),
                holding.get('gain_loss_percentage'),
                holding.get('sector'),
                other_fields
            ))
            inserted_count += 1
        
        conn.commit()
        logger.info(f"Inserted {inserted_count} holdings for report ID {report_id}")
        return inserted_count
    
    def get_reports(
        self,
        pms_provider: str = None,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve reports with optional filtering.
        
        Args:
            pms_provider: Filter by provider name
            start_date: Filter reports from this date
            end_date: Filter reports until this date
        
        Returns:
            List of report dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM pms_reports WHERE 1=1"
        params = []
        
        if pms_provider:
            query += " AND pms_provider = ?"
            params.append(pms_provider)
        if start_date:
            query += " AND report_date >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND report_date <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY report_date DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_holdings(
        self,
        report_id: int = None,
        stock_name: str = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve holdings with optional filtering.
        
        Args:
            report_id: Filter by report ID
            stock_name: Filter by stock name (partial match)
        
        Returns:
            List of holding dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT h.*, r.pms_provider, r.report_date 
            FROM holdings h
            JOIN pms_reports r ON h.report_id = r.id
            WHERE 1=1
        """
        params = []
        
        if report_id:
            query += " AND h.report_id = ?"
            params.append(report_id)
        if stock_name:
            query += " AND h.stock_name LIKE ?"
            params.append(f"%{stock_name}%")
        
        query += " ORDER BY h.market_value DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            holding = dict(row)
            # Parse JSON other_fields if present
            if holding.get('other_fields'):
                try:
                    holding['other_fields'] = json.loads(holding['other_fields'])
                except json.JSONDecodeError:
                    pass
            results.append(holding)
        
        return results
    
    def get_report_by_id(self, report_id: int) -> Optional[Dict[str, Any]]:
        """Get a single report by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM pms_reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()
        
        return dict(row) if row else None
    
    def delete_report(self, report_id: int) -> bool:
        """
        Delete a report and its associated holdings.
        
        Args:
            report_id: ID of the report to delete
        
        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM pms_reports WHERE id = ?", (report_id,))
        conn.commit()
        
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Deleted report ID {report_id}")
        return deleted
    
    def report_exists(self, pms_provider: str, report_date: date, file_hash: str) -> bool:
        """Check if a report already exists (for duplicate detection)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 1 FROM pms_reports 
            WHERE pms_provider = ? AND report_date = ? AND file_hash = ?
        """, (pms_provider, report_date.isoformat(), file_hash))
        
        return cursor.fetchone() is not None
    
    def get_portfolio_summary(self, report_id: int) -> Dict[str, Any]:
        """
        Get a summary of a portfolio from a specific report.
        
        Args:
            report_id: ID of the report
        
        Returns:
            Dictionary with portfolio statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_stocks,
                SUM(market_value) as total_value,
                SUM(gain_loss) as total_gain_loss,
                AVG(gain_loss_percentage) as avg_gain_loss_pct
            FROM holdings
            WHERE report_id = ?
        """, (report_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else {}

