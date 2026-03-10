from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from db.models import Employee, EmployeeAccess, LifecycleRun, User


def init_db(engine) -> None:
    from db.session import Base
    Base.metadata.create_all(bind=engine)


def get_or_create_employee(
    db: Session,
    *,
    name: str,
    email: str,
    manager_email: str,
    role: str,
    department: str | None = None,
) -> Employee:
    employee = db.query(Employee).filter(Employee.email == email).first()

    if employee:
        employee.name = name
        employee.manager_email = manager_email
        employee.role = role
        employee.department = department
        employee.updated_at = datetime.utcnow()
    else:
        employee = Employee(
            name=name,
            email=email,
            manager_email=manager_email,
            role=role,
            department=department,
        )
        db.add(employee)
        db.flush()

    return employee


def update_employee_status(db: Session, employee: Employee, action: str) -> None:
    if action == "offboard":
        employee.employment_status = "inactive"
        employee.lifecycle_status = "offboarded"
    else:
        employee.employment_status = "active"
        employee.lifecycle_status = "onboarded"

    employee.updated_at = datetime.utcnow()


def sync_access(db: Session, employee: Employee, access_payload: dict | None, action: str) -> None:
    if not isinstance(access_payload, dict):
        return

    systems = access_payload.get("systems", {})
    if not isinstance(systems, dict):
        return

    for system_name, raw_status in systems.items():
        row = (
            db.query(EmployeeAccess)
            .filter(
                EmployeeAccess.employee_id == employee.id,
                EmployeeAccess.system_name == system_name,
            )
            .first()
        )

        normalized = str(raw_status).lower()
        if normalized == "granted":
            access_status = "granted"
        elif normalized == "revoked":
            access_status = "revoked"
        elif normalized == "failed":
            access_status = "failed"
        else:
            access_status = "pending"

        if row:
            row.access_status = access_status
            row.last_updated = datetime.utcnow()
        else:
            db.add(
                EmployeeAccess(
                    employee_id=employee.id,
                    system_name=system_name,
                    access_status=access_status,
                    last_updated=datetime.utcnow(),
                )
            )


def create_lifecycle_run(
    db: Session,
    *,
    employee: Employee,
    result: dict,
    initiated_by: str | None = None,
    initiator_role: str | None = None,
) -> LifecycleRun:
    access = result.get("access", {}) if isinstance(result.get("access"), dict) else {}
    run = LifecycleRun(
        employee_id=employee.id,
        action=result.get("action", "unknown"),
        status=result.get("status", "completed"),
        audit_id=access.get("audit_id"),
        run_path=result.get("stored_at"),
        initiated_by=initiated_by,
        initiator_role=initiator_role,
        created_at=datetime.utcnow(),
    )
    db.add(run)
    db.flush()
    return run


def persist_workflow_result(
    db: Session,
    *,
    result: dict,
    initiated_by: str | None = None,
    initiator_role: str | None = None,
) -> None:
    employee = get_or_create_employee(
        db,
        name=result.get("name", "Unknown"),
        email=result.get("email", "unknown@company.com"),
        manager_email=result.get("manager_email", "manager@company.com"),
        role=result.get("role", "Employee"),
    )

    action = result.get("action", "onboard")
    update_employee_status(db, employee, action)
    sync_access(db, employee, result.get("access"), action)
    create_lifecycle_run(
        db,
        employee=employee,
        result=result,
        initiated_by=initiated_by,
        initiator_role=initiator_role,
    )

    db.commit()


def get_dashboard(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 10,
    search: str | None = None,
    status: str | None = None,
    role: str | None = None,
) -> dict:
    page = max(page, 1)
    page_size = max(1, min(page_size, 50))

    query = db.query(Employee)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Employee.name.ilike(term),
                Employee.email.ilike(term),
                Employee.manager_email.ilike(term),
            )
        )

    if status:
        query = query.filter(Employee.employment_status == status)

    if role:
        query = query.filter(Employee.role == role)

    total_filtered = query.count()

    employees = (
        query.order_by(Employee.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    total_all = db.query(func.count(Employee.id)).scalar() or 0
    active_count = db.query(func.count(Employee.id)).filter(Employee.employment_status == "active").scalar() or 0
    inactive_count = db.query(func.count(Employee.id)).filter(Employee.employment_status == "inactive").scalar() or 0

    out = []
    for e in employees:
        access_map = {a.system_name: a.access_status for a in e.accesses}

        granted = sum(1 for v in access_map.values() if v == "granted")
        revoked = sum(1 for v in access_map.values() if v == "revoked")
        total_access = len(access_map)

        out.append(
            {
                "id": e.id,
                "name": e.name,
                "email": e.email,
                "manager_email": e.manager_email,
                "role": e.role,
                "department": e.department,
                "employment_status": e.employment_status,
                "lifecycle_status": e.lifecycle_status,
                "created_at": e.created_at.isoformat() + "Z",
                "updated_at": e.updated_at.isoformat() + "Z",
                "access": access_map,
                "access_summary": {
                    "total": total_access,
                    "granted": granted,
                    "revoked": revoked,
                },
            }
        )

    return {
        "summary": {
            "total": total_all,
            "active": active_count,
            "inactive": inactive_count,
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_filtered": total_filtered,
            "total_pages": (total_filtered + page_size - 1) // page_size,
        },
        "employees": out,
    }


def get_distinct_roles(db: Session) -> list[str]:
    rows = db.query(Employee.role).distinct().order_by(Employee.role.asc()).all()
    return [r[0] for r in rows if r[0]]


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(
    db: Session,
    *,
    name: str,
    email: str,
    role: str = "employee",
    is_active: bool = True,
) -> User:
    user = User(
        name=name,
        email=email,
        role=role,
        is_active=is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_active_employees_tool(db: Session) -> list[dict]:
    employees = (
        db.query(Employee)
        .filter(Employee.employment_status == "active")
        .order_by(Employee.name.asc())
        .all()
    )
    return [
        {
            "name": e.name,
            "email": e.email,
            "role": e.role,
            "manager_email": e.manager_email,
            "employment_status": e.employment_status,
            "lifecycle_status": e.lifecycle_status,
        }
        for e in employees
    ]


def list_inactive_employees_tool(db: Session) -> list[dict]:
    employees = (
        db.query(Employee)
        .filter(Employee.employment_status == "inactive")
        .order_by(Employee.name.asc())
        .all()
    )
    return [
        {
            "name": e.name,
            "email": e.email,
            "role": e.role,
            "manager_email": e.manager_email,
            "employment_status": e.employment_status,
            "lifecycle_status": e.lifecycle_status,
        }
        for e in employees
    ]


def get_employee_access_tool(db: Session, employee_name: str) -> dict:
    employee = db.query(Employee).filter(Employee.name.ilike(employee_name)).first()
    if not employee:
        return {"found": False, "employee_name": employee_name}

    return {
        "found": True,
        "name": employee.name,
        "email": employee.email,
        "role": employee.role,
        "employment_status": employee.employment_status,
        "lifecycle_status": employee.lifecycle_status,
        "access": {a.system_name: a.access_status for a in employee.accesses},
    }


def get_employee_status_tool(db: Session, employee_name: str) -> dict:
    employee = db.query(Employee).filter(Employee.name.ilike(employee_name)).first()
    if not employee:
        return {"found": False, "employee_name": employee_name}

    return {
        "found": True,
        "name": employee.name,
        "email": employee.email,
        "role": employee.role,
        "employment_status": employee.employment_status,
        "lifecycle_status": employee.lifecycle_status,
        "manager_email": employee.manager_email,
    }