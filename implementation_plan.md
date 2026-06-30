# Database Architecture Implementation Plan

This document outlines the schema design, relationships, and implementation strategy for the AskDB database before writing the SQLAlchemy 2.0 models and Alembic migrations.

## Proposed Changes

We will implement 15 tables normalized to 3NF, utilizing UUID primary keys, explicit foreign keys, `TIMESTAMP WITH TIME ZONE` for audit fields (`created_at`, `updated_at`), and appropriate ENUMs.

### Schema Design & Dictionary

#### Application Tables
1. **users**
   - **Purpose**: Core application identity.
   - **Columns**: `id` (UUID, PK), `email` (VARCHAR, UNIQUE), `password_hash` (VARCHAR), `role` (ENUM: admin, user), `created_at`, `updated_at`.
2. **search_history**
   - **Purpose**: Auditing and history of natural language searches.
   - **Columns**: `id` (UUID, PK), `user_id` (UUID, FK -> users), `natural_language` (TEXT), `structured_json` (JSONB), `generated_sql` (TEXT), `execution_time_ms` (INTEGER), `created_at`.
3. **saved_queries**
   - **Purpose**: Allow users to bookmark frequent searches.
   - **Columns**: `id` (UUID, PK), `user_id` (UUID, FK -> users), `name` (VARCHAR), `natural_language` (TEXT), `created_at`, `updated_at`.

#### Business Tables
4. **offices**
   - **Purpose**: Physical or logical office locations.
   - **Columns**: `id` (UUID, PK), `name` (VARCHAR), `city` (VARCHAR), `country` (VARCHAR), `created_at`, `updated_at`.
5. **departments**
   - **Purpose**: Organizational units.
   - **Columns**: `id` (UUID, PK), `name` (VARCHAR, UNIQUE), `budget` (NUMERIC), `created_at`, `updated_at`.
6. **employees**
   - **Purpose**: Core business entities.
   - **Columns**: `id` (UUID, PK), `department_id` (UUID, FK -> departments), `office_id` (UUID, FK -> offices), `first_name` (VARCHAR), `last_name` (VARCHAR), `email` (VARCHAR, UNIQUE), `hire_date` (DATE), `status` (ENUM: active, terminated, leave), `created_at`, `updated_at`.
7. **clients**
   - **Purpose**: External clients that own projects.
   - **Columns**: `id` (UUID, PK), `name` (VARCHAR, UNIQUE), `industry` (VARCHAR), `created_at`, `updated_at`.
8. **projects**
   - **Purpose**: Business initiatives for clients.
   - **Columns**: `id` (UUID, PK), `client_id` (UUID, FK -> clients), `name` (VARCHAR), `status` (ENUM: planned, active, completed, cancelled), `start_date` (DATE), `end_date` (DATE), `created_at`, `updated_at`.
9. **project_assignments**
   - **Purpose**: Junction table linking employees to projects.
   - **Columns**: `id` (UUID, PK), `employee_id` (UUID, FK -> employees), `project_id` (UUID, FK -> projects), `role` (VARCHAR), `allocation_percentage` (INTEGER, CHECK <= 100), `created_at`, `updated_at`.
10. **attendance**
    - **Purpose**: Track daily employee presence/hours.
    - **Columns**: `id` (UUID, PK), `employee_id` (UUID, FK -> employees), `date` (DATE), `hours_worked` (NUMERIC), `created_at`, `updated_at`.
11. **payroll**
    - **Purpose**: Financial compensation records.
    - **Columns**: `id` (UUID, PK), `employee_id` (UUID, FK -> employees), `period_start` (DATE), `period_end` (DATE), `base_salary` (NUMERIC), `bonus` (NUMERIC), `created_at`, `updated_at`.
12. **leave_requests**
    - **Purpose**: Employee time-off requests.
    - **Columns**: `id` (UUID, PK), `employee_id` (UUID, FK -> employees), `start_date` (DATE), `end_date` (DATE), `leave_type` (ENUM: sick, vacation, personal), `status` (ENUM: pending, approved, rejected), `created_at`, `updated_at`.
13. **performance_reviews**
    - **Purpose**: Employee evaluations.
    - **Columns**: `id` (UUID, PK), `employee_id` (UUID, FK -> employees), `reviewer_id` (UUID, FK -> employees), `review_date` (DATE), `score` (INTEGER, CHECK 1-5), `comments` (TEXT), `created_at`, `updated_at`.
14. **skills**
    - **Purpose**: Dictionary of available technical/soft skills.
    - **Columns**: `id` (UUID, PK), `name` (VARCHAR, UNIQUE), `category` (VARCHAR), `created_at`, `updated_at`.
15. **employee_skills**
    - **Purpose**: Junction table mapping skills to employees.
    - **Columns**: `employee_id` (UUID, FK -> employees, PK part 1), `skill_id` (UUID, FK -> skills, PK part 2), `proficiency_level` (INTEGER, CHECK 1-5), `created_at`, `updated_at`.

### File Structure Modifications

#### [NEW] `backend/app/models/business/__init__.py`
To organize the business tables separately from application logic tables.

#### [NEW] Model Files
- `backend/app/models/auth/users.py`
- `backend/app/models/history/search_history.py`
- `backend/app/models/history/saved_queries.py`
- `backend/app/models/business/organization.py` (offices, departments, employees, skills, employee_skills)
- `backend/app/models/business/projects.py` (clients, projects, project_assignments)
- `backend/app/models/business/hr.py` (attendance, payroll, leave_requests, performance_reviews)

#### [MODIFY] `backend/app/database/base.py`
Ensure all models are imported here so Alembic can discover them for migrations.

#### [NEW] `backend/alembic/versions/initial_migration.py`
A manually generated but accurate Alembic revision file that creates these 15 tables with proper ENUMs, foreign keys, constraints, and indexes.

### Index & Search Optimization Strategy
Since AskDB will translate natural language into SQL, indexing is critical for the resulting search queries to be fast:
- **Foreign Keys**: Every foreign key will have an explicit index (e.g., `ix_employees_department_id`).
- **Text Search**: We will add `B-Tree` indexes on high-cardinality search fields (`employees.email`, `employees.last_name`, `clients.name`).
- **Dates**: Indexes on `payroll.period_start`, `attendance.date`, and `projects.start_date` to rapidly filter timeline-based NL queries ("What was payroll last month?").
- **Unique Constraints**: Unique constraints automatically create indexes, protecting data integrity and speeding up exact lookups (`users.email`, `departments.name`).

## User Review Required
> [!IMPORTANT]
> Please review the structural grouping of models (e.g., grouping HR models into `hr.py`). Are you comfortable with this grouping, or would you prefer a separate file for every single table? 
>
> Once approved, I will generate the complete SQLAlchemy 2.0 ORM code, output the comprehensive documentation (ER Diagram, DB Dictionary), and provide the Alembic migration script.
