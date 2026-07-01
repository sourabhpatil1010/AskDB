"""Comprehensive test suite covering 150 queries (50 simple, 50 medium, 50 complex business queries)."""
import pytest
from app.ai.planner.planner import AIQueryPlanner
from app.ai.planner.planner_schema import ExecutionPlan, IntentEnum

SIMPLE_QUERIES = [
    "Compare average salary by department",
    "Employees hired after COVID",
    "List all employees in IT department",
    "Count total number of employees",
    "Show all active employees",
    "Find projects for client Acme Corp",
    "Average performance review score",
    "Total budget across all departments",
    "List skills in technical category",
    "Show employees currently on sick leave",
    "Count total departments in the organization",
    "Find office location in London",
    "List all clients in the banking industry",
    "Show planned projects for this year",
    "Average hourly wage for contractors",
    "Count active projects",
    "List employees hired today",
    "Show attendance records for yesterday",
    "Total bonus paid out this month",
    "Find employees with status terminated",
    "List all software engineering projects",
    "Count total number of offices",
    "Average allocation percentage across assignments",
    "Show leave requests pending approval",
    "Find performance reviews with score 5",
    "List all soft skills available",
    "Count employees assigned to project X",
    "Show base salary for employee John Doe",
    "Find departments with budget over 500000",
    "List employees hired last year",
    "Average attendance hours worked this week",
    "Count total leave requests approved",
    "Show clients added this quarter",
    "List projects starting next month",
    "Find offices in United States",
    "Average bonus percentage by department",
    "Count total project assignments",
    "Show employees on personal leave",
    "Find skills with advanced proficiency",
    "List performance reviews conducted last month",
    "Count total active clients",
    "Show payroll records for last quarter",
    "Find employees hired in 2023",
    "Average base salary across company",
    "List all cancelled projects",
    "Count employees in New York office",
    "Show leave requests for next week",
    "Find departments without budget allocation",
    "List attendance hours worked yesterday",
    "Count total completed projects"
]

MEDIUM_QUERIES = [
    "Top 10 departments with highest payroll",
    "Departments with more than 50 employees",
    "Managers with highest team salary",
    "Average attendance by project",
    "List employees hired between January and June 2024",
    "Find projects ending this quarter with budget above 100000",
    "Top 5 clients by number of active projects",
    "Count employees on vacation this week by department",
    "Average salary of active employees by office city",
    "Top 3 skills with highest employee proficiency levels",
    "Departments with average performance score above 4",
    "List employees with more than 3 active project assignments",
    "Compare total bonus payout between IT and Sales departments",
    "Find clients with more than 5 completed projects last year",
    "Average leave duration by leave type for active employees",
    "Top 5 offices by total employee headcount",
    "Projects with allocation percentage exceeding 80 percent",
    "Count performance reviews below average score by department",
    "Average attendance hours worked by employees hired after 2022",
    "Find departments where total payroll exceeds budget",
    "Top 10 highest paid employees across all offices",
    "List projects with zero attendance recorded last week",
    "Compare average salary of active versus terminated employees",
    "Departments with more than 10 pending leave requests",
    "Find managers whose team has average score above 4.5",
    "Top 5 projects by total hours worked this month",
    "Count employees with proficiency level 5 in Python",
    "Average budget of projects for clients in technology industry",
    "List offices with more than 20 employees hired last year",
    "Find employees who have not taken vacation this year",
    "Compare average attendance hours between London and New York offices",
    "Top 3 departments with lowest employee turnover rate",
    "Find projects where start date is after client creation date",
    "Count employees assigned to multiple concurrent projects",
    "Average base salary of employees with more than 5 skills",
    "List departments with budget increase compared to last year",
    "Top 5 clients with highest total project revenue",
    "Find employees with performance review score below 3 this year",
    "Average allocation percentage by project status",
    "Count leave requests rejected by department manager",
    "Top 10 employees by total bonus earned across all years",
    "Find projects that have been active for more than 2 years",
    "Compare average performance score of remote vs office employees",
    "Departments with more than 3 cancelled projects this year",
    "List skills required by more than 15 active projects",
    "Average salary of employees hired before 2020 by department",
    "Top 5 offices with highest average employee tenure",
    "Find clients who initiated new projects this quarter",
    "Count employees on sick leave for more than 5 consecutive days",
    "Compare total attendance hours between Q1 and Q2 this year"
]

COMPLEX_QUERIES = [
    "Employee growth year over year across all departments",
    "Salary increase compared to previous year by department",
    "Top 5 departments with highest hiring growth rate",
    "Average salary of employees hired after 2021 excluding interns",
    "Compare average hours worked month over month for IT project assignments",
    "Distribution of performance scores across departments for employees hired before COVID",
    "Rank offices by total payroll percentage increase compared to last financial year excluding terminated staff",
    "Find departments with lowest employee retention growth rate over last 3 years",
    "Correlation between technical skill proficiency level and base salary across active projects",
    "Compare year over year bonus growth rate for managers with team size above 15",
    "Top 3 clients with highest project budget growth over last 3 financial years",
    "Analyze month over month attendance variation for remote employees excluding interns",
    "Find departments where average salary increase exceeds company average growth rate",
    "Distribution of leave types taken before versus after COVID across offices",
    "Rank projects by percentage difference between allocated hours and actual attendance hours",
    "Compare average performance review progression year over year for employees promoted after 2022",
    "Top 5 skills associated with highest salary growth rate over last 2 years",
    "Analyze seasonal trend in sick leave requests month over month across all departments",
    "Find offices with highest percentage increase in headcount compared to previous financial year",
    "Compare average project completion time before COVID versus after COVID by client industry",
    "Distribution of allocation percentage across active projects for employees with salary above 100000",
    "Rank departments by ratio of bonus payout to base salary year over year",
    "Find clients whose average project budget grew faster than inflation rate over last 3 years",
    "Analyze correlation between employee training skill acquisition and subsequent performance score increase",
    "Compare year over year turnover rate between technical and non technical departments",
    "Top 5 projects with highest monthly attendance variance compared to planned allocation",
    "Distribution of salary across proficiency levels for top 10 most demanded technical skills",
    "Rank managers by average percentage salary increase awarded to their teams this year",
    "Find departments with above average employee tenure and below average salary growth",
    "Analyze month over month project expense trend compared to department budget quarterly allocation",
    "Compare average leave duration before promotion versus after promotion for senior staff",
    "Top 3 offices with highest year over year growth in client acquisition and project starts",
    "Distribution of performance review comments sentiment across departments with high turnover",
    "Rank clients by profitability growth rate calculated from project budget versus attendance cost",
    "Find employees whose salary increased by more than 20 percent year over year excluding promotions",
    "Analyze trend in average hours worked per week across consecutive financial quarters",
    "Compare bonus percentage distribution between departments with above average and below average budget",
    "Top 5 skills where employee proficiency level increased fastest year over year",
    "Rank projects by team performance review average compared to project completion delay",
    "Find departments where hiring growth rate exceeded budget growth rate over last 2 financial years",
    "Analyze year over year correlation between remote work attendance and performance scores",
    "Compare average tenure of employees assigned to long term versus short term projects",
    "Top 3 industries with highest project budget percentage increase compared to last year",
    "Distribution of employee age and tenure across departments with highest revenue growth",
    "Rank offices by efficiency score calculated from attendance hours per completed project milestone",
    "Find managers with highest retention rate during periods of below average salary growth",
    "Analyze trend in leave request approval rate month over month across different office locations",
    "Compare year over year skill gap reduction across technical project teams",
    "Top 5 departments by overall productivity growth rate compared to previous financial year",
    "Rank active clients by year over year increase in total dedicated employee headcount"
]


@pytest.mark.asyncio
@pytest.mark.parametrize("query", SIMPLE_QUERIES)
async def test_simple_queries(query):
    planner = AIQueryPlanner()
    plan = await planner.plan(query)
    assert isinstance(plan, ExecutionPlan)
    assert plan.confidence >= 0.70
    assert len(plan.tables) >= 1
    assert plan.intent in IntentEnum or isinstance(plan.intent, str)


@pytest.mark.asyncio
@pytest.mark.parametrize("query", MEDIUM_QUERIES)
async def test_medium_queries(query):
    planner = AIQueryPlanner()
    plan = await planner.plan(query)
    assert isinstance(plan, ExecutionPlan)
    assert plan.confidence >= 0.70
    assert len(plan.tables) >= 1
    # Ensure intermediate joins or group by / having or filters are detected
    assert plan.relationships or plan.group_by or plan.filters or plan.limit or len(plan.tables) > 1


@pytest.mark.asyncio
@pytest.mark.parametrize("query", COMPLEX_QUERIES)
async def test_complex_queries(query):
    planner = AIQueryPlanner()
    plan = await planner.plan(query)
    assert isinstance(plan, ExecutionPlan)
    assert plan.confidence >= 0.70
    assert len(plan.tables) >= 1
    # Complex queries must be decomposed into logical tasks
    assert plan.decomposition is not None
    assert len(plan.decomposition) >= 1
