"""
Knowledge Base Manager for GlyphMind AI
Handles persistent storage and retrieval of learned information
"""
import sqlite3
import asyncio
import aiosqlite
import json
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import pickle
import numpy as np
from abc import ABC, abstractmethod

from logs.logger import log_info, log_error, log_warning
from config.config_manager import get_config

@dataclass
class KnowledgeEntry:
    """Knowledge entry data structure"""
    id: Optional[str] = None
    content: str = ""
    title: str = ""
    source: str = ""
    url: Optional[str] = None
    category: str = "general"
    tags: List[str] = None
    confidence: float = 1.0
    relevance_score: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.id is None:
            self.id = self._generate_id()
            
    def _generate_id(self) -> str:
        """Generate unique ID for knowledge entry"""
        content_hash = hashlib.md5(
            f"{self.content}{self.source}{self.url}".encode()
        ).hexdigest()
        return f"kb_{content_hash[:16]}"

@dataclass
class SearchQuery:
    """Knowledge base search query"""
    query: str
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    min_confidence: float = 0.0
    max_results: int = 10
    semantic_search: bool = True

class BaseKnowledgeStore(ABC):
    """Abstract base class for knowledge storage backends"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the knowledge store"""
        pass
        
    @abstractmethod
    async def store_knowledge(self, entry: KnowledgeEntry) -> bool:
        """Store a knowledge entry"""
        pass
        
    @abstractmethod
    async def search_knowledge(self, query: SearchQuery) -> List[KnowledgeEntry]:
        """Search for knowledge entries"""
        pass
        
    @abstractmethod
    async def get_knowledge(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get a specific knowledge entry"""
        pass
        
    @abstractmethod
    async def update_knowledge(self, entry: KnowledgeEntry) -> bool:
        """Update a knowledge entry"""
        pass
        
    @abstractmethod
    async def delete_knowledge(self, entry_id: str) -> bool:
        """Delete a knowledge entry"""
        pass

class SQLiteKnowledgeStore(BaseKnowledgeStore):
    """SQLite-based knowledge storage"""
    
    def __init__(self, db_path: str = "knowledge_base/kb.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
    async def initialize(self) -> bool:
        """Initialize SQLite database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await self._create_tables(db)
                await self._create_indexes(db)
                await db.commit()
            
            log_info(f"SQLite knowledge store initialized: {self.db_path}")
            return True
        except Exception as e:
            log_error("Failed to initialize SQLite knowledge store", e)
            return False
            
    async def _create_tables(self, db: aiosqlite.Connection):
        """Create database tables"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_entries (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                title TEXT,
                source TEXT,
                url TEXT,
                category TEXT DEFAULT 'general',
                tags TEXT, -- JSON array
                confidence REAL DEFAULT 1.0,
                relevance_score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT -- JSON object
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_vectors (
                entry_id TEXT PRIMARY KEY,
                vector BLOB, -- Pickled numpy array
                FOREIGN KEY (entry_id) REFERENCES knowledge_entries (id)
                    ON DELETE CASCADE
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_entries INTEGER DEFAULT 0,
                last_cleanup TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
    async def _create_indexes(self, db: aiosqlite.Connection):
        """Create database indexes for performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_category ON knowledge_entries (category)",
            "CREATE INDEX IF NOT EXISTS idx_source ON knowledge_entries (source)",
            "CREATE INDEX IF NOT EXISTS idx_created_at ON knowledge_entries (created_at)",
            "CREATE INDEX IF NOT EXISTS idx_confidence ON knowledge_entries (confidence)",
            "CREATE INDEX IF NOT EXISTS idx_relevance ON knowledge_entries (relevance_score)",
        ]
        
        for index_sql in indexes:
            await db.execute(index_sql)
            
    async def store_knowledge(self, entry: KnowledgeEntry) -> bool:
        """Store knowledge entry in SQLite"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Check if entry already exists
                existing = await self.get_knowledge(entry.id)
                
                if existing:
                    # Update existing entry
                    entry.updated_at = datetime.now()
                    return await self._update_entry(db, entry)
                else:
                    # Insert new entry
                    return await self._insert_entry(db, entry)
                    
        except Exception as e:
            log_error("Failed to store knowledge entry", e, {"entry_id": entry.id})
            return False
            
    async def _insert_entry(self, db: aiosqlite.Connection, entry: KnowledgeEntry) -> bool:
        """Insert new knowledge entry"""
        await db.execute("""
            INSERT INTO knowledge_entries (
                id, content, title, source, url, category, tags, 
                confidence, relevance_score, created_at, updated_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id, entry.content, entry.title, entry.source, entry.url,
            entry.category, json.dumps(entry.tags), entry.confidence,
            entry.relevance_score, entry.created_at, entry.updated_at,
            json.dumps(entry.metadata) if entry.metadata else None
        ))
        
        await db.commit()
        return True
        
    async def _update_entry(self, db: aiosqlite.Connection, entry: KnowledgeEntry) -> bool:
        """Update existing knowledge entry"""
        await db.execute("""
            UPDATE knowledge_entries SET
                content = ?, title = ?, source = ?, url = ?, category = ?,
                tags = ?, confidence = ?, relevance_score = ?, updated_at = ?, metadata = ?
            WHERE id = ?
        """, (
            entry.content, entry.title, entry.source, entry.url, entry.category,
            json.dumps(entry.tags), entry.confidence, entry.relevance_score,
            entry.updated_at, json.dumps(entry.metadata) if entry.metadata else None,
            entry.id
        ))
        
        await db.commit()
        return True
        
    async def search_knowledge(self, query: SearchQuery) -> List[KnowledgeEntry]:
        """Search knowledge entries"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Build SQL query
                sql, params = self._build_search_query(query)
                
                async with db.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()
                    
                entries = []
                for row in rows:
                    entry = self._row_to_entry(row)
                    if entry:
                        entries.append(entry)
                        
                # Apply semantic search if enabled
                if query.semantic_search and entries:
                    entries = await self._apply_semantic_ranking(entries, query.query)
                    
                return entries[:query.max_results]
                
        except Exception as e:
            log_error("Failed to search knowledge base", e, {"query": query.query})
            return []
            
    def _build_search_query(self, query: SearchQuery) -> Tuple[str, List[Any]]:
        """Build SQL search query"""
        conditions = []
        params = []
        
        # Text search
        if query.query:
            conditions.append("(content LIKE ? OR title LIKE ?)")
            search_term = f"%{query.query}%"
            params.extend([search_term, search_term])
            
        # Category filter
        if query.categories:
            category_placeholders = ",".join(["?"] * len(query.categories))
            conditions.append(f"category IN ({category_placeholders})")
            params.extend(query.categories)
            
        # Source filter
        if query.sources:
            source_placeholders = ",".join(["?"] * len(query.sources))
            conditions.append(f"source IN ({source_placeholders})")
            params.extend(query.sources)
            
        # Confidence filter
        if query.min_confidence > 0:
            conditions.append("confidence >= ?")
            params.append(query.min_confidence)
            
        # Build final query
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"""
            SELECT id, content, title, source, url, category, tags,
                   confidence, relevance_score, created_at, updated_at, metadata
            FROM knowledge_entries 
            WHERE {where_clause}
            ORDER BY relevance_score DESC, confidence DESC, updated_at DESC
            LIMIT ?
        """
        params.append(query.max_results * 2)  # Get more for semantic ranking
        
        return sql, params
        
    def _row_to_entry(self, row) -> Optional[KnowledgeEntry]:
        """Convert database row to KnowledgeEntry"""
        try:
            return KnowledgeEntry(
                id=row[0],
                content=row[1] or "",
                title=row[2] or "",
                source=row[3] or "",
                url=row[4],
                category=row[5] or "general",
                tags=json.loads(row[6]) if row[6] else [],
                confidence=row[7] or 1.0,
                relevance_score=row[8] or 0.0,
                created_at=datetime.fromisoformat(row[9]) if row[9] else None,
                updated_at=datetime.fromisoformat(row[10]) if row[10] else None,
                metadata=json.loads(row[11]) if row[11] else None
            )
        except Exception as e:
            log_error("Failed to parse knowledge entry row", e)
            return None
            
    async def _apply_semantic_ranking(self, entries: List[KnowledgeEntry], 
                                    query: str) -> List[KnowledgeEntry]:
        """Apply semantic ranking to search results"""
        # Simple text similarity for now
        # TODO: Implement proper semantic embeddings
        
        def calculate_similarity(entry: KnowledgeEntry) -> float:
            query_words = set(query.lower().split())
            content_words = set((entry.content + " " + entry.title).lower().split())
            
            if not query_words or not content_words:
                return 0.0
                
            intersection = query_words.intersection(content_words)
            union = query_words.union(content_words)
            
            return len(intersection) / len(union) if union else 0.0
            
        # Calculate similarity scores
        for entry in entries:
            similarity = calculate_similarity(entry)
            entry.relevance_score = similarity * entry.confidence
            
        # Sort by relevance
        entries.sort(key=lambda x: x.relevance_score, reverse=True)
        return entries
        
    async def get_knowledge(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get specific knowledge entry"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, content, title, source, url, category, tags,
                           confidence, relevance_score, created_at, updated_at, metadata
                    FROM knowledge_entries WHERE id = ?
                """, (entry_id,)) as cursor:
                    row = await cursor.fetchone()
                    
                if row:
                    return self._row_to_entry(row)
                return None
                
        except Exception as e:
            log_error("Failed to get knowledge entry", e, {"entry_id": entry_id})
            return None
            
    async def update_knowledge(self, entry: KnowledgeEntry) -> bool:
        """Update knowledge entry"""
        entry.updated_at = datetime.now()
        return await self.store_knowledge(entry)
        
    async def delete_knowledge(self, entry_id: str) -> bool:
        """Delete knowledge entry"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM knowledge_entries WHERE id = ?", (entry_id,))
                await db.commit()
                return True
        except Exception as e:
            log_error("Failed to delete knowledge entry", e, {"entry_id": entry_id})
            return False
            
    async def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Total entries
                async with db.execute("SELECT COUNT(*) FROM knowledge_entries") as cursor:
                    total_entries = (await cursor.fetchone())[0]
                    
                # Entries by category
                async with db.execute("""
                    SELECT category, COUNT(*) FROM knowledge_entries 
                    GROUP BY category ORDER BY COUNT(*) DESC
                """) as cursor:
                    categories = dict(await cursor.fetchall())
                    
                # Entries by source
                async with db.execute("""
                    SELECT source, COUNT(*) FROM knowledge_entries 
                    GROUP BY source ORDER BY COUNT(*) DESC LIMIT 10
                """) as cursor:
                    sources = dict(await cursor.fetchall())
                    
                # Recent entries
                async with db.execute("""
                    SELECT COUNT(*) FROM knowledge_entries 
                    WHERE created_at > datetime('now', '-7 days')
                """) as cursor:
                    recent_entries = (await cursor.fetchone())[0]
                    
                return {
                    "total_entries": total_entries,
                    "categories": categories,
                    "top_sources": sources,
                    "recent_entries_7d": recent_entries,
                    "last_updated": datetime.now().isoformat()
                }
                
        except Exception as e:
            log_error("Failed to get knowledge base statistics", e)
            return {}

class KnowledgeManager:
    """Main knowledge management coordinator"""
    
    def __init__(self):
        self.store: Optional[BaseKnowledgeStore] = None
        
    async def initialize(self):
        """Initialize knowledge manager"""
        log_info("Initializing Knowledge Manager")
        
        config = get_config()
        db_path = config.database.knowledge_base_path
        
        self.store = SQLiteKnowledgeStore(db_path)
        success = await self.store.initialize()
        
        if success:
            log_info("Knowledge Manager initialized successfully")
        else:
            log_error("Failed to initialize Knowledge Manager")
            
        return success
        
    async def learn_from_web_results(self, query: str, results: List[Any]) -> int:
        """Learn from web search results"""
        if not self.store:
            return 0
            
        learned_count = 0
        
        for result in results:
            try:
                # Create knowledge entry from search result
                entry = KnowledgeEntry(
                    content=result.snippet,
                    title=result.title,
                    source=result.source,
                    url=result.url,
                    category=self._categorize_content(result.snippet, result.title),
                    tags=self._extract_tags(query, result.snippet),
                    confidence=getattr(result, 'relevance_score', 0.8),
                    metadata={
                        "original_query": query,
                        "search_timestamp": datetime.now().isoformat(),
                        "result_metadata": getattr(result, 'metadata', {})
                    }
                )
                
                if await self.store.store_knowledge(entry):
                    learned_count += 1
                    
            except Exception as e:
                log_error("Failed to learn from web result", e, {"result": str(result)[:200]})
                
        if learned_count > 0:
            log_info(f"Learned {learned_count} new knowledge entries from web search")
            
        return learned_count
        
    async def search(self, query: str, categories: Optional[List[str]] = None,
                    max_results: int = 10) -> List[KnowledgeEntry]:
        """Search knowledge base"""
        if not self.store:
            return []
            
        search_query = SearchQuery(
            query=query,
            categories=categories,
            max_results=max_results
        )
        
        return await self.store.search_knowledge(search_query)
        
    async def store_manual_knowledge(self, content: str, title: str, 
                                   category: str = "manual", 
                                   tags: Optional[List[str]] = None) -> bool:
        """Store manually provided knowledge"""
        if not self.store:
            return False
            
        entry = KnowledgeEntry(
            content=content,
            title=title,
            source="manual",
            category=category,
            tags=tags or [],
            confidence=1.0,
            metadata={
                "manual_entry": True,
                "created_by": "user",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return await self.store.store_knowledge(entry)
        
    def _categorize_content(self, content: str, title: str) -> str:
        """Automatically categorize content"""
        text = (content + " " + title).lower()
        
        categories = {
            "technology": ["code", "programming", "software", "tech", "computer", "algorithm"],
            "science": ["research", "study", "experiment", "theory", "scientific", "data"],
            "news": ["breaking", "report", "update", "announced", "today", "recent"],
            "education": ["learn", "tutorial", "guide", "how to", "explain", "course"],
            "business": ["company", "market", "business", "economy", "finance", "industry"],
            "health": ["health", "medical", "doctor", "treatment", "disease", "medicine"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
                
        return "general"
        
    def _extract_tags(self, query: str, content: str) -> List[str]:
        """Extract relevant tags from content"""
        text = (query + " " + content).lower()
        words = text.split()
        
        # Simple tag extraction - get meaningful words
        tags = []
        for word in words:
            if (len(word) > 3 and 
                word.isalpha() and 
                word not in ['this', 'that', 'with', 'from', 'they', 'have', 'been']):
                if word not in tags:
                    tags.append(word)
                    
        return tags[:10]  # Limit to 10 tags
        
    async def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        if not self.store:
            return {}
            
        return await self.store.get_statistics()

# Global knowledge manager instance
knowledge_manager = KnowledgeManager()

async def search_knowledge(query: str, categories: Optional[List[str]] = None,
                          max_results: int = 10) -> List[KnowledgeEntry]:
    """Convenience function for knowledge search"""
    return await knowledge_manager.search(query, categories, max_results)
