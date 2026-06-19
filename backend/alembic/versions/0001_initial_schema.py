"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-06-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    user_role = postgresql.ENUM('ADMIN', 'USER', name='userrole', create_type=False)
    user_role.create(op.get_bind(), checkfirst=True)
    
    emp_status = postgresql.ENUM('ACTIVE', 'TERMINATED', 'LEAVE', name='employeestatus', create_type=False)
    emp_status.create(op.get_bind(), checkfirst=True)
    
    proj_status = postgresql.ENUM('PLANNED', 'ACTIVE', 'COMPLETED', 'CANCELLED', name='projectstatus', create_type=False)
    proj_status.create(op.get_bind(), checkfirst=True)
    
    leave_type = postgresql.ENUM('SICK', 'VACATION', 'PERSONAL', name='leavetype', create_type=False)
    leave_type.create(op.get_bind(), checkfirst=True)
    
    leave_status = postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', name='leavestatus', create_type=False)
    leave_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', user_role, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_table(
        'search_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('natural_language', sa.Text(), nullable=False),
        sa.Column('structured_json', postgresql.JSONB(), nullable=True),
        sa.Column('generated_sql', sa.Text(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_search_history_user_id'), 'search_history', ['user_id'], unique=False)

    op.create_table(
        'saved_queries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('natural_language', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_saved_queries_user_id'), 'saved_queries', ['user_id'], unique=False)

    op.create_table(
        'offices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('city', sa.String(length=255), nullable=False),
        sa.Column('country', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'departments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('budget', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    op.create_table(
        'employees',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('office_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=False),
        sa.Column('last_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hire_date', sa.Date(), nullable=False),
        sa.Column('status', emp_status, nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['office_id'], ['offices.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employees_department_id'), 'employees', ['department_id'], unique=False)
    op.create_index(op.f('ix_employees_office_id'), 'employees', ['office_id'], unique=False)
    op.create_index(op.f('ix_employees_email'), 'employees', ['email'], unique=True)
    op.create_index(op.f('ix_employees_last_name'), 'employees', ['last_name'], unique=False)

    op.create_table(
        'clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('industry', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clients_name'), 'clients', ['name'], unique=True)

    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', proj_status, nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_client_id'), 'projects', ['client_id'], unique=False)
    op.create_index(op.f('ix_projects_start_date'), 'projects', ['start_date'], unique=False)

    op.create_table(
        'project_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=255), nullable=False),
        sa.Column('allocation_percentage', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'project_id', name='uq_emp_proj'),
        sa.CheckConstraint('allocation_percentage >= 0 AND allocation_percentage <= 100', name='chk_allocation')
    )
    op.create_index(op.f('ix_project_assignments_employee_id'), 'project_assignments', ['employee_id'], unique=False)
    op.create_index(op.f('ix_project_assignments_project_id'), 'project_assignments', ['project_id'], unique=False)

    op.create_table(
        'attendance',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('hours_worked', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'date', name='uq_emp_date'),
        sa.CheckConstraint('hours_worked >= 0 AND hours_worked <= 24', name='chk_hours')
    )
    op.create_index(op.f('ix_attendance_employee_id'), 'attendance', ['employee_id'], unique=False)
    op.create_index(op.f('ix_attendance_date'), 'attendance', ['date'], unique=False)

    op.create_table(
        'payroll',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('base_salary', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('bonus', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payroll_employee_id'), 'payroll', ['employee_id'], unique=False)
    op.create_index(op.f('ix_payroll_period_start'), 'payroll', ['period_start'], unique=False)

    op.create_table(
        'leave_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('leave_type', leave_type, nullable=False),
        sa.Column('status', leave_status, nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leave_requests_employee_id'), 'leave_requests', ['employee_id'], unique=False)

    op.create_table(
        'performance_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('review_date', sa.Date(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['employees.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('score >= 1 AND score <= 5', name='chk_score')
    )
    op.create_index(op.f('ix_performance_reviews_employee_id'), 'performance_reviews', ['employee_id'], unique=False)
    op.create_index(op.f('ix_performance_reviews_reviewer_id'), 'performance_reviews', ['reviewer_id'], unique=False)

    op.create_table(
        'skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skills_name'), 'skills', ['name'], unique=True)

    op.create_table(
        'employee_skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('proficiency_level', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'skill_id', name='uq_emp_skill'),
        sa.CheckConstraint('proficiency_level >= 1 AND proficiency_level <= 5', name='chk_proficiency')
    )
    op.create_index(op.f('ix_employee_skills_employee_id'), 'employee_skills', ['employee_id'], unique=False)
    op.create_index(op.f('ix_employee_skills_skill_id'), 'employee_skills', ['skill_id'], unique=False)


def downgrade():
    op.drop_table('employee_skills')
    op.drop_table('skills')
    op.drop_table('performance_reviews')
    op.drop_table('leave_requests')
    op.drop_table('payroll')
    op.drop_table('attendance')
    op.drop_table('project_assignments')
    op.drop_table('projects')
    op.drop_table('clients')
    op.drop_table('employees')
    op.drop_table('departments')
    op.drop_table('offices')
    op.drop_table('saved_queries')
    op.drop_table('search_history')
    op.drop_table('users')

    postgresql.ENUM(name='userrole').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='employeestatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='projectstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='leavetype').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='leavestatus').drop(op.get_bind(), checkfirst=True)
