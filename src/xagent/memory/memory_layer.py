"""Memory Layer - Multi-tier memory system for X-Agent."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
import json
import asyncio

import redis.asyncio as aioredis
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
import chromadb
from chromadb.config import Settings as ChromaSettings

from xagent.config import settings
from xagent.utils.logging import get_logger

logger = get_logger(__name__)

Base = declarative_base()


class MemoryEntry(Base):
    """Memory entry model for PostgreSQL."""
    
    __tablename__ = "memory_entries"
    
    id = Column(String, primary_key=True)
    content = Column(Text, nullable=False)
    memory_type = Column(String, nullable=False)  # short, medium, long
    entry_metadata = Column(JSONB, default={})  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class MemoryStore(ABC):
    """Abstract base class for memory stores."""
    
    @abstractmethod
    async def save(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Save a value to memory."""
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from memory."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a value from memory."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close memory store connection."""
        pass


class ShortTermMemory(MemoryStore):
    """
    Short-term memory using Redis.
    Fast access, TTL-based, for current context and active tasks.
    """
    
    def __init__(self) -> None:
        """Initialize short-term memory."""
        self.redis: Optional[aioredis.Redis] = None
        
    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self.redis.ping()
            logger.info("Connected to Redis for short-term memory")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def save(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Save to short-term memory.
        
        Args:
            key: Memory key
            value: Value to store
            ttl: Time to live in seconds (default: 3600 = 1 hour)
        """
        if not self.redis:
            await self.connect()
            
        try:
            serialized = json.dumps(value)
            if ttl:
                await self.redis.setex(f"stm:{key}", ttl, serialized)
            else:
                await self.redis.setex(f"stm:{key}", 3600, serialized)
            logger.debug(f"Saved to short-term memory: {key}")
        except Exception as e:
            logger.error(f"Failed to save to short-term memory: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from short-term memory."""
        if not self.redis:
            await self.connect()
            
        try:
            value = await self.redis.get(f"stm:{key}")
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get from short-term memory: {e}")
            return None
    
    async def delete(self, key: str) -> None:
        """Delete from short-term memory."""
        if not self.redis:
            await self.connect()
            
        try:
            await self.redis.delete(f"stm:{key}")
        except Exception as e:
            logger.error(f"Failed to delete from short-term memory: {e}")
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()


class MediumTermMemory(MemoryStore):
    """
    Medium-term memory using PostgreSQL.
    Persistent storage for project history and intermediate states.
    """
    
    def __init__(self) -> None:
        """Initialize medium-term memory."""
        self.engine = None
        self.session_maker = None
        
    async def connect(self) -> None:
        """Connect to PostgreSQL."""
        try:
            # Use async engine with proper URL parsing
            from urllib.parse import urlparse, urlunparse
            
            parsed = urlparse(self.engine.config.postgres_url if hasattr(self, 'engine') and hasattr(self.engine, 'config') else settings.postgres_url)
            # Replace scheme for asyncpg
            async_url = urlunparse((
                'postgresql+asyncpg',
                parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            
            self.engine = create_async_engine(async_url, echo=False)
            self.session_maker = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                
            logger.info("Connected to PostgreSQL for medium-term memory")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def save(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Save to medium-term memory.
        
        Args:
            key: Memory key
            value: Value to store
            ttl: Time to live in seconds (optional)
        """
        if not self.session_maker:
            await self.connect()
            
        try:
            async with self.session_maker() as session:
                expires_at = None
                if ttl:
                    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
                
                entry = MemoryEntry(
                    id=key,
                    content=json.dumps(value) if not isinstance(value, str) else value,
                    memory_type="medium",
                    expires_at=expires_at,
                )
                
                session.add(entry)
                await session.commit()
                
            logger.debug(f"Saved to medium-term memory: {key}")
        except Exception as e:
            logger.error(f"Failed to save to medium-term memory: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from medium-term memory."""
        if not self.session_maker:
            await self.connect()
            
        try:
            async with self.session_maker() as session:
                result = await session.get(MemoryEntry, key)
                if result and (not result.expires_at or result.expires_at > datetime.now(timezone.utc)):
                    try:
                        return json.loads(result.content)
                    except json.JSONDecodeError:
                        return result.content
                return None
        except Exception as e:
            logger.error(f"Failed to get from medium-term memory: {e}")
            return None
    
    async def delete(self, key: str) -> None:
        """Delete from medium-term memory."""
        if not self.session_maker:
            await self.connect()
            
        try:
            async with self.session_maker() as session:
                entry = await session.get(MemoryEntry, key)
                if entry:
                    await session.delete(entry)
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to delete from medium-term memory: {e}")
    
    async def close(self) -> None:
        """Close PostgreSQL connection."""
        if self.engine:
            await self.engine.dispose()


class LongTermMemory(MemoryStore):
    """
    Long-term memory using ChromaDB vector store.
    Semantic search for learned patterns and knowledge.
    """
    
    def __init__(self) -> None:
        """Initialize long-term memory."""
        self.client = None
        self.collection = None
        
    async def connect(self) -> None:
        """Connect to ChromaDB."""
        try:
            self.client = chromadb.Client(
                ChromaSettings(
                    persist_directory=settings.chroma_persist_directory,
                    anonymized_telemetry=False,
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="xagent_longterm_memory",
                metadata={"description": "X-Agent long-term semantic memory"},
            )
            
            logger.info("Connected to ChromaDB for long-term memory")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise
    
    async def save(
        self, key: str, value: Any, ttl: Optional[int] = None, embedding: Optional[List[float]] = None
    ) -> None:
        """
        Save to long-term memory with embedding.
        
        Args:
            key: Memory key
            value: Value to store
            ttl: Not used for long-term memory
            embedding: Optional pre-computed embedding
        """
        if not self.collection:
            await self.connect()
            
        try:
            content = json.dumps(value) if not isinstance(value, str) else value
            
            # Add to collection
            self.collection.add(
                ids=[key],
                documents=[content],
                embeddings=[embedding] if embedding else None,
                metadatas=[{"created_at": datetime.now(timezone.utc).isoformat()}],
            )
            
            logger.debug(f"Saved to long-term memory: {key}")
        except Exception as e:
            logger.error(f"Failed to save to long-term memory: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from long-term memory by ID."""
        if not self.collection:
            await self.connect()
            
        try:
            result = self.collection.get(ids=[key])
            if result and result["documents"]:
                content = result["documents"][0]
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return content
            return None
        except Exception as e:
            logger.error(f"Failed to get from long-term memory: {e}")
            return None
    
    async def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Semantic search in long-term memory.
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of matching memories
        """
        if not self.collection:
            await self.connect()
            
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
            )
            
            memories = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    try:
                        content = json.loads(doc)
                    except json.JSONDecodeError:
                        content = doc
                        
                    memories.append({
                        "id": results["ids"][0][i] if results["ids"] else None,
                        "content": content,
                        "distance": results["distances"][0][i] if results.get("distances") else None,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    })
                    
            return memories
        except Exception as e:
            logger.error(f"Failed to search long-term memory: {e}")
            return []
    
    async def delete(self, key: str) -> None:
        """Delete from long-term memory."""
        if not self.collection:
            await self.connect()
            
        try:
            self.collection.delete(ids=[key])
        except Exception as e:
            logger.error(f"Failed to delete from long-term memory: {e}")
    
    async def close(self) -> None:
        """Close ChromaDB connection."""
        # ChromaDB client doesn't need explicit closing
        pass


class MemoryLayer:
    """
    Multi-tier memory system combining short, medium, and long-term memory.
    """
    
    def __init__(self) -> None:
        """Initialize memory layer."""
        self.short_term = ShortTermMemory()
        self.medium_term = MediumTermMemory()
        self.long_term = LongTermMemory()
        
    async def initialize(self) -> None:
        """Initialize all memory stores."""
        await self.short_term.connect()
        await self.medium_term.connect()
        await self.long_term.connect()
        logger.info("Memory layer initialized")
    
    async def save_short_term(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Save to short-term memory (RAM)."""
        await self.short_term.save(key, value, ttl)
    
    async def save_medium_term(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Save to medium-term memory (Buffer)."""
        await self.medium_term.save(key, value, ttl)
    
    async def save_long_term(
        self, key: str, value: Any, embedding: Optional[List[float]] = None
    ) -> None:
        """Save to long-term memory (Knowledge Store)."""
        await self.long_term.save(key, value, embedding=embedding)
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from memory (checks all tiers).
        
        Args:
            key: Memory key
            
        Returns:
            Value if found, None otherwise
        """
        # Try short-term first (fastest)
        value = await self.short_term.get(key)
        if value is not None:
            return value
        
        # Try medium-term
        value = await self.medium_term.get(key)
        if value is not None:
            # Cache in short-term for future access
            await self.short_term.save(key, value, ttl=300)
            return value
        
        # Try long-term
        value = await self.long_term.get(key)
        if value is not None:
            # Cache in short-term for future access
            await self.short_term.save(key, value, ttl=300)
            return value
        
        return None
    
    async def search_knowledge(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search long-term knowledge base."""
        return await self.long_term.search(query, n_results)
    
    async def close(self) -> None:
        """Close all memory stores."""
        await self.short_term.close()
        await self.medium_term.close()
        await self.long_term.close()
        logger.info("Memory layer closed")
