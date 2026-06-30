# AskDB Deployment Architecture Guide

> **Note**: This document provides a comprehensive enterprise-level deployment architecture guide for AskDB. It details the infrastructure, scaling strategies, security models, and exact request lifecycles necessary to run AskDB in production.

---

## Section 1 — Deployment Overview

AskDB is a modern, cloud-native application that leverages a decoupled architecture. To run AskDB in a production environment, the following core components are required:

1. **Frontend Presentation Layer**: A React-based Single Page Application (SPA) that provides the user interface.
2. **Backend API Layer**: A FastAPI server that orchestrates business logic, handles security, and manages state.
3. **AI Orchestration Layer**: LangChain pipelines that manage the translation of natural language to JSON AST, and then to SQL.
4. **LLM Provider**: The underlying AI engine (e.g., Groq, OpenAI, Ollama) that interprets user intent.
5. **Database Layer**: PostgreSQL databases, including an internal application state database and target user databases.

### High-Level Architecture Flow

```mermaid
graph TD
    User[User] --> |Browser| Frontend[React Frontend]
    Frontend --> |HTTPS/REST| Backend[FastAPI Backend]
    Backend --> |JSON| SearchPipeline[Search Pipeline]
    SearchPipeline --> |Prompt| LLM[LLM Provider]
    LLM --> |Structured JSON| SearchPipeline
    SearchPipeline --> |AST parsing| SQLGenerator[SQL Generator]
    SQLGenerator --> |Parameterized SQL| TargetDB[(Target PostgreSQL)]
    TargetDB --> |Result Rows| Backend
    Backend --> |JSON| Frontend
```

---

## Section 2 — Complete Technology Stack

| Component | Technology | Purpose | Why it was selected | Possible alternatives |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend** | React 19 / Vite | UI rendering and building | Extremely fast HMR, massive ecosystem, component reusability. | Angular, SvelteKit |
| **Language** | TypeScript | Static typing | Prevents runtime errors, enhances developer experience and refactoring. | JavaScript |
| **Styling** | TailwindCSS | Utility-first CSS framework | Rapid styling without context switching, highly optimized for production. | Styled Components, SASS |
| **Backend API** | FastAPI | Core backend framework | Built-in async support, automatic OpenAPI specs, high performance. | Django, Flask, Express.js |
| **Backend Server** | Uvicorn | ASGI web server | Required to run asynchronous Python code efficiently. | Gunicorn, Hypercorn |
| **AI Orchestration** | LangChain | LLM chaining and parsing | Standardizes interactions across different LLMs, handles output parsing cleanly. | LlamaIndex, Custom integration |
| **LLM Provider** | Groq / OpenAI | Inference generation | Groq provides ultra-fast LPU inference; OpenAI provides state-of-the-art accuracy. | Gemini, Anthropic, Ollama |
| **Database** | PostgreSQL | Relational database | Robust, ACID compliant, excellent JSONB support for history. | MySQL, MongoDB |
| **ORM / DB Driver** | SQLAlchemy & asyncpg | DB interaction | `asyncpg` is the fastest Python driver; SQLAlchemy provides safe parameter binding. | Prisma, Django ORM |
| **Validation** | Pydantic v2 | Data schema validation | Ensures LLM outputs strictly match the required JSON structure. | Marshmallow, Zod (Frontend) |
| **State Management**| Zustand / TanStack | Client-side state | React Query (TanStack) handles caching; Zustand handles minimal global state. | Redux Toolkit, Context API |
| **Networking** | Axios | HTTP client | Reliable, promise-based interceptors for auth tokens. | Fetch API |

---

## Section 3 — Production Architecture

The production environment separates concerns into distinct, scalable tiers. 

```mermaid
graph TD
    Browser[Client Browser]
    
    subgraph Edge Network
        CDN[CDN / Vercel]
    end
    
    subgraph Backend Infrastructure
        LB[Load Balancer]
        API1[FastAPI Instance 1]
        API2[FastAPI Instance 2]
    end
    
    subgraph AI Providers
        Groq[Groq API]
        OAI[OpenAI API]
    end
    
    subgraph Database Infrastructure
        InternalDB[(Internal App DB - Neon)]
        TargetDB[(User Target DBs)]
    end

    Browser -->|HTTPS| CDN
    CDN -->|Static Assets| Browser
    Browser -->|HTTPS / REST| LB
    LB --> API1
    LB --> API2
    
    API1 -->|HTTPS| Groq
    API1 -->|HTTPS| OAI
    API2 -->|HTTPS| Groq
    
    API1 -->|TCP/5432| InternalDB
    API2 -->|TCP/5432| TargetDB
```

### Communication Protocols
- **HTTPS**: Used for all client-to-backend and backend-to-LLM provider communication.
- **REST**: Architectural style for the FastAPI endpoints.
- **JSON**: The universal data interchange format used across the HTTP boundaries.
- **TCP (Port 5432)**: The PostgreSQL wire protocol used by `asyncpg` to communicate with the databases.

---

## Section 4 — Deployment Options

AskDB supports flexible deployment architectures based on privacy and performance requirements.

### Option 1: Cloud LLM Deployment
**Architecture:** React → FastAPI → Groq/OpenAI/Gemini → PostgreSQL
* **Advantages**: Minimal infrastructure to manage. Zero GPU requirements. Extremely fast (especially with Groq).
* **Disadvantages**: Data privacy concerns (sending database schema to third-party APIs). API rate limits.
* **Cost**: Pay-per-token API costs. Cheap server hosting (CPU only).
* **Security**: Relies on third-party data processing agreements (SOC2, HIPAA if applicable).

### Option 2: Local / Private LLM Deployment
**Architecture:** React → FastAPI → Ollama (Self-hosted) → PostgreSQL
* **Advantages**: Absolute data privacy. Air-gapped capable. No recurring API costs.
* **Disadvantages**: Requires significant hardware. Slower inference speeds compared to cloud providers.
* **Requirements**: 
  - **GPU**: NVIDIA RTX 3090/4090 or A100/H100 (depending on model size).
  - **CPU**: Multi-core processor for orchestration.
  - **RAM**: Minimum 32GB (for 7B-14B parameter models), up to 128GB+ for larger models.

---

## Section 5 — Environment Variables

Environment variables are critical for configuration and security.

| Variable | Purpose | Where Used | Required | Example |
| :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Connection string for internal DB. | `backend/app/core/config.py` | Yes | `postgresql+asyncpg://user:pass@host/askdb` |
| `SECRET_KEY` | Used to sign JWT tokens. | `backend/app/core/security.py` | Yes | `super_secret_string_32_bytes` |
| `GROQ_API_KEY` | Authenticates with Groq. | `backend/app/core/llm.py` | Conditional | `gsk_123456789...` |
| `OPENAI_API_KEY`| Authenticates with OpenAI. | `backend/app/core/llm.py` | Conditional | `sk-123456789...` |
| `OLLAMA_BASE_URL`| Points to local Ollama instance. | `backend/app/core/llm.py` | Conditional | `http://localhost:11434` |
| `MODEL_NAME` | Specifies the LLM model to use. | `backend/app/core/config.py` | Yes | `qwen/qwen3-32b` or `gpt-4o` |
| `APP_ENV` | Sets execution context. | Main app lifecycle. | No | `production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiration time. | Auth module. | No | `60` |

---

## Section 6 — Request Flow

The complete lifecycle of a natural language search request.

1. **User Entry**: User types *"Show all departments"* in the React UI.
2. **Browser (Axios)**: Wraps the request in a JSON payload and attaches the JWT authorization header.
3. **FastAPI Endpoint (`/api/v1/search`)**: Receives the request and validates it using Pydantic.
4. **Search Pipeline**: Orchestrates the multi-step process.
5. **Schema Extraction**: Backend queries the target PostgreSQL database to retrieve the DDL (schema).
6. **LangChain Context Assembly**: Combines the schema and user query into a system prompt.
7. **LLM Generation**: Makes an async HTTPS call to Groq.
8. **Structured JSON**: LLM returns a JSON string representing the query intent.
9. **Pydantic Validation**: `PydanticOutputParser` forces the string into a validated `StructuredQuery` object.
10. **SQL Generator**: A deterministic Python engine translates the `StructuredQuery` AST into a parameterized SQL string (e.g., `SELECT name FROM departments`).
11. **SQLAlchemy & asyncpg**: Safely binds any parameters and sends the query to the target database.
12. **Database Result**: PostgreSQL executes the query and returns binary rows.
13. **FastAPI Response**: Rows are mapped to JSON and returned to the client.
14. **React UI**: TanStack Query caches the response; React renders the data table.

---

## Section 7 — Network Communication

| Path | Protocol | Port | Authentication | Data Format |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend → Backend** | HTTPS / HTTP | 443 / 8000 | JWT (Bearer Token) | JSON |
| **Backend → DB (Internal)** | TCP (PostgreSQL) | 5432 | Username / Password | Binary Wire Protocol |
| **Backend → DB (Target)** | TCP (PostgreSQL) | 5432 | Username / Password | Binary Wire Protocol |
| **Backend → LLM (Cloud)**| HTTPS | 443 | API Key (Bearer) | JSON (REST/SSE) |
| **Backend → LLM (Local)**| HTTP | 11434 | None / Basic Auth | JSON |

---

## Section 8 — Deployment Platforms

### 1. Vercel (Frontend)
- **Advantages**: Best-in-class global CDN, instant deployments, seamless Vite support.
- **Disadvantages**: Serverless functions can have cold starts (though AskDB's backend isn't hosted here).
- **Recommended use case**: Production frontend hosting.

### 2. Railway / Render (Backend)
- **Advantages**: Native Docker support, auto-scaling, built-in CI/CD from GitHub, easy environment variable management.
- **Disadvantages**: PaaS premium pricing compared to raw VMs.
- **Recommended use case**: Production API hosting for fast iteration.

### 3. Docker (Self-Hosted / VPS like DigitalOcean)
- **Advantages**: Complete control, cheaper at scale, no platform lock-in.
- **Disadvantages**: Requires manual setup of reverse proxy (Nginx/Traefik), SSL certificates, and orchestration.
- **Recommended use case**: Cost-sensitive startups, enterprise on-premise deployments.

### 4. AWS / Azure / Google Cloud
- **Advantages**: Infinite scalability, enterprise compliance, virtual private clouds (VPC).
- **Disadvantages**: High complexity, requires dedicated DevOps/Terraform knowledge.
- **Recommended use case**: Large enterprise deployments requiring SOC2 compliance and VPC peering.

---

## Section 9 — Database Deployment

For AskDB's internal state (Users, Search History, Connection Metadata):

- **Recommended: Neon or Supabase (Serverless Postgres)**
  - **Advantages**: Auto-scaling compute, built-in connection pooling (PgBouncer), database branching for staging environments.
- **Migrations**: AskDB uses **Alembic**. Migrations should be run as part of the CI/CD pipeline or initialization script (`alembic upgrade head`) before the FastAPI application boots.
- **Security**: The internal database must be protected. Target database credentials must be encrypted symmetrically at the application layer *before* being stored in PostgreSQL.
- **Connection Pooling**: When deploying to serverless platforms, a connection pooler (like PgBouncer or Neon's native pooler) is mandatory to prevent exhausting PostgreSQL connections under high load.

---

## Section 10 — AI Provider Deployment

| Provider | Authentication | Latency | Advantages | Disadvantages | Production Suitability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Groq** | `GROQ_API_KEY` | **Ultra-low** (< 500ms) | Blazing fast, highly engaging UX. | Strict rate limits, fewer models. | Excellent |
| **OpenAI** | `OPENAI_API_KEY` | Medium (1-3s) | State-of-the-art reasoning (GPT-4o). | Higher cost. | Excellent |
| **Anthropic**| `ANTHROPIC_API_KEY`| Medium (1-3s) | Superior coding and formatting accuracy. | Strict rate limits. | Excellent |
| **Gemini** | `GEMINI_API_KEY` | Low/Medium | High rate limits on free tier, good context. | Sometimes inconsistent JSON. | Good |
| **Ollama** | URL (No Auth) | Hardware dependent | 100% private, free inference. | Requires expensive local GPUs. | Enterprise/On-Prem |

---

## Section 11 — Security

Security is the most critical aspect of AskDB, given it executes dynamic queries.

- **HTTPS / SSL**: Enforced universally. No plaintext HTTP traffic allowed in production.
- **CORS**: Configured in FastAPI (`main.py`) to only allow the Vercel frontend origin.
- **SQL Injection Prevention**: 
  - The LLM *never* writes raw SQL. It outputs a JSON AST.
  - The AST is validated by **Pydantic**.
  - The AST is converted to parameterized SQL using **SQLAlchemy** (`text(sql).bindparams()`).
- **Target DB Roles**: Users are strongly encouraged to provide credentials for a `READ-ONLY` database role.
- **Secrets Management**: API Keys and JWT secrets must be injected at runtime via secure environment variables, never committed to version control.

---

## Section 12 — Scaling

- **Horizontal Scaling**: The FastAPI backend is entirely stateless. You can spin up multiple containers (replicas) behind a Load Balancer. JWTs are verifiable without a database lookup, and session state is non-existent.
- **Database Scaling (Internal)**: Utilize connection pooling. If read traffic increases (e.g., loading history), introduce read replicas.
- **Database Scaling (Target)**: Ensure target databases have query timeouts configured to prevent long-running AI-generated queries from locking tables or consuming all workers.
- **Future Architecture**: For massive scale, background tasks (like saving to `search_history` or compiling massive schemas) can be offloaded to Celery workers via Redis.

---

## Section 13 — Monitoring

To maintain high availability, the following monitoring stack is recommended:

- **Logs**: Stream standard output from Docker/FastAPI to a centralized aggregator like Datadog, Better Stack, or AWS CloudWatch.
- **Health Checks**: Configure load balancers to ping the `/health` endpoint periodically. If it fails, the container should be cycled.
- **Metrics**: Expose Prometheus metrics from FastAPI to track request latency, LLM response times, and target database execution times.
- **Error Tracking**: Integrate Sentry into the frontend and backend to catch unhandled exceptions, specifically Pydantic validation errors (LLM hallucinations) and database connection drops.

---

## Section 14 — Deployment Checklist

**Pre-Flight:**
- [ ] Internal PostgreSQL database provisioned.
- [ ] Database migrations run (`alembic upgrade head`).
- [ ] Environment variables configured in hosting provider.
  - [ ] `DATABASE_URL`
  - [ ] `SECRET_KEY` (Generated securely)
  - [ ] API Keys (Groq, OpenAI, etc.)

**Deployment:**
- [ ] Backend deployed (Docker container running Uvicorn).
- [ ] Frontend deployed (Vercel).
- [ ] CORS `ALLOW_ORIGINS` updated to point to production frontend URL.
- [ ] SSL certificates provisioned and active.

**Post-Flight:**
- [ ] `/health` endpoint returns 200 OK.
- [ ] Can register a new user.
- [ ] Can connect a target database.
- [ ] End-to-end natural language search successfully returns data.

---

## Section 15 — Diagrams

### System & Infrastructure Diagram
```mermaid
graph TD
    subgraph Client
        UI[React App - Vercel]
    end

    subgraph API Gateway / Load Balancer
        LB[Nginx / Cloudflare]
    end

    subgraph Application Tier
        API[FastAPI Container]
        Background[Background Workers - Future]
    end

    subgraph Data Tier
        StateDB[(Neon App DB)]
        Redis[(Redis Cache - Future)]
    end

    subgraph External Dependencies
        LLM[Groq / OpenAI API]
        TargetDB[(Client PostgreSQL)]
    end

    UI -->|HTTPS| LB
    LB --> API
    API -->|Read/Write| StateDB
    API -->|HTTPS Request| LLM
    API -->|Parameterized Query| TargetDB
```

---

## Section 16 — Code References

### FastAPI Entry Point
- **File:** `backend/app/main.py`
- **Purpose:** Initializes the FastAPI application, mounts CORS middleware, and includes API routers.
- **How it works:** Uses Uvicorn as the ASGI server. It is the root node of the backend architecture. It initializes the `ProviderFactory` on the startup event.

### Search Pipeline Orchestrator
- **File:** `backend/app/services/search/search_pipeline.py`
- **Purpose:** Manages the entire data flow from NLP to SQL execution.
- **How it works:** Connects the `JSONService`, `SQLService`, and `QueryService`. It ensures that execution stops immediately if the LLM hallucinates an invalid JSON structure.

### Output Validation
- **File:** `backend/app/ai/structured_output/schemas.py`
- **Purpose:** Defines the `StructuredQuery` Pydantic model.
- **Why it is needed:** This file acts as the primary security firewall. It prevents invalid SQL operators or malformed logic from ever reaching the SQL generator.

---

## Section 17 — Engineering Notes

- **Why FastAPI over Django?**
  AskDB is heavily reliant on concurrent I/O operations (waiting for LLMs and databases). FastAPI's native `asyncio` support allows a single worker to handle thousands of requests concurrently without thread-blocking, which is a massive performance advantage over traditional synchronous frameworks.
- **Why LangChain?**
  Vendor lock-in is a significant risk in the AI space. By using LangChain, the system interacts with an abstraction (`BaseChatModel`) rather than the Groq or OpenAI SDKs directly. Swapping providers is as simple as changing an environment variable.
- **Security by Design:**
  The decision to parse natural language into a JSON AST rather than raw SQL introduces overhead but is non-negotiable for enterprise deployment. It is the only reliable method to sanitize AI output before it hits a target database, providing a mathematically provable defense against SQL injection.
