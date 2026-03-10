from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Boolean
from db.session import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    manager_email: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(120))
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)

    employment_status: Mapped[str] = mapped_column(String(50), default="active")
    lifecycle_status: Mapped[str] = mapped_column(String(50), default="onboarded")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    accesses = relationship("EmployeeAccess", back_populates="employee", cascade="all, delete-orphan")
    runs = relationship("LifecycleRun", back_populates="employee", cascade="all, delete-orphan")


class EmployeeAccess(Base):
    __tablename__ = "employee_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    system_name: Mapped[str] = mapped_column(String(120))
    access_status: Mapped[str] = mapped_column(String(50), default="pending")
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="accesses")


class LifecycleRun(Base):
    __tablename__ = "lifecycle_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    action: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    audit_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    run_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    initiated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    initiator_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="runs")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(50), default="employee")  # employee, hr, admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)