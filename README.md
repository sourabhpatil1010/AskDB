# AskDB

AskDB is a production-ready SaaS application that allows users to query PostgreSQL databases using natural language.

## Folder Structure

```text
AskDB/
├── backend/          # FastAPI, LangChain, Groq API backend
├── frontend/         # React 18, Vite, Tailwind CSS frontend
├── docker-compose.yml
├── Makefile
└── README.md
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd AskDB
   ```

2. **Configure Environments:**
   Copy the `.env.example` templates (or use the populated `.env` files if available).
   ```bash
   # Backend
   cp backend/.env.example backend/.env
   # Frontend
   cp frontend/.env.example frontend/.env
   ```

## Docker Setup (Recommended)

The easiest way to start the entire stack (Database, Backend API, Frontend React App) locally.

```bash
# Build and run all services
docker-compose up --build

# Run in detached mode
docker-compose up -d
```

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API Docs (Swagger): `http://localhost:8000/api/v1/openapi.json`

## Running Locally (Without Docker)

### Backend

1. Create a virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run FastAPI server:
```bash
uvicorn app.main:app --reload
```

### Frontend

1. Install Node modules:
```bash
cd frontend
npm install
```

2. Run Vite dev server:
```bash
npm run dev
```

## Development Commands

We provide a `Makefile` for quick development operations at the root:

- `make up`: Starts docker-compose in detached mode.
- `make down`: Stops docker-compose.
- `make build`: Rebuilds docker-compose containers.
- `make logs`: Follows logs from all containers.
- `make backend-shell`: Opens a bash shell in the backend container.
- `make frontend-shell`: Opens a shell in the frontend container.

## Architecture Overview

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query, Zustand.
- **Backend**: FastAPI, Python 3.12, SQLAlchemy 2.0 (async), Pydantic v2.
- **AI**: LangChain, Groq API.
- **Database**: PostgreSQL with asyncpg driver.

## License
MIT