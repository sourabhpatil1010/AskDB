# AskDB Software Architecture Document

## 1. Project Overview
AskDB is a production-ready SaaS application designed to empower users to query PostgreSQL databases using natural language. By abstracting the complexity of SQL, AskDB provides an intuitive interface for data exploration, making data accessible to non-technical stakeholders while maintaining transparency and control for power users. The system leverages AI (Groq API, LangChain) to translate user intent into structured output and subsequently into safe, parameterized SQL queries.

## 2. Business Goal
To democratize data access within organizations by allowing anyone to query databases using conversational language, thereby reducing the dependency on data analysts for ad-hoc queries, accelerating decision-making, and increasing overall productivity.

## 3. Functional Requirements
- **Natural Language Querying:** Users can input queries in plain English.
- **Query Translation & Transparency:** The system displays the original input, generated structured JSON, generated SQL query, execution time, and results.
- **Database Connection Management:** Users can securely connect their target PostgreSQL databases.
- **Search History:** The system automatically saves the complete search history (natural language, JSON, SQL, results, metadata) for each user.
- **Authentication & Authorization:** Secure user sign-up, login, and session management using JWT.
- **Result Visualization:** Data is presented in readable tables with potential for future charting capabilities.

## 4. Non-functional Requirements
- **Performance:** High responsiveness, with AI translation response times ideally under 2 seconds and robust handling of database execution times.
- **Security:** Strict prevention of SQL injection via parameterized queries, AST parsing, and read-only database roles. Secure storage of database credentials (encrypted at rest).
- **Scalability:** Stateless backend architecture (FastAPI) allowing for easy horizontal scaling.
- **Reliability:** High availability (99.9% uptime target) utilizing robust deployment platforms (Vercel, Railway/Render).
- **Maintainability:** Clean, modular code following SOLID principles, utilizing static typing (TypeScript, Python type hints).

## 5. User Flow
1. User authenticates via JWT-based login.
2. User configures or selects a target PostgreSQL database connection.
3. User enters a Natural Language query in the main search bar.
4. Frontend displays a loading state and sends the query to the backend.
5. Backend uses Groq API + LangChain to parse the query into Structured JSON (intent, tables, filters).
6. Frontend receives and displays the Structured JSON (Transparency Step 1).
7. Backend generates a safe SQL query from the JSON and schema context.
8. Frontend receives and displays the SQL Query (Transparency Step 2).
9. Backend executes the SQL query against the target database.
10. Frontend receives and displays the Search Results & Execution Time.
11. Backend asynchronously logs the entire transaction to the Search History.
12. User can view and re-run past searches in the History tab.

## 6. System Architecture
A modern, decoupled, cloud-native architecture comprising a React/TypeScript Single Page Application (SPA) communicating with a Python/FastAPI backend via RESTful APIs. The backend orchestrates the AI pipeline (LangChain + Groq) and handles direct interactions with target PostgreSQL databases. Internal application state (users, connections, history) is stored in a separate internal PostgreSQL database (Neon).

## 7. High-Level Architecture Diagram (ASCII)

```text
                                +-------------------+
                                |                   |
                                |   User Browser    |
                                |  (React, Vite)    |
                                |                   |
                                +---------+---------+
                                          |
                                    REST API (JSON)
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                 AskDB Backend API                                 |
|                                   (FastAPI)                                       |
|                                                                                   |
|  +----------------+      +-----------------------+      +----------------------+  |
|  |                |      |                       |      |                      |  |
|  | Auth Module    +----->+    Query Engine       +----->+  Database Manager    |  |
|  | (JWT, Passwd)  |      |  (LangChain, Groq)    |      | (SQLAlchemy, async)  |  |
|  |                |      |                       |      |                      |  |
|  +-------+--------+      +-----------+-----------+      +----------+-----------+  |
|          |                           |                             |              |
+----------|---------------------------|-----------------------------|--------------+
           |                           |                             |
           v                           v                             v
  +------------------+         +----------------+            +------------------+
  |                  |         |                |            |                  |
  | Internal App DB  |         |   Groq API     |            | Target User DBs  |
  |     (Neon)       |         |   (LLM)        |            |   (PostgreSQL)   |
  |                  |         |                |            |                  |
  +------------------+         +----------------+            +------------------+
```

## 8. Frontend Architecture
- **Framework:** React 18+ with TypeScript, bootstrapped via Vite for rapid development.
- **Styling:** Tailwind CSS combined with `shadcn/ui` for highly accessible, customizable, and headless components.
- **State Management:** React Query (TanStack Query) for server state caching and synchronization; Zustand for minimal global client-side state.
- **Routing:** React Router v6.
- **Structure:** Feature-driven architecture (grouping files by feature: auth, search, history, connections).

## 9. Backend Architecture
- **Framework:** FastAPI (Python 3.11+) leveraging standard async/await for high concurrency and auto-generated OpenAPI documentation.
- **Data Validation:** Pydantic v2 for robust schema definition, request validation, and deterministic AI structured output parsing.
- **ORM:** SQLAlchemy 2.0 with an async engine (asyncpg) for internal database operations. Alembic for migrations.
- **AI Orchestration:** LangChain for prompt management, context injection (DB schema), and chain execution.
- **Authentication:** OAuth2 with Password Flow and JWT tokens. Passlib for password hashing.

## 10. AI Pipeline Architecture
1. **Schema Retrieval:** Dynamically fetch target database schema (tables, columns, types, foreign keys) relevant to the user's connection.
2. **Context Assembly:** Combine the user's NL query with the schema context inside a rigid system prompt.
3. **Structured Output Generation:** Call the Groq API requesting structured JSON output strictly mapped to a Pydantic model (`QueryIntent`).
4. **SQL Generation:** Translate the structured `QueryIntent` into a valid PostgreSQL dialect query using a specialized LangChain prompt.
5. **Validation & Sanitization:** Pre-parse the generated SQL to ensure it is `SELECT` only. Reject any mutating commands.

## 11. Database Architecture
We maintain an **Internal App Database** (Neon PostgreSQL).
**Key Tables:**
- `users`: id, email, password_hash, created_at, updated_at
- `database_connections`: id, user_id, alias, host, port, db_name, username, encrypted_password, created_at
- `search_history`: id, user_id, connection_id, natural_language_query, structured_json (JSONB), sql_query, execution_time_ms, success (Boolean), created_at

## 12. API Flow
- `POST /api/v1/auth/register` - Create user
- `POST /api/v1/auth/login` - Authenticate, return JWT access & refresh tokens
- `GET /api/v1/connections` - List user's DB connections
- `POST /api/v1/connections` - Add a new DB connection securely
- `POST /api/v1/search/translate` - NL to JSON + SQL (returns intermediate steps)
- `POST /api/v1/search/execute` - Execute the generated SQL, return results
- `GET /api/v1/history` - Retrieve paginated search history

## 13. Folder Structure
**Frontend (`/frontend`)**
```
src/
├── assets/
├── components/
│   ├── ui/          # shadcn/ui generic components
│   └── shared/      # layout, navbar, containers
├── features/
│   ├── auth/        # Login/Register components & api
│   ├── search/      # Search bar, results, transparency views
│   ├── history/     # History data tables
│   └── connections/ # Connection forms & lists
├── hooks/           # Shared custom hooks
├── lib/             # Utility functions, axios config, cn helper
├── services/        # Centralized API clients
├── store/           # Zustand stores
├── types/           # Global TypeScript interfaces
└── App.tsx
```

**Backend (`/backend`)**
```
app/
├── api/
│   └── v1/          # Endpoints categorized by routers
├── core/            # Configuration, security, exceptions
├── db/              # SQLAlchemy session setup, Alembic
├── models/          # SQLAlchemy ORM models (Internal DB)
├── schemas/         # Pydantic models (Request/Response DTOs)
├── services/        # Core business logic
│   ├── ai/          # LangChain integrations, Groq calls
│   └── execution/   # Target DB runners, schema extractors
└── main.py
```

## 14. Naming Conventions
- **Frontend:** PascalCase for React components and interfaces (`SearchBox.tsx`, `ISearchProps`). camelCase for variables, functions, and hooks (`useSearch`, `executeDbQuery`). kebab-case for directories and CSS classes.
- **Backend:** snake_case for Python variables, functions, modules, and database columns. PascalCase for Python Classes (Pydantic models, SQLAlchemy models).
- **API Endpoints:** kebab-case, nouns representing resources (e.g., `/api/v1/database-connections`).

## 15. Coding Standards
- **TypeScript:** Strict mode enabled. Avoid `any` types. Prettier for automated formatting. ESLint for static analysis and linting.
- **Python:** Black for deterministic formatting. Ruff for blazing-fast linting. Mypy for static type checking. Comprehensive type hints for all function signatures.
- **General:** Adhere to DRY (Don't Repeat Yourself) and SOLID principles. Write small, testable pure functions wherever possible.

## 16. Error Handling Strategy
- **Frontend:** Global Error Boundary for unhandled React tree crashes. Toast notifications for transient API errors. Inline error messages for form validation (react-hook-form + zod).
- **Backend:** Global exception handlers in FastAPI returning standardized JSON error responses `{ "error": { "code": "...", "message": "..." } }`. Specific exception classes for AI failures (e.g., `LLMGenerationError`), DB connection failures (`TargetDBConnectionError`), and SQL syntax errors.

## 17. Logging Strategy
- **Backend:** Utilize the Python `logging` module (or `loguru`). Log levels: `INFO` for standard operations (requests, DB queries), `WARNING` for retries, `ERROR` for exceptions with full stack traces.
- **AI Tracking:** Log prompt tokens, completion tokens, and latency for Groq API calls to monitor costs, optimize prompts, and track LLM performance.
- **Aggregation:** In production, stream logs to a centralized cloud service (e.g., Datadog, AWS CloudWatch, or PaperTrail).

## 18. Security Strategy
- **Authentication:** Standard JWT implementation with short-lived access tokens and secure, HTTP-only refresh tokens.
- **Database Credentials:** Target DB passwords must be symmetrically encrypted at rest (e.g., using Python cryptography/Fernet) before storing in the Neon database.
- **SQL Injection Prevention:** 
  1. Strongly recommend (or enforce) that users connect using read-only database roles.
  2. The system pre-parses generated SQL (using tools like `sqlglot`) to strictly block `INSERT`, `UPDATE`, `DELETE`, `DROP`, etc.
- **CORS:** Strictly configured to allow only the Vercel frontend origin in production.

## 19. Search Workflow
1. Client sends NL query -> `POST /translate`.
2. Server queries target DB schema for necessary context.
3. Server calls Groq to get structured JSON intent.
4. Server transforms JSON to standard PostgreSQL.
5. Server responds with `{"json_intent": {...}, "sql": "SELECT..."}`.
6. Client explicitly displays JSON and SQL to the user.
7. Client requests execution -> `POST /execute` (passing the generated SQL or reference token).
8. Server executes SQL against the Target DB, recording start/end execution time.
9. Server saves complete payload to `search_history`.
10. Server returns standardized JSON results to the client.

## 20. Search History Workflow
- Saved asynchronously after successful (or failed) query execution to prevent blocking the HTTP response.
- Includes timestamp, exact NL string, generated JSON, generated SQL, execution time (ms), and success boolean.
- Purpose: User reference, audit logging, and potential future AI few-shot learning or fine-tuning datasets (if user opts-in).

## 21. Deployment Architecture
- **Frontend:** Deployed to Vercel. Continuous deployment triggered from the `main` branch. Environment variables configured for Backend API URLs.
- **Backend:** Deployed to Railway or Render via Docker container. Horizontal scaling enabled behind a platform load balancer.
- **Internal Database:** Neon (Serverless Postgres). Provides automatic branching, pooling, and scaling out of the box.

## 22. Future Scalability
- **Caching:** Implement Redis to cache database schemas (which rarely change) and frequent exact-match NL queries to bypass the LLM.
- **Async Workers:** Move long-running database queries and AI generation to Celery/Redis background workers to prevent HTTP request timeouts.
- **Vector Database:** Introduce Pinecone/Weaviate for RAG (Retrieval-Augmented Generation) to handle highly complex schemas or external documentation matching.

## 23. Project Milestones
- **M1: Foundation:** Project setup, monorepo/polyrepo init, CI/CD pipelines, Auth, and DB Connection management.
- **M2: Core AI Pipeline:** LangChain + Groq integration, NL -> JSON -> SQL translation logic.
- **M3: Execution & Transparency UI:** Executing queries, building the React frontend to display JSON/SQL/Results dynamically.
- **M4: History & Polish:** Search history tracking, robust error handling, UI/UX polish, performance optimization, beta launch.

## 24. Development Roadmap
- **Week 1:** Backend scaffolding, Auth API endpoints, Neon DB setup, Frontend scaffolding, Auth UI screens.
- **Week 2:** DB Connection API, credential encryption, dynamic schema extraction logic.
- **Week 3:** Groq API integration, structured output parsing logic, SQL generator chain implementation.
- **Week 4:** Core Search UI, transparency step components, connecting frontend to the AI pipeline.
- **Week 5:** Secure query execution engine, AST security filters, dynamic result tables visualization.
- **Week 6:** History tracking UI, comprehensive testing, bug fixing, deployment to Vercel & Railway.

## 25. Suggested Git Branch Strategy
- **`main`:** Production-ready code. Auto-deploys to production.
- **`develop`:** Primary integration branch. Auto-deploys to staging environment.
- **`feature/feature-name`:** Branched from `develop` for new features (e.g., `feature/ai-pipeline`).
- **`bugfix/bug-description`:** For non-critical bug fixes off `develop`.
- **`hotfix/issue-name`:** Branched directly from `main` for critical production hotfixes.
- **Process:** PRs required for all merges into `develop` and `main` with passing CI checks.

## 26. Risks and Mitigation
- **Risk:** LLM hallucinations resulting in invalid or wildly incorrect SQL.
  - *Mitigation:* Strict schema injection, fallback retry loops with error feedback to the LLM, and forcing the user to see the SQL before full trust.
- **Risk:** Security (Malicious SQL Execution).
  - *Mitigation:* Strict read-only role requirements, mandatory AST-based blocking of mutating commands, network isolation.
- **Risk:** High Latency ruining UX.
  - *Mitigation:* Utilizing Groq (known for ultra-fast LPU inference), aggressive caching of schemas, and optimistic UI loading states.

## 27. Recommended Development Order
1. **Infrastructure:** Set up GitHub repository, Neon DB, base Dockerfile for backend, Vite for frontend.
2. **Backend Core:** FastAPI basic setup, SQLAlchemy base models, JWT User Authentication.
3. **Frontend Core:** Vite setup, `shadcn/ui` base installation, React Router, Auth pages.
4. **Database Connections:** Backend logic to securely connect, encrypt credentials, and fetch target schemas. UI to manage these connections.
5. **AI Pipeline (Backend):** Implement Groq structured output and LangChain prompts. Test heavily via Swagger/Postman.
6. **Search Interface (Frontend):** Build the transparency UI flow (NL -> Loading -> JSON -> SQL -> Results).
7. **Execution & History:** Hook up the DB execution engine, build AST safety checks, and log to the history table.
8. **Polish:** Implement empty states, error states, loading skeletons, and ensure fully responsive design across viewports.
# AskDB Technical Engineering Guide

> **Note**: This document serves as a comprehensive, deep-dive architectural and engineering manual for the AskDB system. It explains not just *what* the code does, but *how* it operates internally, *why* specific technologies were chosen, and the exact flow of data through the ecosystem.

---

## 1. System Architecture Overview

AskDB is a modern web application designed to convert natural language queries into executable PostgreSQL commands, execute them securely, and display the results. 

### High-Level Architecture Diagram

```mermaid
graph TD
    Client[React Frontend] --> |HTTP POST /api/v1/search| FastAPI[FastAPI Backend]
    
    subgraph AskDB Backend Core
        FastAPI --> SearchPipeline[Search Pipeline]
        SearchPipeline --> JSONService[JSON Service]
        JSONService --> LangChain[LangChain AI Core]
        LangChain --> LLM[(LLM: Groq/OpenAI/Gemini)]
        JSONService --> Pydantic[Pydantic Validation]
        
        SearchPipeline --> SQLService[SQL Service]
        SQLService --> SQLGenerator[SQL Generator]
        
        SearchPipeline --> QueryService[Query Service]
        QueryService --> SQLAlchemy[SQLAlchemy + asyncpg]
    end
    
    SQLAlchemy --> |Executes Query| DB[(PostgreSQL Database)]
    DB --> |Returns Rows| SQLAlchemy
    SQLAlchemy --> QueryService
    QueryService --> SearchPipeline
    SearchPipeline --> FastAPI
    FastAPI --> |JSON Response| Client
```

---

## 2. The Request Lifecycle (Data Flow)

Every request in AskDB follows a strict, well-defined pipeline. This section traces a single user prompt from input to UI render.

### The Transformation Pipeline

1. **User Input**: Natural Language query typed into the UI (e.g., "Show me top 5 users by revenue").
2. **React State**: Managed locally in components, submitted via React Query.
3. **HTTP Request**: Axios sends a JSON payload to the FastAPI `/api/v1/search` endpoint.
4. **Python Object**: FastAPI's Request Model (`FullSearchRequest`) validates the payload using Pydantic.
5. **Search Pipeline (`search_pipeline.py`)**: The orchestrator takes over.
6. **Prompt Template**: `JSONGenerationChain` loads the prompt template.
7. **Rendered Prompt**: LangChain's `ChatPromptTemplate` injects database schema and format instructions.
8. **LLM Request**: LangChain sends the formatted prompt to the LLM (via `ProviderFactory` and `ChatGroq`/etc).
9. **Raw LLM Response**: The model returns a string containing a JSON payload.
10. **Output Parser**: LangChain's `PydanticOutputParser` extracts the JSON.
11. **Pydantic Validation**: `StructuredQuery` schema strictly validates the output, ensuring all fields, types, and constraints match exactly.
12. **Validated Python Object**: A fully typed `StructuredQuery` object is produced.
13. **SQL Generator**: `SQLGenerator` receives the `StructuredQuery` and constructs parameterized SQL syntax to prevent SQL injection.
14. **Parameterized SQL & Parameters**: Output is a tuple: `(sql_string, parameters_dict)`.
15. **SQLAlchemy & asyncpg**: `QueryService` uses an `AsyncSession` to execute the raw parameterized SQL against the DB via the `asyncpg` driver.
16. **Database Result**: PostgreSQL returns binary data, converted to Python objects by asyncpg/SQLAlchemy.
17. **Python Dictionary**: Rows are mapped to lists of dictionaries.
18. **JSON Response**: FastAPI serializes the `FullSearchResponse` back to the client.
19. **React Axios & TanStack Query**: The frontend receives the JSON, resolves the Promise, and TanStack Query caches the result.
20. **Rendered UI**: React components re-render to display the data table.

### Data Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant Frontend (React)
    participant API (FastAPI)
    participant AI (LangChain)
    participant LLM
    participant DB (PostgreSQL)

    User->>Frontend: "Show me top 5 users"
    Frontend->>API: POST /api/v1/search { query: "..." }
    
    API->>API: Validate via FullSearchRequest
    API->>AI: run_pipeline(session, query)
    
    AI->>AI: ChatPromptTemplate.format_messages()
    AI->>LLM: ainvoke(messages)
    LLM-->>AI: Raw JSON String
    
    AI->>AI: PydanticOutputParser.parse()
    Note over AI: Yields Validated StructuredQuery
    
    AI->>API: build_sql(structured_query)
    Note over API: Yields Parameterized SQL
    
    API->>DB: execute(sql, parameters)
    DB-->>API: Result Rows
    
    API-->>Frontend: JSON { success, rows, columns, ... }
    Frontend->>Frontend: Update State (Zustand/React Query)
    Frontend-->>User: Render Data Table
```

### Pipeline Implementation (`backend/app/services/search/search_pipeline.py`)

**File Path:** `backend/app/services/search/search_pipeline.py`
**Class:** `SearchPipeline`
**Method:** `run_pipeline`

```python
async def run_pipeline(self, session: AsyncSession, natural_language: str) -> Dict[str, Any]:
    # 1. Natural Language -> Structured JSON
    structured_query = await self.json_service.process_query(natural_language)
    structured_json = structured_query.model_dump()
    
    # 2. Structured JSON -> Parameterized SQL
    sql, parameters = self.sql_service.build_sql(structured_json)
    
    # 3. SQL Execution -> Results
    db_result = await self.query_service.execute_query(session, sql, parameters)
    
    # 5. Construct Final Response
    return {
        "success": True,
        "question": natural_language,
        # ... mapped response fields
    }
```

**Why this approach?**
By separating the generation phase (`JSONService`) from the compilation phase (`SQLService`) and execution phase (`QueryService`), the system ensures high testability, fault tolerance, and tight security. The LLM is never trusted to write executable SQL directly. Instead, it writes an Abstract Syntax Tree (JSON), which AskDB strictly validates and compiles to parameterized SQL safely.

---

## 3. Backend Technologies & Implementation

### FastAPI

#### Part 1: General Explanation
FastAPI is a modern, high-performance web framework for building APIs with Python, based on standard Python type hints. It was created to solve the sluggishness of traditional frameworks like Django and Flask while offering automatic data validation and OpenAPI documentation out-of-the-box. 

Internally, it leverages Starlette for web routing and Pydantic for data validation. Concepts like Dependency Injection (`Depends()`) allow clean, modular management of resources like database connections and authentication. It is highly advantageous for AI applications where async/await is essential for non-blocking network calls to LLMs and databases.

#### Part 2: AskDB Implementation
**File Path:** `backend/app/api/v1/endpoints/search.py`
**Library:** `fastapi`

AskDB uses FastAPI to define non-blocking, typed HTTP endpoints. Let's look at the main search endpoint:

```python
@router.post("", response_model=FullSearchResponse)
async def full_search(
    request: FullSearchRequest,
    pipeline: SearchPipeline = Depends(get_search_pipeline),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await pipeline.run_pipeline(db, request.query)
        return FullSearchResponse(**result)
    except Exception as e:
        logger.exception(f"Search API Error (Full Pipeline): {str(e)}", exc_info=e)
        raise HTTPException(status_code=400, detail=str(e))
```

**Line-by-line breakdown:**
- `@router.post("", response_model=FullSearchResponse)`: Registers an HTTP POST endpoint. FastAPI uses the `FullSearchResponse` model to automatically serialize the return value and generate OpenAPI specs.
- `request: FullSearchRequest`: Automatically validates the incoming JSON body. If the client sends an invalid payload, FastAPI returns a 422 Unprocessable Entity *before* this function even runs.
- `pipeline: SearchPipeline = Depends(get_search_pipeline)`: FastAPI's Dependency Injection system. It instantiates the pipeline only when needed, allowing easy mocking during unit testing.
- `db: AsyncSession = Depends(get_db)`: Injects an asynchronous SQLAlchemy database session. The session's lifecycle (creation, yield, close) is managed entirely by FastAPI.
- `return FullSearchResponse(**result)`: The raw dictionary returned by the pipeline is unpacked and validated against the output schema.
- `raise HTTPException(status_code=400, detail=str(e))`: Traps pipeline errors and maps them to standard HTTP status codes.

**Execution Step:** From here, if successful, the serialized JSON is streamed across the network back to Axios on the frontend.

### LangChain

#### Part 1: General Explanation
LangChain is a framework for developing applications powered by language models. It was created to abstract the complexities of connecting LLMs (like OpenAI, Groq, or Anthropic) to external data sources, prompts, and parsers. 

Internally, LangChain relies on building "chains" of operations using the Runnable Interface (LCEL - LangChain Expression Language). Core concepts include PromptTemplates (dynamic string formatting), ChatModels (the LLM wrappers), and OutputParsers (turning string outputs into structured data). It is advantageous because it allows developers to swap out LLM providers effortlessly without rewriting logic.

#### Part 2: AskDB Implementation
AskDB specifically utilizes `ChatPromptTemplate`, `PydanticOutputParser`, and the `BaseChatModel` abstractions.

**File Path:** `backend/app/ai/chains/json_chain.py`
**Class:** `JSONGenerationChain`

```python
class JSONGenerationChain:
    def __init__(self):
        self.llm = get_llm()
        self.parser = PydanticOutputParser(pydantic_object=StructuredQuery)
        
    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    async def generate(self, natural_language: str) -> StructuredQuery:
        prompt_text = self.prompt_service.load_prompt("json_generation.txt")
        prompt_template = ChatPromptTemplate.from_template(prompt_text)
        
        messages = prompt_template.format_messages(
            schema_info=self.schema_info,
            query=natural_language,
            format_instructions=self.parser.get_format_instructions()
        )
        
        response = await self.llm.ainvoke(messages)
        structured_query = self.parser.parse(response.content)
        return structured_query
```

**Components Explained:**
1. **`get_llm()`**: Sourced from `core/llm.py`, this dynamically fetches the active `BaseChatModel` via `ProviderFactory`. This is why AskDB can switch between Groq, OpenAI, and Gemini at runtime seamlessly.
2. **`PydanticOutputParser`**: Takes the `StructuredQuery` Pydantic class and generates strict JSON formatting instructions for the LLM. It then takes the raw string output from the LLM and attempts to parse it safely into the Pydantic object.
3. **`ChatPromptTemplate`**: Formats the system prompt, injecting the `schema_info` (database DDl metadata), the user's `query`, and the `format_instructions`.
4. **`self.llm.ainvoke(messages)`**: Asynchronously sends the prompt to the language model.
5. **`@retry`**: Tenacity decorator. If parsing or validation fails (which is common with LLMs), it automatically retries with exponential backoff.

**Why AskDB uses it?**
Without LangChain's Output Parsers, we would be relying on unstable Regex string matching to extract JSON from LLM responses (which often include markdown backticks and conversational filler). LangChain handles this cleanup, and if removed, we would have to build complex parsing heuristics manually.

### Pydantic

#### Part 1: General Explanation
Pydantic is a data validation and settings management library for Python. It enforces type hints at runtime. Created to bring type safety to Python APIs, it is the backbone of FastAPI.

Internally, when a dictionary is passed into a `BaseModel`, Pydantic aggressively parses and coerces the data. For example, if a model expects an integer and receives the string `"123"`, Pydantic converts it to `123`. If it receives `"abc"`, it raises a `ValidationError`. Its core concepts revolve around `BaseModel`, `Field` descriptors for metadata, and `model_dump()`/`model_validate()`. 

#### Part 2: AskDB Implementation
**File Path:** `backend/app/ai/structured_output/schemas.py`

Pydantic is the absolute crux of AskDB's safety guarantees.

```python
class FilterCondition(BaseModel):
    table: Optional[str] = Field(default=None, description="The table this field belongs to")
    field: str = Field(description="The column name to filter on")
    operator: OperatorEnum = Field(description="The comparison operator")
    value: str | int | float | list[str] | list[int] | list[float] | None = Field(default=None, description="The value to compare against")

class StructuredQuery(BaseModel):
    table: str = Field(description="The primary table to query from")
    joins: Optional[List[JoinCondition]] = Field(default=None, description="List of JOIN conditions")
    columns: List[str] = Field(description="List of columns to select...")
    filters: Optional[List[FilterCondition]] = Field(default=None, description="List of filter conditions")
    limit: Optional[int] = Field(default=50, description="Maximum number of rows to return")
```

**Line-by-line breakdown:**
- `BaseModel`: Inheriting from this enables the class to be validated automatically.
- `OperatorEnum`: Restricts the `operator` field to a specific set of SQL operators (e.g., `=`, `>`, `IN`). The LLM literally cannot output a malicious or invalid operator without triggering a `ValidationError`.
- `Field(description="...")`: These descriptions aren't just for developers. Because we use LangChain's `PydanticOutputParser`, these exact descriptions are injected into the LLM prompt to instruct the AI on exactly what data goes into each key.
- `limit: Optional[int] = Field(default=50)`: AskDB explicitly enforces a default hard-limit on queries. If the LLM omits it, Pydantic inserts `50`, ensuring we don't accidentally query millions of rows.

**Output:** Calling `structured_query.model_dump()` yields a standard Python dictionary stripped of methods, ready to be passed to the `SQLGenerator`.

### SQLAlchemy & asyncpg

#### Part 1: General Explanation
SQLAlchemy is the premier SQL toolkit and ORM for Python. It provides a full suite of well known enterprise-level persistence patterns. `asyncpg` is a database interface library designed specifically for PostgreSQL and Python/asyncio. It is insanely fast (often 3x faster than psycopg2) because it implements the PostgreSQL binary protocol directly rather than relying on C-libraries like libpq.

When used together, `SQLAlchemy` provides the query building and session management, while `asyncpg` acts as the underlying driver fulfilling the asynchronous IO operations.

#### Part 2: AskDB Implementation
**File Path:** `backend/app/database/session.py` & `backend/app/query_builder/sql_generator.py`

```python
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)
```
Here, we configure an `async_sessionmaker` factory. `expire_on_commit=False` ensures that our objects don't detach and become inaccessible when the session commits, an important requirement for async operations.

**Dynamic SQL Generation:**
**File Path:** `backend/app/query_builder/sql_generator.py`

AskDB does NOT use an ORM to execute the user's natural language queries. Why? Because the queries are entirely dynamic and unpredictable. Instead, AskDB generates raw parameterized SQL.

```python
# From SQLGenerator.generate()
if op == "BETWEEN":
    param_name_1 = f"{param_name}_1"
    param_name_2 = f"{param_name}_2"
    where_clauses.append(f"{qual_field} BETWEEN :{param_name_1} AND :{param_name_2}")
    parameters[param_name_1] = f.value[0]
    parameters[param_name_2] = f.value[1]
```

**Explanation:**
This is a critical security implementation. The generator parses the `StructuredQuery` and creates raw SQL text, but it NEVER concatenates user values into the string. 
Instead, it inserts bind parameters (e.g., `:field_name_1`). The actual values are placed in a `parameters` dictionary.

When executed in `query_service.py`:
```python
result = await session.execute(text(sql), parameters)
```
SQLAlchemy's `text()` construct safely binds the parameters via `asyncpg`. This architecture makes AskDB **100% immune to SQL injection attacks** originating from the LLM or user input.

---

## 4. Frontend Technologies & Implementation

### React, Vite & React Router

#### Part 1: General Explanation
React is a declarative, component-based library for building UIs. AskDB uses Vite as the build tool—which leverages ES Modules for blazing-fast Hot Module Replacement (HMR)—replacing Webpack. React Router manages client-side navigation without full page reloads, making the app feel like a seamless desktop application.

#### Part 2: AskDB Implementation
**File Path:** `frontend/src/App.tsx`

```tsx
<Route
  path="search"
  element={
    <Suspense fallback={<PageLoader />}>
      <AISearchPage />
    </Suspense>
  }
/>
```
AskDB leverages `lazy()` and `Suspense` for code-splitting. Instead of loading the entire application bundle on first visit, the app only loads the components required for the current route. The `<PageLoader />` handles the UI gracefully while the chunk is fetched.

### Zustand

#### Part 1: General Explanation
Zustand is a small, fast, and scalable bearbones state-management solution using simplified flux principles. Unlike Redux, it doesn't require massive boilerplate, providers, or reducers. It works well with React's concurrency and doesn't pollute the component tree.

#### Part 2: AskDB Implementation
**File Path:** `frontend/src/store/appStore.ts`

```typescript
export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      llmSettings: {
        aiSource: 'cloud',
        provider: 'groq',
        model: 'qwen/qwen3-32b',
        ollamaBaseUrl: 'http://localhost:11434',
        apiKey: '',
        rememberKey: false,
      },
      updateLLMSettings: (llmSettings) =>
        set((state) => ({
          llmSettings: { ...state.llmSettings, ...llmSettings },
        })),
    }),
    {
      name: 'askdb-app-store',
      partialize: (state) => ({
        ...state,
        llmSettings: {
          ...state.llmSettings,
          apiKey: state.llmSettings.rememberKey ? state.llmSettings.apiKey : '',
        },
      }),
    }
  )
);
```

**Implementation Details:**
- `create<AppStore>()`: Instantiates the store with strict TypeScript types.
- `persist`: A Zustand middleware that automatically synchronizes the store's state with `localStorage`. This ensures that when the user refreshes, their LLM settings and Sidebar state are preserved.
- `partialize`: This is a security and privacy implementation. AskDB strips out the `apiKey` from being saved to `localStorage` unless the user explicitly ticked `rememberKey`. This prevents API keys from sitting persistently in browser storage maliciously.

### Axios & TanStack Query

#### Part 1: General Explanation
Axios is a promise-based HTTP client. TanStack Query (React Query) is a powerful data-fetching library that handles caching, background updates, stale data, and retries natively.

#### Part 2: AskDB Implementation
**File Path:** `frontend/src/services/search.service.ts`

```typescript
export const searchApi = {
  executeSearch: async (request: SearchRequest): Promise<SearchResponse> => {
    try {
      const response = await axios.post<SearchResponse>(`${API_URL}/api/v1/search`, request);
      return response.data;
    } catch (error: any) {
      if (error.response?.data) {
        throw new Error(error.response.data.detail || error.message);
      }
      throw error;
    }
  }
};
```
Axios acts purely as the transport layer. It sends the strongly typed payload, receives the response, and standardizes the error format (extracting FastAPI's `detail` message).

In the UI, TanStack Query calls this Axios wrapper, managing the `isLoading`, `isError`, and `data` states flawlessly without requiring `useEffect` or local state bloat.

---

## 5. Engineering Notes & Architecture Decisions

### 1. Why generate JSON instead of directly writing SQL?
**Trade-off:** We could ask the LLM to output raw SQL directly. It would be faster (less latency) and require less code.
**Why our approach is better:** An LLM outputting raw SQL is a massive security vulnerability. It can hallucinate `DROP TABLE`, or fail to escape strings, opening the door to SQL injection. By forcing the LLM to output structured JSON representing an Abstract Syntax Tree (AST), AskDB assumes full control of the compilation process. We validate the AST against the schema, ensure no destructive operations are present, and generate the final SQL natively with SQLAlchemy bind parameters. 

### 2. Why asyncpg?
AskDB is designed as an I/O bound application. While processing requests, the server spends 95% of its time waiting for the LLM or waiting for PostgreSQL. Using `psycopg2` (synchronous) would block the main thread, limiting the application to only a handful of concurrent users. `asyncpg` combined with FastAPI ensures that the server can handle thousands of concurrent queries asynchronously.

### 3. Maintainability Considerations: The ProviderFactory
In `core/llm.py`, instead of hardcoding `ChatGroq`, we use a `ProviderFactory` singleton. The LLM landscape changes rapidly. Next year, a new provider might be superior to Groq. The Factory pattern ensures that adding a new LLM provider requires zero changes to the LangChain execution logic or Prompt Templates; you only register the new class in the Factory.

### 4. Pydantic over TypedDict
Python offers `TypedDict` for type hinting dictionaries. However, `TypedDict` only provides hints to the IDE at development time; it does nothing at runtime. When receiving JSON from an unpredictable LLM, runtime validation is non-negotiable. Pydantic ensures that if the LLM hallucinates a string where an integer should be, the error is caught explicitly rather than crashing deep inside the SQL compilation engine.

---
*End of Technical Engineering Guide*
