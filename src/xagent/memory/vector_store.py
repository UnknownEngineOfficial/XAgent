"""Vector Store - Enhanced ChromaDB integration with embeddings for semantic memory."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from xagent.config import settings
from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    """
    Enhanced vector store for semantic memory using ChromaDB.
    
    Features:
    - Automatic embedding generation (OpenAI or Sentence Transformers)
    - Semantic search with similarity scoring
    - Document metadata management
    - Collection management
    - Efficient batch operations
    """

    def __init__(
        self,
        collection_name: str = "xagent_semantic_memory",
        embedding_model: str = "all-MiniLM-L6-v2",
        use_openai: bool = False,
    ) -> None:
        """
        Initialize vector store.
        
        Args:
            collection_name: Name of the ChromaDB collection
            embedding_model: Model to use for embeddings
            use_openai: Whether to use OpenAI embeddings (requires API key)
        """
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.use_openai = use_openai
        self.client: Any = None
        self.collection: Any = None
        self.embedding_function: Any = None

    async def connect(self) -> None:
        """Connect to ChromaDB and set up embedding function."""
        try:
            # Initialize ChromaDB client
            self.client = chromadb.Client(
                ChromaSettings(
                    persist_directory=settings.chroma_persist_directory,
                    anonymized_telemetry=False,
                )
            )

            # Set up embedding function
            if self.use_openai and settings.openai_api_key:
                # Use OpenAI embeddings
                self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=settings.openai_api_key,
                    model_name="text-embedding-ada-002",
                )
                logger.info("Using OpenAI embeddings for vector store")
            else:
                # Use Sentence Transformers (local, no API key needed)
                self.embedding_function = (
                    embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name=self.embedding_model
                    )
                )
                logger.info(f"Using Sentence Transformers ({self.embedding_model}) for vector store")

            # Get or create collection with embedding function
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={
                    "description": "X-Agent semantic memory with vector embeddings",
                    "embedding_model": self.embedding_model,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            logger.info(f"Connected to ChromaDB collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise

    async def add_document(
        self,
        document: str,
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> str:
        """
        Add a document to the vector store.
        
        Args:
            document: Text content to store
            metadata: Optional metadata dictionary
            doc_id: Optional document ID (auto-generated if not provided)
            
        Returns:
            Document ID
        """
        if not self.collection:
            await self.connect()

        if not self.collection:
            raise RuntimeError("Vector store not connected")

        try:
            # Generate ID if not provided
            if not doc_id:
                doc_id = self._generate_id(document)

            # Prepare metadata
            meta = metadata or {}
            meta["created_at"] = datetime.now(timezone.utc).isoformat()
            meta["document_length"] = len(document)

            # Add to collection (embedding generated automatically)
            self.collection.add(
                ids=[doc_id],
                documents=[document],
                metadatas=[meta],
            )

            logger.debug(f"Added document to vector store: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            raise

    async def add_documents_batch(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        doc_ids: list[str] | None = None,
    ) -> list[str]:
        """
        Add multiple documents in batch.
        
        Args:
            documents: List of text documents
            metadatas: Optional list of metadata dictionaries
            doc_ids: Optional list of document IDs
            
        Returns:
            List of document IDs
        """
        if not self.collection:
            await self.connect()

        if not self.collection:
            raise RuntimeError("Vector store not connected")

        try:
            # Generate IDs if not provided
            if not doc_ids:
                doc_ids = [self._generate_id(doc) for doc in documents]

            # Prepare metadatas
            if not metadatas:
                metadatas = [{} for _ in documents]

            # Add timestamps and lengths
            now = datetime.now(timezone.utc).isoformat()
            for i, meta in enumerate(metadatas):
                meta["created_at"] = now
                meta["document_length"] = len(documents[i])

            # Batch add to collection
            self.collection.add(
                ids=doc_ids,
                documents=documents,
                metadatas=metadatas,
            )

            logger.info(f"Added {len(documents)} documents to vector store")
            return doc_ids
        except Exception as e:
            logger.error(f"Failed to add documents batch: {e}")
            raise

    async def search(
        self,
        query: str,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
        include_distances: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Semantic search for similar documents.
        
        Args:
            query: Search query text
            n_results: Number of results to return
            where: Optional metadata filter
            include_distances: Whether to include similarity distances
            
        Returns:
            List of matching documents with metadata
        """
        if not self.collection:
            await self.connect()

        if not self.collection:
            raise RuntimeError("Vector store not connected")

        try:
            # Query collection
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"] if include_distances else ["documents", "metadatas"],
            )

            # Format results
            documents = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    result = {
                        "id": results["ids"][0][i] if results["ids"] else None,
                        "document": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    }
                    
                    if include_distances and results.get("distances"):
                        result["distance"] = results["distances"][0][i]
                        # Convert distance to similarity score (0-1, higher is better)
                        result["similarity"] = 1 / (1 + results["distances"][0][i])

                    documents.append(result)

            logger.debug(f"Search for '{query[:50]}...' returned {len(documents)} results")
            return documents
        except Exception as e:
            logger.error(f"Failed to search vector store: {e}")
            return []

    async def get_document(self, doc_id: str) -> dict[str, Any] | None:
        """
        Get a specific document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document with metadata or None if not found
        """
        if not self.collection:
            await self.connect()

        if not self.collection:
            raise RuntimeError("Vector store not connected")

        try:
            result = self.collection.get(ids=[doc_id], include=["documents", "metadatas"])
            
            if result and result["documents"]:
                return {
                    "id": doc_id,
                    "document": result["documents"][0],
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None

    async def update_document(
        self,
        doc_id: str,
        document: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Update a document's content or metadata.
        
        Args:
            doc_id: Document ID
            document: New document content (optional)
            metadata: New metadata (optional, merged with existing)
            
        Returns:
            True if successful
        """
        if not self.collection:
            await self.connect()

        if not self.collection:
            raise RuntimeError("Vector store not connected")

        try:
            # Get existing document if we need to update metadata only
            if not document and metadata:
                existing = await self.get_document(doc_id)
                if not existing:
                    return False
                document = existing["document"]
                # Merge metadata
                existing_meta = existing.get("metadata", {})
                existing_meta.update(metadata)
                metadata = existing_meta

            if document:
                # Update document (and metadata if provided)
                update_args = {"ids": [doc_id], "documents": [document]}
                if metadata:
                    metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
                    update_args["metadatas"] = [metadata]

                self.collection.update(**update_args)
                logger.debug(f"Updated document: {doc_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            return False

    async def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if successful
        """
        if not self.collection:
            await self.connect()

        if not self.collection:
            raise RuntimeError("Vector store not connected")

        try:
            self.collection.delete(ids=[doc_id])
            logger.debug(f"Deleted document: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False

    async def delete_documents_batch(self, doc_ids: list[str]) -> int:
        """
        Delete multiple documents.
        
        Args:
            doc_ids: List of document IDs
            
        Returns:
            Number of documents deleted
        """
        if not self.collection:
            await self.connect()

        if not self.collection:
            raise RuntimeError("Vector store not connected")

        try:
            self.collection.delete(ids=doc_ids)
            logger.info(f"Deleted {len(doc_ids)} documents")
            return len(doc_ids)
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return 0

    async def count_documents(self) -> int:
        """
        Get total number of documents in collection.
        
        Returns:
            Document count
        """
        if not self.collection:
            await self.connect()

        if not self.collection:
            return 0

        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            return 0

    async def clear_collection(self) -> bool:
        """
        Clear all documents from collection.
        
        Returns:
            True if successful
        """
        if not self.collection:
            await self.connect()

        if not self.collection:
            return False

        try:
            # Get all IDs and delete them
            count = await self.count_documents()
            if count > 0:
                result = self.collection.get(limit=count, include=[])
                if result and result["ids"]:
                    self.collection.delete(ids=result["ids"])
            logger.info(f"Cleared {count} documents from collection")
            return True
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False

    async def get_collection_stats(self) -> dict[str, Any]:
        """
        Get statistics about the collection.
        
        Returns:
            Statistics dictionary
        """
        if not self.collection:
            await self.connect()

        if not self.collection:
            return {}

        try:
            count = await self.count_documents()
            metadata = self.collection.metadata

            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "embedding_model": self.embedding_model,
                "use_openai": self.use_openai,
                "collection_metadata": metadata,
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}

    def _generate_id(self, content: str) -> str:
        """Generate a unique ID for content using hash."""
        # Use SHA-256 hash of content + timestamp for uniqueness
        timestamp = datetime.now(timezone.utc).isoformat()
        content_hash = hashlib.sha256(f"{content}{timestamp}".encode()).hexdigest()
        return f"doc_{content_hash[:16]}"

    async def close(self) -> None:
        """Close vector store connection."""
        # ChromaDB persists automatically, no explicit close needed
        logger.info("Vector store closed")


class SemanticMemory:
    """
    High-level semantic memory interface using vector store.
    
    Provides convenient methods for storing and retrieving memories
    with automatic context management.
    """

    def __init__(self, vector_store: VectorStore | None = None) -> None:
        """
        Initialize semantic memory.
        
        Args:
            vector_store: Optional VectorStore instance (created if not provided)
        """
        self.vector_store = vector_store or VectorStore()

    async def initialize(self) -> None:
        """Initialize semantic memory."""
        await self.vector_store.connect()
        logger.info("Semantic memory initialized")

    async def remember(
        self,
        content: str,
        category: str | None = None,
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> str:
        """
        Store a memory.
        
        Args:
            content: Memory content
            category: Optional memory category
            importance: Importance score (0-1)
            tags: Optional list of tags
            
        Returns:
            Memory ID
        """
        metadata = {
            "category": category or "general",
            "importance": importance,
            "tags": tags or [],
        }
        return await self.vector_store.add_document(content, metadata=metadata)

    async def recall(
        self,
        query: str,
        n_results: int = 5,
        min_similarity: float = 0.0,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Recall memories similar to query.
        
        Args:
            query: Query text
            n_results: Number of results
            min_similarity: Minimum similarity threshold (0-1)
            category: Optional category filter
            
        Returns:
            List of relevant memories
        """
        where = {"category": category} if category else None
        results = await self.vector_store.search(query, n_results=n_results, where=where)
        
        # Filter by similarity threshold
        if min_similarity > 0:
            results = [r for r in results if r.get("similarity", 0) >= min_similarity]
        
        return results

    async def get_memory_stats(self) -> dict[str, Any]:
        """Get statistics about stored memories."""
        return await self.vector_store.get_collection_stats()

    async def close(self) -> None:
        """Close semantic memory."""
        await self.vector_store.close()
