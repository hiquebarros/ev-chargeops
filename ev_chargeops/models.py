from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Unit(Base):
    __tablename__ = "unidades"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    sessions = relationship("ChargingSessionRecord", back_populates="unit")


class ChargingSessionRecord(Base):
    __tablename__ = "sessoes"

    id = Column(String, primary_key=True)
    competence = Column(String, nullable=False, index=True)
    unit_id = Column(String, ForeignKey("unidades.id"), nullable=True, index=True)
    credential_id = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    charge_minutes = Column(Integer, nullable=False)
    idle_minutes = Column(Integer, nullable=False, default=0)
    energy_kwh = Column(Float, nullable=False)
    charger_power_kw = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="concluida")
    source = Column(String, nullable=False, default="simulador")
    unit = relationship("Unit", back_populates="sessions")
    anomaly = relationship("AnomalyRecord", back_populates="session", uselist=False)


class MonthlyAccount(Base):
    __tablename__ = "contas_mensais"

    competence = Column(String, primary_key=True)
    bill_value_rs = Column(Float, nullable=False)
    bill_energy_kwh = Column(Float, nullable=False)
    charger_energy_kwh = Column(Float, nullable=False)
    fixed_cost_rs = Column(Float, nullable=False)
    idle_grace_minutes = Column(Integer, nullable=False, default=30)
    idle_rate_rs_hour = Column(Float, nullable=False, default=5.0)


class AnomalyRecord(Base):
    __tablename__ = "anomalias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessoes.id"), nullable=False, unique=True)
    kind = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    explanation = Column(String, nullable=False)
    decision = Column(String, nullable=False, default="pendente")
    reviewed_at = Column(DateTime, nullable=True)
    session = relationship("ChargingSessionRecord", back_populates="anomaly")


class MonthlyClose(Base):
    __tablename__ = "fechamentos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competence = Column(String, nullable=False, unique=True)
    total_rs = Column(Float, nullable=False)
    closed_at = Column(DateTime, nullable=False, server_default=func.now())
    invoices = relationship("InvoiceRecord", back_populates="close", cascade="all, delete-orphan")


class InvoiceRecord(Base):
    __tablename__ = "faturas"
    __table_args__ = (UniqueConstraint("close_id", "unit_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    close_id = Column(Integer, ForeignKey("fechamentos.id"), nullable=False)
    unit_id = Column(String, ForeignKey("unidades.id"), nullable=False)
    energy_kwh = Column(Float, nullable=False)
    energy_rs = Column(Float, nullable=False)
    adjustment_rs = Column(Float, nullable=False)
    fixed_rs = Column(Float, nullable=False)
    idle_rs = Column(Float, nullable=False)
    total_rs = Column(Float, nullable=False)
    close = relationship("MonthlyClose", back_populates="invoices")
    unit = relationship("Unit")