"""Tests for vector store functionality."""

import pytest

from xagent.memory.vector_store import SemanticMemory, VectorStore


@pytest.fixture
async def vector_store():
    """Create a vector store for testing."""
    store = VectorStore(collection_name="test_collection", use_openai=False)
    await store.connect()
    yield store
    # Cleanup
    await store.clear_collection()
    await store.close()


@pytest.fixture
async def semantic_memory(vector_store):
    """Create semantic memory for testing."""
    memory = SemanticMemory(vector_store=vector_store)
    await memory.initialize()
    yield memory
    await memory.close()


class TestVectorStore:
    """Test vector store operations."""

    @pytest.mark.asyncio
    async def test_connect(self, vector_store):
        """Test connection to ChromaDB."""
        assert vector_store.client is not None
        assert vector_store.collection is not None
        assert vector_store.embedding_function is not None

    @pytest.mark.asyncio
    async def test_add_document(self, vector_store):
        """Test adding a single document."""
        doc_id = await vector_store.add_document(
            "The quick brown fox jumps over the lazy dog",
            metadata={"category": "test", "source": "example"},
        )
        assert doc_id is not None
        assert doc_id.startswith("doc_")

    @pytest.mark.asyncio
    async def test_add_documents_batch(self, vector_store):
        """Test adding multiple documents in batch."""
        documents = [
            "Machine learning is a subset of artificial intelligence",
            "Deep learning uses neural networks with multiple layers",
            "Natural language processing enables computers to understand text",
        ]
        doc_ids = await vector_store.add_documents_batch(documents)
        assert len(doc_ids) == 3
        assert all(doc_id.startswith("doc_") for doc_id in doc_ids)

    @pytest.mark.asyncio
    async def test_get_document(self, vector_store):
        """Test retrieving a document by ID."""
        content = "Test document for retrieval"
        doc_id = await vector_store.add_document(content, metadata={"test": "value"})
        
        result = await vector_store.get_document(doc_id)
        assert result is not None
        assert result["id"] == doc_id
        assert result["document"] == content
        assert result["metadata"]["test"] == "value"

    @pytest.mark.asyncio
    async def test_search_semantic(self, vector_store):
        """Test semantic search."""
        # Add documents
        documents = [
            "Python is a programming language",
            "JavaScript is used for web development",
            "Machine learning algorithms learn from data",
            "Neural networks are inspired by the human brain",
        ]
        await vector_store.add_documents_batch(documents)

        # Search for similar documents
        results = await vector_store.search("artificial intelligence and learning", n_results=2)
        assert len(results) <= 2
        assert all("document" in r for r in results)
        assert all("similarity" in r for r in results)
        # Should find ML/neural network docs
        assert any("learning" in r["document"].lower() or "neural" in r["document"].lower() 
                  for r in results)

    @pytest.mark.asyncio
    async def test_search_with_filter(self, vector_store):
        """Test search with metadata filter."""
        # Add documents with different categories
        await vector_store.add_document(
            "Python programming tutorial",
            metadata={"category": "programming"}
        )
        await vector_store.add_document(
            "Machine learning basics",
            metadata={"category": "ml"}
        )
        
        # Search with filter
        results = await vector_store.search(
            "tutorial",
            n_results=5,
            where={"category": "programming"}
        )
        assert all(r["metadata"]["category"] == "programming" for r in results)

    @pytest.mark.asyncio
    async def test_update_document(self, vector_store):
        """Test updating a document."""
        doc_id = await vector_store.add_document("Original content")
        
        # Update content
        success = await vector_store.update_document(doc_id, document="Updated content")
        assert success is True
        
        # Verify update
        result = await vector_store.get_document(doc_id)
        assert result["document"] == "Updated content"

    @pytest.mark.asyncio
    async def test_update_metadata(self, vector_store):
        """Test updating document metadata."""
        doc_id = await vector_store.add_document(
            "Test content",
            metadata={"version": 1}
        )
        
        # Update metadata
        success = await vector_store.update_document(
            doc_id,
            metadata={"version": 2, "status": "updated"}
        )
        assert success is True
        
        # Verify metadata update
        result = await vector_store.get_document(doc_id)
        assert result["metadata"]["version"] == 2
        assert result["metadata"]["status"] == "updated"

    @pytest.mark.asyncio
    async def test_delete_document(self, vector_store):
        """Test deleting a document."""
        doc_id = await vector_store.add_document("To be deleted")
        
        # Delete
        success = await vector_store.delete_document(doc_id)
        assert success is True
        
        # Verify deletion
        result = await vector_store.get_document(doc_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_documents_batch(self, vector_store):
        """Test deleting multiple documents."""
        documents = ["Doc 1", "Doc 2", "Doc 3"]
        doc_ids = await vector_store.add_documents_batch(documents)
        
        # Delete batch
        deleted = await vector_store.delete_documents_batch(doc_ids)
        assert deleted == 3

    @pytest.mark.asyncio
    async def test_count_documents(self, vector_store):
        """Test counting documents."""
        initial_count = await vector_store.count_documents()
        
        # Add documents
        await vector_store.add_documents_batch(["Doc 1", "Doc 2", "Doc 3"])
        
        # Check count
        new_count = await vector_store.count_documents()
        assert new_count == initial_count + 3

    @pytest.mark.asyncio
    async def test_clear_collection(self, vector_store):
        """Test clearing all documents."""
        # Add documents
        await vector_store.add_documents_batch(["Doc 1", "Doc 2"])
        
        # Clear
        success = await vector_store.clear_collection()
        assert success is True
        
        # Verify empty
        count = await vector_store.count_documents()
        assert count == 0

    @pytest.mark.asyncio
    async def test_collection_stats(self, vector_store):
        """Test getting collection statistics."""
        await vector_store.add_documents_batch(["Doc 1", "Doc 2", "Doc 3"])
        
        stats = await vector_store.get_collection_stats()
        assert stats["collection_name"] == "test_collection"
        assert stats["document_count"] == 3
        assert "embedding_model" in stats

    @pytest.mark.asyncio
    async def test_similarity_scoring(self, vector_store):
        """Test that similarity scores are calculated correctly."""
        # Add a document
        await vector_store.add_document("Machine learning is artificial intelligence")
        
        # Search with exact match
        results = await vector_store.search("machine learning artificial intelligence", n_results=1)
        assert len(results) > 0
        assert "similarity" in results[0]
        assert 0 <= results[0]["similarity"] <= 1
        # Exact match should have high similarity
        assert results[0]["similarity"] > 0.5

    @pytest.mark.asyncio
    async def test_empty_search(self, vector_store):
        """Test search on empty collection."""
        results = await vector_store.search("any query", n_results=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_document_metadata_persistence(self, vector_store):
        """Test that metadata persists correctly."""
        metadata = {
            "importance": 0.9,
            "category": "critical",
            "tags": ["important", "urgent"],
        }
        doc_id = await vector_store.add_document("Important document", metadata=metadata)
        
        result = await vector_store.get_document(doc_id)
        assert result["metadata"]["importance"] == 0.9
        assert result["metadata"]["category"] == "critical"
        assert result["metadata"]["tags"] == ["important", "urgent"]


class TestSemanticMemory:
    """Test semantic memory interface."""

    @pytest.mark.asyncio
    async def test_initialize(self, semantic_memory):
        """Test semantic memory initialization."""
        assert semantic_memory.vector_store is not None
        assert semantic_memory.vector_store.collection is not None

    @pytest.mark.asyncio
    async def test_remember(self, semantic_memory):
        """Test storing a memory."""
        memory_id = await semantic_memory.remember(
            "I learned that Python is a great programming language",
            category="learning",
            importance=0.8,
            tags=["python", "programming"],
        )
        assert memory_id is not None

    @pytest.mark.asyncio
    async def test_recall(self, semantic_memory):
        """Test recalling memories."""
        # Store memories
        await semantic_memory.remember(
            "Python is great for data science",
            category="programming",
            importance=0.7,
        )
        await semantic_memory.remember(
            "JavaScript is used for web development",
            category="programming",
            importance=0.6,
        )
        await semantic_memory.remember(
            "Machine learning requires large datasets",
            category="ml",
            importance=0.9,
        )

        # Recall programming memories
        results = await semantic_memory.recall("programming languages", n_results=2)
        assert len(results) <= 2
        assert all("document" in r for r in results)

    @pytest.mark.asyncio
    async def test_recall_with_category_filter(self, semantic_memory):
        """Test recalling memories with category filter."""
        # Store memories in different categories
        await semantic_memory.remember("Python programming", category="code")
        await semantic_memory.remember("Data analysis", category="data")
        
        # Recall with filter
        results = await semantic_memory.recall("programming", category="code", n_results=5)
        assert all(r["metadata"]["category"] == "code" for r in results)

    @pytest.mark.asyncio
    async def test_recall_with_similarity_threshold(self, semantic_memory):
        """Test recalling memories with similarity threshold."""
        await semantic_memory.remember("Machine learning algorithms")
        
        # Recall with high similarity threshold
        results = await semantic_memory.recall(
            "machine learning",
            n_results=5,
            min_similarity=0.5,
        )
        # Should only return results with similarity >= 0.5
        assert all(r["similarity"] >= 0.5 for r in results)

    @pytest.mark.asyncio
    async def test_memory_stats(self, semantic_memory):
        """Test getting memory statistics."""
        await semantic_memory.remember("Memory 1")
        await semantic_memory.remember("Memory 2")
        
        stats = await semantic_memory.get_memory_stats()
        assert stats["document_count"] >= 2

    @pytest.mark.asyncio
    async def test_multiple_recall_operations(self, semantic_memory):
        """Test multiple recall operations work correctly."""
        # Store diverse memories
        memories = [
            ("Python is a versatile programming language", "programming"),
            ("Machine learning enables AI applications", "ml"),
            ("Web development uses HTML, CSS, and JavaScript", "web"),
            ("Data science involves statistics and programming", "data"),
        ]
        
        for content, category in memories:
            await semantic_memory.remember(content, category=category, importance=0.8)

        # Perform multiple recalls
        results1 = await semantic_memory.recall("programming", n_results=2)
        results2 = await semantic_memory.recall("artificial intelligence", n_results=2)
        results3 = await semantic_memory.recall("web design", n_results=2)

        assert len(results1) <= 2
        assert len(results2) <= 2
        assert len(results3) <= 2

    @pytest.mark.asyncio
    async def test_memory_importance_metadata(self, semantic_memory):
        """Test that importance metadata is stored correctly."""
        memory_id = await semantic_memory.remember(
            "Critical information",
            importance=0.95,
        )
        
        # Retrieve and check
        result = await semantic_memory.vector_store.get_document(memory_id)
        assert result["metadata"]["importance"] == 0.95

    @pytest.mark.asyncio
    async def test_memory_tags(self, semantic_memory):
        """Test that tags are stored and retrievable."""
        memory_id = await semantic_memory.remember(
            "Tagged memory",
            tags=["important", "urgent", "review"],
        )
        
        result = await semantic_memory.vector_store.get_document(memory_id)
        assert result["metadata"]["tags"] == ["important", "urgent", "review"]


class TestVectorStoreEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_document(self, vector_store):
        """Test handling of empty document."""
        doc_id = await vector_store.add_document("")
        assert doc_id is not None
        
        result = await vector_store.get_document(doc_id)
        assert result["document"] == ""

    @pytest.mark.asyncio
    async def test_very_long_document(self, vector_store):
        """Test handling of very long document."""
        long_doc = "word " * 10000  # 10k words
        doc_id = await vector_store.add_document(long_doc)
        assert doc_id is not None
        
        result = await vector_store.get_document(doc_id)
        assert result["document"] == long_doc

    @pytest.mark.asyncio
    async def test_special_characters_in_document(self, vector_store):
        """Test handling of special characters."""
        special_doc = "Test with special chars: @#$%^&*()_+-=[]{}|;:',.<>?/~`"
        doc_id = await vector_store.add_document(special_doc)
        
        result = await vector_store.get_document(doc_id)
        assert result["document"] == special_doc

    @pytest.mark.asyncio
    async def test_unicode_in_document(self, vector_store):
        """Test handling of Unicode characters."""
        unicode_doc = "Test with Unicode: 你好世界 مرحبا بالعالم Здравствуй мир"
        doc_id = await vector_store.add_document(unicode_doc)
        
        result = await vector_store.get_document(doc_id)
        assert result["document"] == unicode_doc

    @pytest.mark.asyncio
    async def test_get_nonexistent_document(self, vector_store):
        """Test getting a document that doesn't exist."""
        result = await vector_store.get_document("nonexistent_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_nonexistent_document(self, vector_store):
        """Test updating a document that doesn't exist."""
        success = await vector_store.update_document(
            "nonexistent_id",
            document="new content"
        )
        assert success is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, vector_store):
        """Test deleting a document that doesn't exist (should not raise error)."""
        success = await vector_store.delete_document("nonexistent_id")
        # Should handle gracefully
        assert success is True

    @pytest.mark.asyncio
    async def test_search_with_zero_results(self, vector_store):
        """Test search requesting zero results."""
        await vector_store.add_document("test document")
        results = await vector_store.search("test", n_results=0)
        assert results == []

    @pytest.mark.asyncio
    async def test_large_batch_operation(self, vector_store):
        """Test handling large batch of documents."""
        # Add 100 documents
        documents = [f"Document number {i}" for i in range(100)]
        doc_ids = await vector_store.add_documents_batch(documents)
        
        assert len(doc_ids) == 100
        
        # Verify count
        count = await vector_store.count_documents()
        assert count == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
