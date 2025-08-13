"""
Ledger Manager for GlyphMind AI
Maintains audit trails, transaction logs, and system accountability
"""
import asyncio
import aiosqlite
import json
import time
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from logs.logger import log_info, log_error, log_warning
from config.config_manager import get_config

class TransactionType(Enum):
    """Types of transactions to log"""
    USER_QUERY = "user_query"
    AI_RESPONSE = "ai_response"
    WEB_SEARCH = "web_search"
    KNOWLEDGE_STORE = "knowledge_store"
    EVOLUTION_LEARN = "evolution_learn"
    API_CALL = "api_call"
    SYSTEM_EVENT = "system_event"
    ERROR_EVENT = "error_event"

class TransactionStatus(Enum):
    """Transaction status"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"

@dataclass
class LedgerEntry:
    """Ledger entry data structure"""
    id: Optional[str] = None
    transaction_type: TransactionType = TransactionType.SYSTEM_EVENT
    status: TransactionStatus = TransactionStatus.PENDING
    timestamp: datetime = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    operation: str = ""
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0
    cost: float = 0.0  # For API costs
    metadata: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.id is None:
            self.id = f"{self.transaction_type.value}_{int(time.time() * 1000000)}"

class LedgerManager:
    """Main ledger management system"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use data directory for persistent storage
            data_dir = os.environ.get("DATA_DIR", "data")
            db_path = os.path.join(data_dir, "ledger.sqlite")
        
        self.db_path = Path(db_path)
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            # Fallback to current directory
            self.db_path = Path("ledger.sqlite")
        
    async def initialize(self):
        """Initialize ledger database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await self._create_tables(db)
                await self._create_indexes(db)
                await db.commit()
            
            log_info(f"Ledger manager initialized: {self.db_path}")
            return True
        except Exception as e:
            log_error("Failed to initialize ledger manager", e)
            return False
            
    async def _create_tables(self, db: aiosqlite.Connection):
        """Create ledger tables"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ledger_entries (
                id TEXT PRIMARY KEY,
                transaction_type TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                session_id TEXT,
                request_id TEXT,
                operation TEXT,
                input_data TEXT, -- JSON
                output_data TEXT, -- JSON
                execution_time REAL DEFAULT 0.0,
                cost REAL DEFAULT 0.0,
                metadata TEXT, -- JSON
                error_details TEXT
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ledger_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL, -- YYYY-MM-DD
                transaction_type TEXT NOT NULL,
                total_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                total_execution_time REAL DEFAULT 0.0,
                total_cost REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, transaction_type)
            )
        """)
        
    async def _create_indexes(self, db: aiosqlite.Connection):
        """Create database indexes"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_transaction_type ON ledger_entries (transaction_type)",
            "CREATE INDEX IF NOT EXISTS idx_status ON ledger_entries (status)",
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON ledger_entries (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_user_id ON ledger_entries (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_session_id ON ledger_entries (session_id)",
            "CREATE INDEX IF NOT EXISTS idx_request_id ON ledger_entries (request_id)",
        ]
        
        for index_sql in indexes:
            await db.execute(index_sql)
            
    async def log_transaction(self, entry: LedgerEntry) -> bool:
        """Log a transaction to the ledger"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO ledger_entries (
                        id, transaction_type, status, timestamp, user_id, session_id,
                        request_id, operation, input_data, output_data, execution_time,
                        cost, metadata, error_details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.id,
                    entry.transaction_type.value,
                    entry.status.value,
                    entry.timestamp,
                    entry.user_id,
                    entry.session_id,
                    entry.request_id,
                    entry.operation,
                    json.dumps(entry.input_data) if entry.input_data else None,
                    json.dumps(entry.output_data) if entry.output_data else None,
                    entry.execution_time,
                    entry.cost,
                    json.dumps(entry.metadata) if entry.metadata else None,
                    entry.error_details
                ))
                
                await db.commit()
                
            # Update daily summary
            await self._update_daily_summary(entry)
            
            return True
            
        except Exception as e:
            log_error("Failed to log transaction to ledger", e, {"entry_id": entry.id})
            return False
            
    async def _update_daily_summary(self, entry: LedgerEntry):
        """Update daily summary statistics"""
        try:
            date_str = entry.timestamp.strftime("%Y-%m-%d")
            
            async with aiosqlite.connect(self.db_path) as db:
                # Check if summary exists
                async with db.execute("""
                    SELECT total_count, success_count, failed_count, 
                           total_execution_time, total_cost
                    FROM ledger_summary 
                    WHERE date = ? AND transaction_type = ?
                """, (date_str, entry.transaction_type.value)) as cursor:
                    existing = await cursor.fetchone()
                
                if existing:
                    # Update existing summary
                    total_count, success_count, failed_count, total_time, total_cost = existing
                    
                    total_count += 1
                    total_time += entry.execution_time
                    total_cost += entry.cost
                    
                    if entry.status == TransactionStatus.SUCCESS:
                        success_count += 1
                    elif entry.status == TransactionStatus.FAILED:
                        failed_count += 1
                        
                    await db.execute("""
                        UPDATE ledger_summary SET
                            total_count = ?, success_count = ?, failed_count = ?,
                            total_execution_time = ?, total_cost = ?
                        WHERE date = ? AND transaction_type = ?
                    """, (total_count, success_count, failed_count, total_time, 
                          total_cost, date_str, entry.transaction_type.value))
                else:
                    # Create new summary
                    success_count = 1 if entry.status == TransactionStatus.SUCCESS else 0
                    failed_count = 1 if entry.status == TransactionStatus.FAILED else 0
                    
                    await db.execute("""
                        INSERT INTO ledger_summary (
                            date, transaction_type, total_count, success_count,
                            failed_count, total_execution_time, total_cost
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (date_str, entry.transaction_type.value, 1, success_count,
                          failed_count, entry.execution_time, entry.cost))
                
                await db.commit()
                
        except Exception as e:
            log_error("Failed to update daily summary", e)
            
    async def log_user_query(self, user_id: str, session_id: str, request_id: str,
                           query: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Log a user query"""
        entry = LedgerEntry(
            transaction_type=TransactionType.USER_QUERY,
            status=TransactionStatus.SUCCESS,
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            operation="user_query",
            input_data={"query": query},
            metadata=metadata
        )
        
        await self.log_transaction(entry)
        return entry.id
        
    async def log_ai_response(self, user_id: str, session_id: str, request_id: str,
                            query: str, response: str, model_used: str, 
                            execution_time: float, confidence: float,
                            metadata: Optional[Dict[str, Any]] = None) -> str:
        """Log an AI response"""
        entry = LedgerEntry(
            transaction_type=TransactionType.AI_RESPONSE,
            status=TransactionStatus.SUCCESS,
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            operation="ai_response",
            input_data={"query": query},
            output_data={
                "response": response,
                "model_used": model_used,
                "confidence": confidence
            },
            execution_time=execution_time,
            metadata=metadata
        )
        
        await self.log_transaction(entry)
        return entry.id
        
    async def log_web_search(self, user_id: str, session_id: str, request_id: str,
                           query: str, sources: List[str], results_count: int,
                           execution_time: float, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Log a web search operation"""
        entry = LedgerEntry(
            transaction_type=TransactionType.WEB_SEARCH,
            status=TransactionStatus.SUCCESS,
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            operation="web_search",
            input_data={"query": query, "sources": sources},
            output_data={"results_count": results_count},
            execution_time=execution_time,
            metadata=metadata
        )
        
        await self.log_transaction(entry)
        return entry.id
        
    async def log_api_call(self, service: str, endpoint: str, cost: float,
                         execution_time: float, status: TransactionStatus,
                         request_data: Optional[Dict[str, Any]] = None,
                         response_data: Optional[Dict[str, Any]] = None,
                         error_details: Optional[str] = None) -> str:
        """Log an external API call"""
        entry = LedgerEntry(
            transaction_type=TransactionType.API_CALL,
            status=status,
            operation=f"{service}_{endpoint}",
            input_data=request_data,
            output_data=response_data,
            execution_time=execution_time,
            cost=cost,
            error_details=error_details,
            metadata={"service": service, "endpoint": endpoint}
        )
        
        await self.log_transaction(entry)
        return entry.id
        
    async def log_system_event(self, event: str, details: Optional[Dict[str, Any]] = None) -> str:
        """Log a system event"""
        entry = LedgerEntry(
            transaction_type=TransactionType.SYSTEM_EVENT,
            status=TransactionStatus.SUCCESS,
            operation=event,
            metadata=details
        )
        
        await self.log_transaction(entry)
        return entry.id
        
    async def log_error(self, error_type: str, error_message: str, 
                       context: Optional[Dict[str, Any]] = None) -> str:
        """Log an error event"""
        entry = LedgerEntry(
            transaction_type=TransactionType.ERROR_EVENT,
            status=TransactionStatus.FAILED,
            operation=error_type,
            error_details=error_message,
            metadata=context
        )
        
        await self.log_transaction(entry)
        return entry.id
        
    async def get_transaction_history(self, user_id: Optional[str] = None,
                                    session_id: Optional[str] = None,
                                    transaction_type: Optional[TransactionType] = None,
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None,
                                    limit: int = 100) -> List[Dict[str, Any]]:
        """Get transaction history with filters"""
        try:
            conditions = []
            params = []
            
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
                
            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)
                
            if transaction_type:
                conditions.append("transaction_type = ?")
                params.append(transaction_type.value)
                
            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date)
                
            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date)
                
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            sql = f"""
                SELECT * FROM ledger_entries 
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            """
            params.append(limit)
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()
                    
                    # Get column names
                    columns = [description[0] for description in cursor.description]
                    
                    # Convert to list of dictionaries
                    results = []
                    for row in rows:
                        entry_dict = dict(zip(columns, row))
                        
                        # Parse JSON fields
                        for json_field in ['input_data', 'output_data', 'metadata']:
                            if entry_dict[json_field]:
                                try:
                                    entry_dict[json_field] = json.loads(entry_dict[json_field])
                                except json.JSONDecodeError:
                                    entry_dict[json_field] = None
                                    
                        results.append(entry_dict)
                        
                    return results
                    
        except Exception as e:
            log_error("Failed to get transaction history", e)
            return []
            
    async def get_daily_summary(self, start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get daily summary statistics"""
        try:
            conditions = []
            params = []
            
            if start_date:
                conditions.append("date >= ?")
                params.append(start_date.strftime("%Y-%m-%d"))
                
            if end_date:
                conditions.append("date <= ?")
                params.append(end_date.strftime("%Y-%m-%d"))
                
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            sql = f"""
                SELECT * FROM ledger_summary
                WHERE {where_clause}
                ORDER BY date DESC, transaction_type
            """
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    
                    return [dict(zip(columns, row)) for row in rows]
                    
        except Exception as e:
            log_error("Failed to get daily summary", e)
            return []
            
    async def get_ledger_statistics(self) -> Dict[str, Any]:
        """Get comprehensive ledger statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}
                
                # Total transactions
                async with db.execute("SELECT COUNT(*) FROM ledger_entries") as cursor:
                    stats["total_transactions"] = (await cursor.fetchone())[0]
                    
                # Transactions by type
                async with db.execute("""
                    SELECT transaction_type, COUNT(*) 
                    FROM ledger_entries 
                    GROUP BY transaction_type
                """) as cursor:
                    stats["transactions_by_type"] = dict(await cursor.fetchall())
                    
                # Transactions by status
                async with db.execute("""
                    SELECT status, COUNT(*) 
                    FROM ledger_entries 
                    GROUP BY status
                """) as cursor:
                    stats["transactions_by_status"] = dict(await cursor.fetchall())
                    
                # Recent activity (last 24 hours)
                yesterday = datetime.now() - timedelta(hours=24)
                async with db.execute("""
                    SELECT COUNT(*) FROM ledger_entries 
                    WHERE timestamp > ?
                """, (yesterday,)) as cursor:
                    stats["recent_transactions_24h"] = (await cursor.fetchone())[0]
                    
                # Total costs
                async with db.execute("SELECT SUM(cost) FROM ledger_entries") as cursor:
                    total_cost = (await cursor.fetchone())[0]
                    stats["total_cost"] = total_cost or 0.0
                    
                # Average execution time
                async with db.execute("""
                    SELECT AVG(execution_time) FROM ledger_entries 
                    WHERE execution_time > 0
                """) as cursor:
                    avg_time = (await cursor.fetchone())[0]
                    stats["average_execution_time"] = avg_time or 0.0
                    
                return stats
                
        except Exception as e:
            log_error("Failed to get ledger statistics", e)
            return {}

# Global ledger manager instance
ledger_manager = LedgerManager()

async def log_transaction(entry: LedgerEntry) -> bool:
    """Convenience function to log a transaction"""
    return await ledger_manager.log_transaction(entry)
