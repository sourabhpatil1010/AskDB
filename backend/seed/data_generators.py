import uuid
import random
from datetime import timedelta
from app.constants.enums import UserRole, EmployeeStatus, ProjectStatus, LeaveType, LeaveStatus
from app.models.auth.users import User
from app.models.business import (
    Department, Office, Employee, Client, Project, ProjectAssignment,
    Attendance, Payroll, LeaveRequest, PerformanceReview, Skill, EmployeeSkill
)
from app.models.history.search_history import SearchHistory
from app.models.history.saved_queries import SavedQuery
from seed.factory import fake

def chunk_list(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def generate_users(count: int) -> list[User]:
    users = []
    for _ in range(count):
        users.append(User(
            email=fake.unique.email(),
            password_hash="hashed_fake_password_123",
            role=random.choices([UserRole.USER, UserRole.ADMIN], weights=[95, 5])[0]
        ))
    return users

def generate_departments(count: int) -> list[Department]:
    departments = []
    base_depts = ["Engineering", "HR", "Sales", "Marketing", "Finance", "IT Support", "Operations", "Legal", "Product", "Design"]
    names = set(base_depts)
    while len(names) < count:
        names.add(f"{fake.company_suffix()} {fake.job()}")
    
    for name in list(names)[:count]:
        departments.append(Department(
            name=name,
            budget=round(random.uniform(500000.0, 5000000.0), 2)
        ))
    return departments

def generate_offices(count: int) -> list[Office]:
    offices = []
    for _ in range(count):
        offices.append(Office(
            name=f"{fake.city()} Office",
            city=fake.city(),
            country="India"
        ))
    return offices

def generate_skills(count: int) -> list[Skill]:
    skills = []
    categories = ["Frontend", "Backend", "Cloud", "Database", "Management", "Design", "Testing", "DevOps", "AI/ML", "Mobile"]
    unique_skills = set()
    while len(unique_skills) < count:
        unique_skills.add(fake.job()) 
    for s in list(unique_skills)[:count]:
        skills.append(Skill(
            name=s,
            category=random.choice(categories)
        ))
    return skills

def generate_clients(count: int) -> list[Client]:
    clients = []
    for _ in range(count):
        clients.append(Client(
            name=fake.unique.company(),
            industry=fake.bs().split()[-1].capitalize()
        ))
    return clients

def generate_projects(count: int, clients: list[Client]) -> list[Project]:
    projects = []
    for _ in range(count):
        start = fake.date_between(start_date='-2y', end_date='today')
        status = random.choice(list(ProjectStatus))
        end = fake.date_between(start_date=start, end_date='+1y') if status == ProjectStatus.COMPLETED else None
        
        projects.append(Project(
            client_id=random.choice(clients).id,
            name=f"{fake.catch_phrase()} Initiative",
            status=status,
            start_date=start,
            end_date=end
        ))
    return projects

def generate_employees(count: int, departments: list[Department], offices: list[Office]) -> list[Employee]:
    employees = []
    for _ in range(count):
        employees.append(Employee(
            department_id=random.choice(departments).id if departments else None,
            office_id=random.choice(offices).id if offices else None,
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.unique.company_email(),
            hire_date=fake.date_between(start_date='-5y', end_date='today'),
            status=random.choices(list(EmployeeStatus), weights=[90, 8, 2])[0]
        ))
    return employees

def generate_project_assignments(count: int, employees: list[Employee], projects: list[Project]) -> list[ProjectAssignment]:
    assignments = []
    seen = set()
    roles = ["Developer", "Manager", "Designer", "Tester", "Architect", "Consultant", "Analyst"]
    
    attempts = 0
    while len(assignments) < count and attempts < count * 2:
        attempts += 1
        emp = random.choice(employees)
        proj = random.choice(projects)
        pair = (emp.id, proj.id)
        if pair not in seen:
            seen.add(pair)
            assignments.append(ProjectAssignment(
                employee_id=emp.id,
                project_id=proj.id,
                role=random.choice(roles),
                allocation_percentage=random.randint(10, 100)
            ))
    return assignments

def generate_attendance(count: int, employees: list[Employee]) -> list[Attendance]:
    records = []
    seen = set()
    attempts = 0
    while len(records) < count and attempts < count * 2:
        attempts += 1
        emp = random.choice(employees)
        dt = fake.date_between(start_date='-1y', end_date='today')
        pair = (emp.id, dt)
        if pair not in seen:
            seen.add(pair)
            records.append(Attendance(
                employee_id=emp.id,
                date=dt,
                hours_worked=round(random.uniform(4.0, 10.0), 2)
            ))
    return records

def generate_payroll(count: int, employees: list[Employee]) -> list[Payroll]:
    records = []
    for _ in range(count):
        emp = random.choice(employees)
        start = fake.date_between(start_date='-1y', end_date='-1m')
        end = start + timedelta(days=30)
        records.append(Payroll(
            employee_id=emp.id,
            period_start=start,
            period_end=end,
            base_salary=round(random.uniform(30000, 200000), 2),
            bonus=round(random.uniform(0, 50000), 2) if random.random() > 0.8 else 0.0
        ))
    return records

def generate_leave_requests(count: int, employees: list[Employee]) -> list[LeaveRequest]:
    requests = []
    for _ in range(count):
        emp = random.choice(employees)
        start = fake.date_between(start_date='-1y', end_date='+3m')
        end = start + timedelta(days=random.randint(1, 14))
        requests.append(LeaveRequest(
            employee_id=emp.id,
            start_date=start,
            end_date=end,
            leave_type=random.choice(list(LeaveType)),
            status=random.choice(list(LeaveStatus))
        ))
    return requests

def generate_performance_reviews(count: int, employees: list[Employee]) -> list[PerformanceReview]:
    reviews = []
    for _ in range(count):
        emp = random.choice(employees)
        reviewer = random.choice(employees)
        while reviewer.id == emp.id:
            reviewer = random.choice(employees)
            
        reviews.append(PerformanceReview(
            employee_id=emp.id,
            reviewer_id=reviewer.id,
            review_date=fake.date_between(start_date='-1y', end_date='today'),
            score=random.randint(1, 5),
            comments=fake.paragraph() if random.random() > 0.5 else None
        ))
    return reviews

def generate_employee_skills(count: int, employees: list[Employee], skills: list[Skill]) -> list[EmployeeSkill]:
    emp_skills = []
    seen = set()
    attempts = 0
    while len(emp_skills) < count and attempts < count * 2:
        attempts += 1
        emp = random.choice(employees)
        sk = random.choice(skills)
        pair = (emp.id, sk.id)
        if pair not in seen:
            seen.add(pair)
            emp_skills.append(EmployeeSkill(
                employee_id=emp.id,
                skill_id=sk.id,
                proficiency_level=random.randint(1, 5)
            ))
    return emp_skills

def generate_saved_queries(count: int, users: list[User]) -> list[SavedQuery]:
    queries = []
    for _ in range(count):
        queries.append(SavedQuery(
            user_id=random.choice(users).id,
            name=f"Search {fake.word()}",
            natural_language=fake.sentence()
        ))
    return queries

def generate_search_history(count: int, users: list[User]) -> list[SearchHistory]:
    history = []
    for _ in range(count):
        history.append(SearchHistory(
            user_id=random.choice(users).id,
            natural_language=fake.sentence(),
            structured_json={"intent": fake.word(), "entities": []},
            generated_sql=f"SELECT * FROM {fake.word()}",
            execution_time_ms=random.randint(10, 500)
        ))
    return history
