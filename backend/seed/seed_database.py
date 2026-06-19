import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database.session import async_session_maker
from seed.data_generators import (
    generate_users, generate_departments, generate_offices, generate_skills,
    generate_clients, generate_projects, generate_employees, generate_project_assignments,
    generate_attendance, generate_payroll, generate_leave_requests, generate_performance_reviews,
    generate_employee_skills, generate_saved_queries, generate_search_history, chunk_list
)

logger = logging.getLogger(__name__)

async def clear_database(session: AsyncSession):
    logger.info("Clearing existing data...")
    tables = [
        "employee_skills", "performance_reviews", "leave_requests", "payroll", "attendance",
        "project_assignments", "projects", "clients", "employees", "departments", "offices",
        "skills", "saved_queries", "search_history", "users"
    ]
    for table in tables:
        await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
    await session.commit()
    logger.info("Database cleared.")

async def seed_all(clear: bool = True):
    async with async_session_maker() as session:
        try:
            if clear:
                await clear_database(session)

            logger.info("Generating base entities (Users, Departments, Offices, Skills, Clients)...")
            users = generate_users(100)
            departments = generate_departments(20)
            offices = generate_offices(10)
            skills = generate_skills(100)
            clients = generate_clients(100)
            
            session.add_all(users + departments + offices + skills + clients)
            await session.commit()

            logger.info("Generating employees (2000) and projects (300)...")
            projects = generate_projects(300, clients)
            employees = generate_employees(2000, departments, offices)
            
            session.add_all(projects + employees)
            await session.commit()

            logger.info("Generating project assignments (6000+)...")
            assignments = generate_project_assignments(6000, employees, projects)
            for chunk in chunk_list(assignments, 2000):
                session.add_all(chunk)
            await session.commit()

            logger.info("Generating attendance records (50000+)...")
            attendances = generate_attendance(50000, employees)
            for chunk in chunk_list(attendances, 5000):
                session.add_all(chunk)
            await session.commit()

            logger.info("Generating payroll records (24000+)...")
            payrolls = generate_payroll(24000, employees)
            for chunk in chunk_list(payrolls, 5000):
                session.add_all(chunk)
            await session.commit()

            logger.info("Generating leave requests (5000+)...")
            leaves = generate_leave_requests(5000, employees)
            for chunk in chunk_list(leaves, 2500):
                session.add_all(chunk)
            await session.commit()

            logger.info("Generating performance reviews (4000+)...")
            reviews = generate_performance_reviews(4000, employees)
            for chunk in chunk_list(reviews, 2000):
                session.add_all(chunk)
            await session.commit()

            logger.info("Generating employee skills (8000+)...")
            emp_skills = generate_employee_skills(8000, employees, skills)
            for chunk in chunk_list(emp_skills, 2000):
                session.add_all(chunk)
            await session.commit()

            logger.info("Generating search history (5000+) and saved queries (1000+)...")
            histories = generate_search_history(5000, users)
            for chunk in chunk_list(histories, 2500):
                session.add_all(chunk)
                
            saved_queries = generate_saved_queries(1000, users)
            session.add_all(saved_queries)
            await session.commit()

            logger.info("Database seeding completed successfully!")

        except Exception as e:
            await session.rollback()
            logger.error(f"Seeding failed: {e}")
            raise
