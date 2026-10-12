from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, List, Optional


CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ChargingSession:
    session_id: str
    unit_id: Optional[str]
    energy_kwh: Decimal
    idle_minutes: int = 0
    status: str = "concluida"


@dataclass(frozen=True)
class UnitInvoice:
    unit_id: str
    energy_kwh: Decimal
    energy_rs: Decimal
    adjustment_rs: Decimal
    fixed_rs: Decimal
    idle_rs: Decimal
    total_rs: Decimal


@dataclass(frozen=True)
class BillingSummary:
    tariff_rs_kwh: Decimal
    session_energy_kwh: Decimal
    charger_energy_kwh: Decimal
    delta_kwh: Decimal
    delta_percent: Decimal
    close_allowed: bool
    blocking_reason: Optional[str]
    invoices: List[UnitInvoice]
    total_rs: Decimal


def calculate_billing(
    sessions: Iterable[ChargingSession],
    bill_value_rs: Decimal,
    bill_energy_kwh: Decimal,
    charger_energy_kwh: Decimal,
    fixed_cost_rs: Decimal,
    idle_grace_minutes: int = 30,
    idle_rate_rs_hour: Decimal = Decimal("5.00"),
    delta_limit_percent: Decimal = Decimal("5.00"),
) -> BillingSummary:
    values = (bill_value_rs, bill_energy_kwh, charger_energy_kwh, fixed_cost_rs, idle_rate_rs_hour)
    if any(value < 0 for value in values) or bill_energy_kwh == 0:
        raise ValueError("Valores da conta, medidor e custos devem ser positivos; consumo da conta não pode ser zero.")
    if idle_grace_minutes < 0:
        raise ValueError("A carência de ociosidade não pode ser negativa.")

    eligible = [session for session in sessions if session.status in {"concluida", "reconstruida"}]
    if any(session.energy_kwh < 0 or session.idle_minutes < 0 for session in eligible):
        raise ValueError("Energia e ociosidade das sessões não podem ser negativas.")

    tariff = bill_value_rs / bill_energy_kwh
    assigned: Dict[str, Decimal] = {}
    idle_by_unit: Dict[str, Decimal] = {}
    for session in eligible:
        if not session.unit_id:
            continue
        assigned[session.unit_id] = assigned.get(session.unit_id, Decimal("0")) + session.energy_kwh
        billable_minutes = max(0, session.idle_minutes - idle_grace_minutes)
        idle_by_unit[session.unit_id] = idle_by_unit.get(session.unit_id, Decimal("0")) + (
            Decimal(billable_minutes) / Decimal(60) * idle_rate_rs_hour
        )

    session_energy = sum(assigned.values(), Decimal("0"))
    delta = charger_energy_kwh - session_energy
    delta_percent = abs(delta) / charger_energy_kwh * Decimal("100") if charger_energy_kwh else Decimal("0")
    if delta_percent > delta_limit_percent:
        return BillingSummary(
            tariff_rs_kwh=tariff,
            session_energy_kwh=session_energy,
            charger_energy_kwh=charger_energy_kwh,
            delta_kwh=delta,
            delta_percent=delta_percent,
            close_allowed=False,
            blocking_reason="Divergência entre o medidor e as sessões acima do limite de 5%.",
            invoices=[],
            total_rs=Decimal("0.00"),
        )
    if not assigned:
        return BillingSummary(
            tariff_rs_kwh=tariff,
            session_energy_kwh=session_energy,
            charger_energy_kwh=charger_energy_kwh,
            delta_kwh=delta,
            delta_percent=delta_percent,
            close_allowed=False,
            blocking_reason="Não há sessões atribuídas a unidades para ratear o consumo.",
            invoices=[],
            total_rs=Decimal("0.00"),
        )

    active_units = sorted(assigned)
    raw_energy_target = money(charger_energy_kwh * tariff)
    energy_lines = {unit: money(assigned[unit] * tariff) for unit in active_units}
    adjustment_lines = {
        unit: money(delta * tariff * assigned[unit] / session_energy)
        for unit in active_units
    }
    energy_residual = raw_energy_target - sum(energy_lines.values()) - sum(adjustment_lines.values())
    adjustment_lines[active_units[0]] += energy_residual

    fixed_lines = {unit: money(fixed_cost_rs / len(active_units)) for unit in active_units}
    fixed_residual = money(fixed_cost_rs) - sum(fixed_lines.values())
    fixed_lines[active_units[0]] += fixed_residual

    raw_idle_total = sum(idle_by_unit.values(), Decimal("0"))
    idle_lines = {unit: money(idle_by_unit.get(unit, Decimal("0"))) for unit in active_units}
    idle_residual = money(raw_idle_total) - sum(idle_lines.values())
    idle_lines[active_units[0]] += idle_residual

    invoices = [
        UnitInvoice(
            unit_id=unit,
            energy_kwh=assigned[unit],
            energy_rs=energy_lines[unit],
            adjustment_rs=adjustment_lines[unit],
            fixed_rs=fixed_lines[unit],
            idle_rs=idle_lines[unit],
            total_rs=energy_lines[unit] + adjustment_lines[unit] + fixed_lines[unit] + idle_lines[unit],
        )
        for unit in active_units
    ]
    total = sum((invoice.total_rs for invoice in invoices), Decimal("0.00"))
    return BillingSummary(
        tariff_rs_kwh=tariff,
        session_energy_kwh=session_energy,
        charger_energy_kwh=charger_energy_kwh,
        delta_kwh=delta,
        delta_percent=delta_percent,
        close_allowed=True,
        blocking_reason=None,
        invoices=invoices,
        total_rs=total,
    )