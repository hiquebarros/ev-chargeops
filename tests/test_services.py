import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ev_chargeops.models import AnomalyRecord, Base, ChargingSessionRecord, MonthlyAccount, Unit
from ev_chargeops.services import billing_summary, close_month, review_anomaly


class BillingWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.db.add(Unit(id="U01", name="Unidade 101"))
        self.db.add(MonthlyAccount(
            competence="2026-09",
            bill_value_rs=100,
            bill_energy_kwh=100,
            charger_energy_kwh=10,
            fixed_cost_rs=0,
            idle_grace_minutes=30,
            idle_rate_rs_hour=5,
        ))
        self.db.add(ChargingSessionRecord(
            id="S-01",
            competence="2026-09",
            unit_id="U01",
            credential_id="RFID-U01",
            started_at=datetime(2026, 9, 1, 8),
            charge_minutes=90,
            idle_minutes=90,
            energy_kwh=9.7,
            charger_power_kw=7,
        ))
        self.db.flush()
        self.db.add(AnomalyRecord(
            session_id="S-01",
            kind="perfil_atipico",
            score=0.8,
            explanation="Alerta sintético para teste de fluxo.",
        ))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_pending_anomaly_blocks_close_until_human_review(self):
        summary, reason = billing_summary(self.db, "2026-09")
        self.assertIsNone(summary)
        self.assertIn("bloqueado", reason)

        review_anomaly(self.db, 1, "aprovada")
        summary, reason = billing_summary(self.db, "2026-09")
        self.assertIsNone(reason)
        self.assertTrue(summary.close_allowed)
        self.assertEqual(str(summary.total_rs), "15.00")

        close, _ = close_month(self.db, "2026-09")
        self.assertEqual(close.competence, "2026-09")
        self.assertEqual(len(close.invoices), 1)
        self.assertEqual(close.invoices[0].total_rs, 15.0)


if __name__ == "__main__":
    unittest.main()