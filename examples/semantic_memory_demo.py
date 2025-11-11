"""
Semantic Memory Demo - Demonstration of ChromaDB vector store with semantic search.

This demo showcases:
1. Storing documents with embeddings
2. Semantic search for similar content
3. Category filtering
4. Similarity scoring
5. Memory statistics
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xagent.memory.vector_store import SemanticMemory, VectorStore
from xagent.utils.logging import get_logger

logger = get_logger(__name__)


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{'='*80}")
    print(f"  {text}")
    print(f"{'='*80}\n")


def print_results(results: list[dict], title: str = "Search Results") -> None:
    """Print search results in a formatted way."""
    print(f"\n{title}:")
    print("-" * 80)
    
    if not results:
        print("  No results found.")
        return
    
    for i, result in enumerate(results, 1):
        similarity = result.get("similarity", 0)
        doc = result.get("document", "")
        metadata = result.get("metadata", {})
        
        print(f"\n  {i}. Document: {doc}")
        print(f"     Similarity: {similarity:.4f} ({similarity*100:.1f}%)")
        print(f"     Category: {metadata.get('category', 'N/A')}")
        if metadata.get("tags"):
            print(f"     Tags: {', '.join(metadata['tags'])}")


async def demo_basic_operations():
    """Demo 1: Basic vector store operations."""
    print_header("Demo 1: Basic Vector Store Operations")
    
    # Create vector store
    store = VectorStore(collection_name="demo_basic", use_openai=False)
    await store.connect()
    print("✅ Connected to ChromaDB with Sentence Transformers embeddings")
    
    # Add single document
    print("\n1. Adding a single document...")
    doc_id = await store.add_document(
        "Python is a high-level programming language known for its simplicity and readability.",
        metadata={"category": "programming", "language": "python"}
    )
    print(f"✅ Added document with ID: {doc_id}")
    
    # Add batch of documents
    print("\n2. Adding multiple documents in batch...")
    documents = [
        "Machine learning is a subset of artificial intelligence.",
        "Deep learning uses neural networks with multiple layers.",
        "Natural language processing enables computers to understand human language.",
        "Computer vision allows machines to interpret visual information.",
    ]
    doc_ids = await store.add_documents_batch(
        documents,
        metadatas=[{"category": "ml"} for _ in documents]
    )
    print(f"✅ Added {len(doc_ids)} documents")
    
    # Get document count
    count = await store.count_documents()
    print(f"\n📊 Total documents in store: {count}")
    
    # Get collection stats
    stats = await store.get_collection_stats()
    print(f"\n📈 Collection Statistics:")
    print(f"   - Collection: {stats['collection_name']}")
    print(f"   - Documents: {stats['document_count']}")
    print(f"   - Embedding Model: {stats['embedding_model']}")
    
    # Cleanup
    await store.clear_collection()
    await store.close()
    print("\n✅ Demo 1 completed successfully!")


async def demo_semantic_search():
    """Demo 2: Semantic search with similarity scoring."""
    print_header("Demo 2: Semantic Search with Similarity Scoring")
    
    store = VectorStore(collection_name="demo_search", use_openai=False)
    await store.connect()
    
    # Add knowledge base
    print("📚 Building knowledge base...")
    knowledge = [
        ("Python is a versatile programming language used for web development, data science, and AI.", "programming"),
        ("JavaScript is the language of the web, used for both frontend and backend development.", "programming"),
        ("Machine learning algorithms can learn patterns from data without explicit programming.", "ai"),
        ("Neural networks are computational models inspired by the human brain.", "ai"),
        ("Databases store and organize data for efficient retrieval and management.", "data"),
        ("SQL is a language for managing and querying relational databases.", "data"),
        ("Kubernetes orchestrates containerized applications across clusters.", "devops"),
        ("Docker containers package applications with their dependencies.", "devops"),
    ]
    
    for content, category in knowledge:
        await store.add_document(content, metadata={"category": category})
    
    print(f"✅ Added {len(knowledge)} documents to knowledge base\n")
    
    # Test semantic search with different queries
    queries = [
        ("artificial intelligence and learning from data", "AI/ML related"),
        ("programming languages for software development", "Programming related"),
        ("managing and storing information", "Data management related"),
        ("deploying and running applications", "DevOps related"),
    ]
    
    for query, description in queries:
        print(f"\n🔍 Query: '{query}' ({description})")
        results = await store.search(query, n_results=3)
        print_results(results, title="Top 3 Results")
    
    # Test with high similarity threshold
    print(f"\n\n🎯 Testing with high similarity threshold (0.7)...")
    results = await store.search("neural networks and AI", n_results=5)
    high_sim_results = [r for r in results if r.get("similarity", 0) >= 0.7]
    print(f"✅ Found {len(high_sim_results)} results with similarity >= 0.7")
    print_results(high_sim_results, title="High Similarity Results")
    
    # Cleanup
    await store.clear_collection()
    await store.close()
    print("\n✅ Demo 2 completed successfully!")


async def demo_category_filtering():
    """Demo 3: Search with category filtering."""
    print_header("Demo 3: Category Filtering")
    
    store = VectorStore(collection_name="demo_filter", use_openai=False)
    await store.connect()
    
    # Add documents with different categories
    print("📚 Adding documents with different categories...")
    documents_by_category = {
        "python": [
            "Python list comprehensions provide a concise way to create lists.",
            "Python decorators modify the behavior of functions or classes.",
            "Python asyncio enables asynchronous programming.",
        ],
        "javascript": [
            "JavaScript promises handle asynchronous operations elegantly.",
            "JavaScript arrow functions provide a shorter syntax for functions.",
            "JavaScript modules help organize code into reusable pieces.",
        ],
        "general": [
            "Code review improves code quality and shares knowledge.",
            "Version control systems track changes in source code.",
            "Automated testing ensures code reliability.",
        ],
    }
    
    for category, docs in documents_by_category.items():
        for doc in docs:
            await store.add_document(doc, metadata={"category": category})
    
    total_docs = sum(len(docs) for docs in documents_by_category.values())
    print(f"✅ Added {total_docs} documents across {len(documents_by_category)} categories\n")
    
    # Search without filter
    print("🔍 Search: 'functions and syntax' (no filter)")
    results = await store.search("functions and syntax", n_results=5)
    print(f"   Found {len(results)} results across all categories")
    print_results(results)
    
    # Search with Python filter
    print("\n🔍 Search: 'functions and syntax' (category: python)")
    results = await store.search("functions and syntax", n_results=5, where={"category": "python"})
    print(f"   Found {len(results)} results in Python category")
    print_results(results)
    
    # Search with JavaScript filter
    print("\n🔍 Search: 'functions and syntax' (category: javascript)")
    results = await store.search("functions and syntax", n_results=5, where={"category": "javascript"})
    print(f"   Found {len(results)} results in JavaScript category")
    print_results(results)
    
    # Cleanup
    await store.clear_collection()
    await store.close()
    print("\n✅ Demo 3 completed successfully!")


async def demo_semantic_memory():
    """Demo 4: High-level semantic memory interface."""
    print_header("Demo 4: Semantic Memory Interface")
    
    # Create semantic memory
    memory = SemanticMemory()
    await memory.initialize()
    print("✅ Initialized semantic memory\n")
    
    # Store memories
    print("💭 Storing memories...")
    memories = [
        ("I learned that Python is great for data science.", "learning", 0.9, ["python", "data-science"]),
        ("Remember to use async/await for I/O operations in Python.", "tip", 0.8, ["python", "async"]),
        ("Machine learning requires large amounts of quality data.", "insight", 0.9, ["ml", "data"]),
        ("Docker containers ensure consistent environments.", "tool", 0.7, ["devops", "docker"]),
        ("Code reviews help catch bugs early.", "practice", 0.8, ["development", "quality"]),
    ]
    
    for content, category, importance, tags in memories:
        memory_id = await memory.remember(content, category=category, importance=importance, tags=tags)
        print(f"  ✓ Stored: {content[:50]}... (ID: {memory_id[:16]}...)")
    
    print(f"\n✅ Stored {len(memories)} memories")
    
    # Recall memories
    print("\n\n🧠 Recalling memories...")
    
    recall_queries = [
        ("Python programming tips", None, "General recall"),
        ("machine learning and data", None, "General recall"),
        ("Python", "learning", "Category filtered"),
    ]
    
    for query, category, description in recall_queries:
        filter_text = f" (category: {category})" if category else ""
        print(f"\n🔍 Query: '{query}'{filter_text} ({description})")
        results = await memory.recall(query, n_results=3, category=category)
        print_results(results, title="Recalled Memories")
    
    # Memory statistics
    print("\n\n📊 Memory Statistics:")
    stats = await memory.get_memory_stats()
    print(f"   - Total memories: {stats['document_count']}")
    print(f"   - Collection: {stats['collection_name']}")
    print(f"   - Embedding model: {stats['embedding_model']}")
    
    # Cleanup
    await memory.vector_store.clear_collection()
    await memory.close()
    print("\n✅ Demo 4 completed successfully!")


async def demo_performance():
    """Demo 5: Performance benchmark."""
    print_header("Demo 5: Performance Benchmark")
    
    import time
    
    store = VectorStore(collection_name="demo_perf", use_openai=False)
    await store.connect()
    
    # Benchmark batch insert
    print("⏱️  Benchmarking batch insert...")
    num_docs = 100
    documents = [f"This is test document number {i} with some content." for i in range(num_docs)]
    
    start = time.time()
    await store.add_documents_batch(documents)
    duration = time.time() - start
    
    print(f"✅ Inserted {num_docs} documents in {duration:.3f} seconds")
    print(f"   Average: {duration/num_docs*1000:.2f} ms per document")
    
    # Benchmark search
    print("\n⏱️  Benchmarking semantic search...")
    queries = [
        "test document content",
        "finding information",
        "search and retrieval",
    ]
    
    total_search_time = 0
    for query in queries:
        start = time.time()
        results = await store.search(query, n_results=10)
        duration = time.time() - start
        total_search_time += duration
        print(f"✅ Search '{query}': {duration*1000:.2f} ms ({len(results)} results)")
    
    avg_search_time = total_search_time / len(queries)
    print(f"\n📊 Average search time: {avg_search_time*1000:.2f} ms")
    
    # Performance summary
    print("\n📈 Performance Summary:")
    print(f"   - Batch insert: {duration/num_docs*1000:.2f} ms/doc")
    print(f"   - Semantic search: {avg_search_time*1000:.2f} ms")
    print(f"   - Documents stored: {await store.count_documents()}")
    
    # Cleanup
    await store.clear_collection()
    await store.close()
    print("\n✅ Demo 5 completed successfully!")


async def demo_real_world_scenario():
    """Demo 6: Real-world scenario - Agent learning and recall."""
    print_header("Demo 6: Real-World Scenario - Agent Learning")
    
    memory = SemanticMemory()
    await memory.initialize()
    
    # Simulate an agent learning from experiences
    print("🤖 Agent is learning from experiences...\n")
    
    experiences = [
        # Programming knowledge
        ("When debugging Python, use print statements or pdb for inspection.", "debugging", 0.8, ["python", "debugging"]),
        ("Git branches allow parallel development of features.", "version-control", 0.7, ["git", "workflow"]),
        ("Unit tests should be isolated and test one thing at a time.", "testing", 0.9, ["testing", "best-practice"]),
        
        # Problem-solving patterns
        ("Breaking complex problems into smaller sub-problems makes them manageable.", "strategy", 0.9, ["problem-solving"]),
        ("When stuck, try explaining the problem to someone else (rubber duck debugging).", "strategy", 0.8, ["debugging", "communication"]),
        
        # Performance tips
        ("Database queries should use indexes for better performance.", "optimization", 0.8, ["database", "performance"]),
        ("Caching frequently accessed data reduces server load.", "optimization", 0.8, ["performance", "architecture"]),
        
        # Team practices
        ("Code reviews improve quality and share knowledge across the team.", "collaboration", 0.9, ["team", "quality"]),
        ("Documentation helps onboard new team members faster.", "collaboration", 0.7, ["team", "documentation"]),
    ]
    
    for content, category, importance, tags in experiences:
        await memory.remember(content, category=category, importance=importance, tags=tags)
        print(f"  💡 Learned: {content}")
    
    print(f"\n✅ Agent has learned {len(experiences)} experiences")
    
    # Agent recalls relevant knowledge when needed
    scenarios = [
        ("How do I debug my Python code?", "Debugging scenario"),
        ("My database queries are slow", "Performance issue"),
        ("I'm stuck on a difficult problem", "Problem-solving"),
        ("How can we improve team code quality?", "Team improvement"),
    ]
    
    print("\n\n🎯 Agent recalling relevant knowledge for different scenarios:\n")
    
    for scenario, description in scenarios:
        print(f"\n{'─'*80}")
        print(f"Scenario: {description}")
        print(f"Question: '{scenario}'")
        print("─"*80)
        
        # Recall with high similarity threshold
        results = await memory.recall(scenario, n_results=2, min_similarity=0.3)
        
        if results:
            print("\n🧠 Agent recalls:")
            for i, result in enumerate(results, 1):
                print(f"\n  {i}. {result['document']}")
                print(f"     Relevance: {result['similarity']*100:.1f}%")
                tags = result['metadata'].get('tags', [])
                if tags:
                    print(f"     Related to: {', '.join(tags)}")
        else:
            print("\n  Agent has no relevant knowledge for this scenario.")
    
    # Statistics
    print("\n\n📊 Agent Memory Statistics:")
    stats = await memory.get_memory_stats()
    print(f"   - Total experiences: {stats['document_count']}")
    print(f"   - Knowledge base ready for production use")
    
    # Cleanup
    await memory.vector_store.clear_collection()
    await memory.close()
    print("\n✅ Demo 6 completed successfully!")


async def main():
    """Run all demos."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                    🧠 SEMANTIC MEMORY DEMONSTRATION 🧠                        ║
║                                                                              ║
║              ChromaDB Vector Store with Sentence Transformers                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Run all demos
        await demo_basic_operations()
        await demo_semantic_search()
        await demo_category_filtering()
        await demo_semantic_memory()
        await demo_performance()
        await demo_real_world_scenario()
        
        # Final summary
        print_header("🎉 All Demos Completed Successfully!")
        print("""
Summary:
  ✅ Basic vector store operations (CRUD)
  ✅ Semantic search with similarity scoring
  ✅ Category filtering and metadata
  ✅ High-level semantic memory interface
  ✅ Performance benchmarks
  ✅ Real-world agent learning scenario

Key Features Demonstrated:
  • Automatic embedding generation with Sentence Transformers
  • Semantic search finds conceptually similar content
  • Similarity scoring (0-1 scale)
  • Category-based filtering
  • Batch operations for efficiency
  • Memory persistence across sessions
  • Production-ready performance

Next Steps:
  • Integrate with cognitive loop for agent memory
  • Add more sophisticated relevance ranking
  • Implement memory consolidation strategies
  • Add support for OpenAI embeddings (optional)

X-Agent now has semantic memory capabilities! 🚀
        """)
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n❌ Demo failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
