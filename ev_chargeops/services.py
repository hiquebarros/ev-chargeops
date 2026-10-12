import calendar
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session, joinedload

from ev_chargeops.ai import detect_anomalies
from ev_chargeops.billing import ChargingSession, calculate_billing
from ev_chargeops.models import (
    AnomalyRecord,
    ChargingSessionRecord,
    InvoiceRecord,
    MonthlyAccount,
    MonthlyClose,
    Unit,
)


def list_competences(db: Session) -> List[str]:
    return [row[0] for row in db.query(MonthlyAccount.competence).order_by(MonthlyAccount.competence.desc()).all()]


def seed_demo(db: Session) -> None:
    if db.query(Unit).first():
        return

    rng = random.Random(20261012)
    units = [Unit(id="U%02d" % number, name="Unidade %03d" % (100 + number * 11)) for number in range(1, 11)]
    db.add_all(units)
    db.flush()

    for month in range(4, 10):
        competence = "2026-%02d" % month
        first_day = datetime(2026, month, 1)
        last_day = calendar.monthrange(2026, month)[1]
        month_sessions = []
        for week_number, week_start in enumerate(range(1, last_day + 1, 7), start=1):
            for unit in units:
                for slot in range(3):
                    day = min(last_day, week_start + rng.randint(0, 5))
                    started_at = datetime(2026, month, day, rng.randint(7, 18), rng.choice([0, 15, 30, 45]))
                    energy = round(rng.uniform(12, 31), 2)
                    average_power = rng.uniform(5.2, 6.6)
                    charge_minutes = max(20, round(energy / average_power * 60))
                    idle_minutes = rng.choice([0, 8, 20, 35, 45, 60, 95])
                    session_id = "%s-%s-W%02d-%d" % (competence, unit.id, week_number, slot + 1)
                    if month == 9 and unit.id == "U01" and week_number == 2 and slot == 0:
                        energy = 42.0
                        charge_minutes = 60
                    month_sessions.append(ChargingSessionRecord(
                        id=session_id,
                        competence=competence,
                        unit_id=unit.id,
                        credential_id="RFID-%s" % unit.id,
                        started_at=started_at,
                        charge_minutes=charge_minutes,
                        idle_minutes=idle_minutes,
                        energy_kwh=energy,
                        charger_power_kw=7.0,
                    ))
        db.add_all(month_sessions)
        db.flush()
        session_energy = sum(row.energy_kwh for row in month_sessions)
        charger_energy = round(session_energy / 0.978, 2)
        db.add(MonthlyAccount(
            competence=competence,
            bill_value_rs=4410.0,
            bill_energy_kwh=4200.0,
            charger_energy_kwh=charger_energy,
            fixed_cost_rs=90.0,
            idle_grace_minutes=30,
            idle_rate_rs_hour=5.0,
        ))
    db.commit()


def analyze_month(db: Session, competence: str) -> List[AnomalyRecord]:
    sessions = (
        db.query(ChargingSessionRecord)
        .filter(
            ChargingSessionRecord.competence == competence,
            ChargingSessionRecord.status != "rejeitada",
        )
        .order_by(ChargingSessionRecord.id)
        .all()
    )
    findings = detect_anomalies(sessions)
    flagged_ids = {finding["session_id"] for finding in findings}
    stale = (
        db.query(AnomalyRecord)
        .join(ChargingSessionRecord)
        .filter(
            ChargingSessionRecord.competence == competence,
            AnomalyRecord.decision == "pendente",
            ~AnomalyRecord.session_id.in_(flagged_ids),
        )
        .all()
    )
    for record in stale:
        db.delete(record)
    for finding in findings:
        record = db.query(AnomalyRecord).filter_by(session_id=finding["session_id"]).one_or_none()
        if record is None:
            db.add(AnomalyRecord(**finding))
        elif record.decision == "pendente":
            record.kind = str(finding["kind"])
            record.score = float(finding["score"])
            record.explanation = str(finding["explanation"])
    db.commit()
    return list_anomalies(db, competence)


def list_anomalies(db: Session, competence: str) -> List[AnomalyRecord]:
    return (
        db.query(AnomalyRecord)
        .join(ChargingSessionRecord)
        .options(joinedload(AnomalyRecord.session).joinedload(ChargingSessionRecord.unit))
        .filter(ChargingSessionRecord.competence == competence)
        .order_by(AnomalyRecord.decision, AnomalyRecord.score.desc())
        .all()
    )


def review_anomaly(db: Session, anomaly_id: int, decision: str) -> AnomalyRecord:
    if decision not in {"aprovada", "rejeitada"}:
        raise ValueError("Decisão deve ser aprovada ou rejeitada.")
    anomaly = db.query(AnomalyRecord).options(joinedload(AnomalyRecord.session)).filter_by(id=anomaly_id).one()
    anomaly.decision = decision
    anomaly.reviewed_at = datetime.now()
    if decision == "rejeitada":
        anomaly.session.status = "rejeitada"
    db.commit()
    return anomaly


def month_sessions(db: Session, competence: str) -> List[ChargingSessionRecord]:
    return (
        db.query(ChargingSessionRecord)
        .options(joinedload(ChargingSessionRecord.unit))
        .filter(ChargingSessionRecord.competence == competence)
        .order_by(ChargingSessionRecord.started_at)
        .all()
    )


def billing_summary(db: Session, competence: str):
    account = db.query(MonthlyAccount).filter_by(competence=competence).one()
    pending = (
        db.query(AnomalyRecord)
        .join(ChargingSessionRecord)
        .filter(
            ChargingSessionRecord.competence == competence,
            AnomalyRecord.decision == "pendente",
        )
        .count()
    )
    if pending:
        return None, "Fechamento bloqueado: %d anomalia(s) aguardam revisão humana." % pending

    records = month_sessions(db, competence)
    sessions = [ChargingSession(
        session_id=row.id,
        unit_id=row.unit_id,
        energy_kwh=Decimal(str(row.energy_kwh)),
        idle_minutes=row.idle_minutes,
        status=row.status,
    ) for row in records]
    result = calculate_billing(
        sessions=sessions,
        bill_value_rs=Decimal(str(account.bill_value_rs)),
        bill_energy_kwh=Decimal(str(account.bill_energy_kwh)),
        charger_energy_kwh=Decimal(str(account.charger_energy_kwh)),
        fixed_cost_rs=Decimal(str(account.fixed_cost_rs)),
        idle_grace_minutes=account.idle_grace_minutes,
        idle_rate_rs_hour=Decimal(str(account.idle_rate_rs_hour)),
    )
    if not result.close_allowed:
        return result, result.blocking_reason
    return result, None


def close_month(db: Session, competence: str) -> Tuple[MonthlyClose, object]:
    existing = db.query(MonthlyClose).filter_by(competence=competence).one_or_none()
    if existing:
        raise ValueError("Esta competência já foi fechada.")
    result, reason = billing_summary(db, competence)
    if reason:
        raise ValueError(reason)

    close = MonthlyClose(competence=competence, total_rs=float(result.total_rs))
    close.invoices = [InvoiceRecord(
        unit_id=invoice.unit_id,
        energy_kwh=float(invoice.energy_kwh),
        energy_rs=float(invoice.energy_rs),
        adjustment_rs=float(invoice.adjustment_rs),
        fixed_rs=float(invoice.fixed_rs),
        idle_rs=float(invoice.idle_rs),
        total_rs=float(invoice.total_rs),
    ) for invoice in result.invoices]
    db.add(close)
    db.commit()
    db.refresh(close)
    return close, result


def get_close(db: Session, competence: str):
    return (
        db.query(MonthlyClose)
        .options(joinedload(MonthlyClose.invoices).joinedload(InvoiceRecord.unit))
        .filter_by(competence=competence)
        .one_or_none()
    )


def session_payload(session: ChargingSessionRecord) -> Dict[str, object]:
    return {
        "id": session.id,
        "competencia": session.competence,
        "unidade": session.unit.name if session.unit else None,
        "credencial": session.credential_id,
        "inicio": session.started_at.isoformat(),
        "energia_kwh": session.energy_kwh,
        "minutos_carregando": session.charge_minutes,
        "minutos_ociosos": session.idle_minutes,
        "status": session.status,
        "origem": session.source,
    }