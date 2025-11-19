# ChatSkLearn 

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-FF6B6B?style=for-the-badge&logo=langchain&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![Apache Airflow](https://img.shields.io/badge/Airflow-2.10.4-017CEE?style=for-the-badge&logo=apache-airflow&logoColor=white)](https://airflow.apache.org)
[![OpenSearch](https://img.shields.io/badge/OpenSearch-2.19.0-005EB8?style=for-the-badge&logo=opensearch&logoColor=white)](https://opensearch.org)
[![Langfuse](https://img.shields.io/badge/Langfuse-Latest-4F46E5?style=for-the-badge&logo=langfuse&logoColor=white)](https://langfuse.com)
[![Docker](https://img.shields.io/badge/Docker-Latest-1D63ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![uv](https://img.shields.io/badge/uv-Latest-FA6E32?style=for-the-badge&logo=uv&logoColor=white)](https://github.com/astral-sh/uv)

> **A production-grade RAG system that doesn't just answer questions—it thinks, plans, and executes.**

Most RAG implementations are glorified search wrappers. ChatSkLearn is different. We built an intelligent assistant that understands context, plans research strategies, and delivers answers with source citations.

---

## What Makes This Different

### Infrastructure-First Development
No prototypes. No "we'll productionize it later." ChatSkLearn ships production-ready from day one with Docker Compose orchestration, health checks, resource limits, and graceful degradation. The architecture scales horizontally, handles failures elegantly, and monitors itself.

### A Data Pipeline That Never Stops
Airflow orchestrates a monthly ingestion workflow that crawls 1000+ scikit-learn documentation pages, intelligently chunks content while preserving code blocks, generates embeddings in batches, and indexes everything into OpenSearch—automatically. Set it and forget it.

### Hybrid Search That Actually Works
We combine BM25 lexical matching with vector similarity using Reciprocal Rank Fusion (RRF). Query-type detection automatically adjusts field boosting, code examples get prioritized for implementation questions, API references surface for parameter queries. The result? Relevance that feels magical.

### An Agent That Plans Before It Acts
Powered by LangGraph, our assistant doesn't just retrieve and respond. It analyzes query intent, generates multi-step research plans, executes parallel document retrieval, and synthesizes answers with full conversation memory. It's RAG with a brain.

### Streaming Responses From the Ground Up
Real-time Server-Sent Events (SSE) stream not just the final answer, but every node execution in the graph. Watch as the system analyzes, researches, and formulates responses—with progress indicators, node execution details, and partial results appearing instantly.

### Source Citations That Matter
Every claim links directly to the source documentation with clean, clickable references. No generic "according to the documentation" handwaving. Users get breadcrumb navigation, page types, and direct URLs to verify information themselves.

### Observability That Ships By Default
Langfuse integration traces every LLM call, embedding generation, and retrieval operation. Performance metrics, token usage, latency monitoring, and conversation flows—all visible out of the box. Debug in production without guessing.

---

## The Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         INGESTION PIPELINE                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐      │
│  │ Scraper  │ → │ Chunker  │ → │ Embedder │ → │ Indexer  │      │
│  │ (Async)  │   │ (Smart)  │   │ (Batch)  │   │(Hybrid)  │      │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘      │
│       ↓              ↓              ↓              ↓            │
│   10K pages     1K chunks      768-dim        OpenSearch        │
│   /month        preserved      embeddings     BM25+Vector       │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                       QUERY PROCESSING                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐      │
│  │  Router  │ → │ Planner  │ → │Researcher│ → │Generator │      │
│  │(Classify)│   │(Strategy)│   │(Parallel)│   │(Stream)  │      │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘      │
│       ↓              ↓              ↓              ↓            │
│   Intent         3-step        RRF Fusion     SSE Stream        │
│   Detection      Plans         top-K docs     w/ Citations      │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY LAYER                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐      │
│  │ Langfuse │   │ OpenTel  │   │  Logs    │   │ Metrics  │      │
│  │ (Traces) │   │(Optional)│   │(Rotation)│   │(Health)  │      │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## The Tech Stack

**Orchestration**
- Docker Compose with health checks and resource limits
- Apache Airflow for scheduled ingestion (runs 28th of every month)

**Storage & Search**
- OpenSearch 2.19 with k-NN plugin for vector similarity
- PostgreSQL 16 for Airflow metadata and checkpointing

**Document Processing**
- AsyncIO-based crawler handling 10K+ pages with 25 concurrent connections
- Custom chunker preserving code blocks, headings, and context
- Google Gemini embeddings (text-embedding-004, 768 dimensions)

**Intelligence Layer**
- LangGraph for stateful agent workflows with memory
- Gemini 2.5 Flash for fast inference
- Custom hybrid search with query-type detection

**API & Frontend**
- FastAPI with SSE streaming and CORS for widget embedding
- Custom JavaScript chat interface with thread persistence
- Prism.js for syntax highlighting with copy-to-clipboard

**Monitoring**
- Langfuse for LLM observability and conversation tracing
- Structured logging with rotation
- OpenSearch Dashboards for search analytics

---

## Project Structure

```
chatsklearn/
│
├── airflow/                          # Airflow orchestration
│   ├── dags/
│   │   ├── sklearn_ingestion.py      # Main DAG definition
│   │   └── ingestion_tasks/          # Task implementations
│   │       ├── scrapper_task.py      # URL crawling
│   │       ├── chunking_task.py      # Document chunking
│   │       ├── embedding_task.py     # Embedding generation
│   │       └── indexing_task.py      # OpenSearch indexing
│   └── Dockerfile                    # Airflow custom image
│
├── src/                              # Core application
│   ├── config.py                     # Configuration management
│   ├── logger.py                     # Logging setup
│   ├── dependencies.py               # FastAPI dependencies
│   ├── main.py                       # FastAPI application
│   │
│   ├── services/                     # Business logic
│   │   ├── scrapper/
│   │   │   └── sklearn_scrapper.py   # Async web crawler
│   │   ├── chunking/
│   │   │   └── content_chunker.py    # Smart document chunking
│   │   ├── embedding/
│   │   │   └── embedding_service.py  # Batch embedding generation
│   │   ├── opensearch/
│   │   │   ├── factory.py            # Client connection
│   │   │   └── hybrid_search_service.py  # BM25 + Vector search
│   │   ├── indexing/
│   │   │   ├── index_config.py       # OpenSearch mappings
│   │   │   └── opensearch_indexer.py # Bulk indexing
│   │   ├── rag/
│   │   │   ├── states.py             # LangGraph state schemas
│   │   │   ├── prompts.py            # System prompts
│   │   │   ├── researcher_subgraph.py # Parallel retrieval
│   │   │   ├── sklearn_graph.py      # Main agent graph
│   │   │   └── rag_service.py        # RAG orchestration
│   │   └── langfuse/
│   │       └── langfuse_tracer.py    # Observability setup
│   │
│   ├── routers/
│   │   └── rag.py                    # FastAPI endpoints
│   │
│   ├── schemas/
│   │   └── api/
│   │       └── rag.py                # Pydantic models
│   │
│   └── frontend/                     # Chat interface
│       ├── index.html                # Main UI
│       ├── style.css                 # Styling
│       └── chat.js                   # Frontend logic
│
├── temp/                             # Temporary storage
│   ├── successful_urls.txt           # Crawled URLs
│   └── sklearn_scraped_data/         # Processed documents
│       ├── chunks_for_rag.jsonl      # JSONL chunks
│       ├── all_chunks.json           # Full chunk data
│       ├── embedded_chunks.json      # Chunks with embeddings
│       └── crawl_statistics.json     # Ingestion metrics
│
├── logs/                             # Application logs
│   └── *.log                         # Timestamped log files
│
├── compose.yml                       # Docker orchestration
├── Dockerfile                        # FastAPI service image
├── pyproject.toml                    # Python dependencies (uv)
├── uv.lock                           # Dependency lock file
├── .env.example                      # Environment template
└── README.md                         
```

**Key Directories Explained:**

- **`airflow/`**: Scheduled data pipeline running monthly. Each task is a standalone module that can be tested independently.

- **`src/services/`**: The heart of the system. Each service is loosely coupled—scraper, chunker, embedder, indexer, and RAG all operate independently with clear contracts.

- **`src/services/rag/`**: LangGraph implementation with state management, routing logic, parallel retrieval, and streaming response generation.

- **`src/frontend/`**: Zero-framework vanilla JavaScript chat interface. Thread persistence via localStorage, SSE streaming support, and syntax highlighting.

- **`temp/`**: Airflow writes here. Contains raw crawled data, processed chunks, and embeddings before they hit OpenSearch.

---

## What It Actually Does

### Smart Document Ingestion
The scraper doesn't just download HTML, it validates URL patterns, maintains proper path structures, preserves the documentation hierarchy, and handles failures gracefully. The chunker then extracts code blocks separately, maintains heading context, creates overlapping windows for continuity, and enriches every chunk with breadcrumbs and metadata.

### Query-Aware Retrieval
When you ask "How to use RandomForestClassifier?", the system detects it's a code-oriented query, boosts `code_blocks.code` and `full_text` fields, prioritizes example pages, and adjusts RRF weights for better code snippet retrieval. Ask about parameters? It shifts to API reference pages with heading emphasis.

### Research Planning
The assistant breaks complex queries into 1-3 research steps, generates diverse search queries per step (not repetitive variations), retrieves documents in parallel with Send() nodes, and accumulates knowledge before formulating the final answer. It thinks before it speaks.

### Conversation Memory
Every thread maintains full message history with automatic summarization when context exceeds 1000 tokens. The system retains the last 3 messages for immediate context while older exchanges get compressed into summaries. Users can resume conversations days later without losing context.

### Source Attribution
Responses include clickable documentation links placed immediately after relevant claims. URLs are shortened intelligently (e.g., `[RandomForestClassifier]` instead of the full path). Breadcrumb trails show exactly where in the documentation hierarchy each piece of information lives.

---

## Running It Locally

**Prerequisites**
- Docker Desktop with 8GB+ RAM allocated
- Google Gemini API key ([get one here](https://aistudio.google.com/api-keys))
- Langfuse account for observability ([free tier](https://cloud.langfuse.com))

**Quick Start**
```bash
# Clone and navigate
git clone https://github.com/kumar8074/chatsklearn.git
cd chatsklearn

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start everything
docker compose up -d

# Watch the magic happen
docker compose logs -f fastapi-app
```

**Access Points**
- Chat Interface: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- Airflow UI: `http://localhost:8080` (admin/admin)
- OpenSearch: `http://localhost:9200`
- OpenSearch Dashboards: `http://localhost:5601`

**First-Time Setup**
The system starts with an empty index. Trigger the ingestion pipeline:
1. Open Airflow at `http://localhost:8080`
2. Enable the `sklearn_documentation_ingestion` DAG
3. Click "Trigger DAG" (takes ~30-45 minutes)
4. Monitor progress in the Graph View

Alternatively, run the pipeline steps manually:
```bash
# Enter the Airflow scheduler container
docker exec -it chatsklearn-airflow-scheduler bash

# Run the full pipeline
airflow dags test sklearn_documentation_ingestion
```

---

## Configuration That Matters

**Chunking Strategy** (`src/config.py`)
```python
CHUNK_SIZE = 1000        # Words per chunk
CHUNK_OVERLAP = 200      # Overlap for continuity
```
Smaller chunks = more precise retrieval, more API calls  
Larger chunks = better context, fewer fragments

**Hybrid Search Weights** (`src/services/opensearch/hybrid_search_service.py`)
```python
bm25_weight = 0.4        # Lexical matching importance
vector_weight = 0.6      # Semantic similarity importance
```
Increase BM25 for exact terminology matching  
Increase vector weight for conceptual understanding

**Retrieval Top-K**
```python
top_k = 5               # Documents per query
```
More documents = better coverage, slower responses  
Fewer documents = faster, risk missing context

**Airflow Schedule** (`airflow/dags/sklearn_ingestion.py`)
```python
schedule_interval = '0 23 28 * *'  # 11 PM on 28th monthly
```
Adjust to match sklearn documentation update frequency

---

## The API Contract

**POST /api/rag/ask**  
Execute a query and return the complete result.
```json
{
  "user_id": "user_123",
  "message": "How to handle imbalanced datasets?",
  "thread_id": "optional_thread_id"
}
```
Response includes `final_message`, `router` classification, `documents_count`, and `steps_completed`.

**POST /api/rag/ask/stream**  
Execute with real-time streaming via Server-Sent Events.
```javascript
const es = new EventSource('/api/rag/ask/stream');
es.onmessage = (event) => {
  const chunk = JSON.parse(event.data);
  // chunk.node, chunk.event_type, chunk.data
};
```
Streams `analyze_and_route_query`, `create_research_plan`, `conduct_research`, `respond`, and `summarize_conversation` node updates.

**GET /api/rag/thread/{thread_id}**  
Retrieve full conversation history including summaries and metadata.

---

## Production Considerations

**Resource Requirements**
- Minimum: 8GB RAM, 4 CPUs
- Recommended: 16GB RAM, 8 CPUs
- Storage: ~2GB for OpenSearch index + embeddings

**Scaling Strategies**
- Increase Airflow `AIRFLOW__CORE__PARALLELISM` for faster ingestion
- Add FastAPI workers with `--workers N` in Dockerfile CMD
- Deploy OpenSearch cluster mode for distributed search
- Use Redis for distributed checkpointing in LangGraph

**Security Hardening**
- Enable OpenSearch security plugin in production
- Use secrets management (AWS Secrets Manager, Vault)
- Implement rate limiting on FastAPI endpoints
- Add authentication middleware for chat interface

**Monitoring in Production**
- Set up Langfuse alerts for high latency or errors
- Configure OpenSearch slow query logs
- Monitor Airflow DAG success rates and SLAs
- Track embedding API quota usage

---

## The Details That Matter

**Why Hybrid Search?**  
Pure vector search fails on exact terminology (e.g., "fit_transform" vs "fit and transform"). Pure BM25 misses semantic equivalence (e.g., "train a model" vs "fit an estimator"). Hybrid with RRF gives you both.

**Why LangGraph?**  
Linear RAG chains can't handle multi-turn conversations, complex queries requiring multiple searches, or conditional logic based on query type. LangGraph's state machine lets the agent plan, branch, and loop as needed.

**Why Airflow?**  
Running ingestion manually is error-prone. Airflow provides scheduling, retry logic, dependency management, and a UI for monitoring. The pipeline becomes infrastructure, not a script.

**Why Streaming?**  
Users don't want to wait 10+ seconds staring at a spinner. Streaming provides psychological feedback (the system is working), allows early information consumption, and enables progressive rendering of code blocks.

**Why Langfuse?**  
Black box LLM calls are impossible to debug. Langfuse captures every prompt, completion, token count, latency, and conversation flow. When something breaks, you know exactly where and why.

---

## What's Next

This system ships production-ready, but there's always room to push further:

- **Multi-model support**: Let users toggle between Gemini, Claude, and GPT-4
- **Document upload**: Extend beyond to user-uploaded code files
- **Feedback loops**: Use thumbs up/down to fine-tune retrieval weights
- **Collaborative features**: Share threads, annotate responses, bookmark answers
- **API rate limiting**: Per-user quotas with token bucket algorithm

A Simple, No InfraStructure version of this project can be accessed [Here](https://github.com/kumar8074/ChatSkLearn)

---

## Built By

**LALAN KUMAR**  
[GitHub](https://github.com/kumar8074) | [LinkedIn](https://www.linkedin.com/in/lalan-kumar-983267229/)

---

## License

MIT License

---

**Remember:** Most teams ship RAG without understanding what happens under the hood. We ship RAG with full visibility, intelligent routing, and production-grade infrastructure. That's the difference between a demo and a system.

Now go build something that actually works. 
