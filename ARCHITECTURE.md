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
