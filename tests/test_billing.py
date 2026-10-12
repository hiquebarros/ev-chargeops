import unittest
from decimal import Decimal

from ev_chargeops.billing import ChargingSession, calculate_billing


class BillingTests(unittest.TestCase):
    def test_reconciles_documented_example_and_excludes_inactive_unit(self):
        sessions = [
            ChargingSession("s1", "101", Decimal("140.0")),
            ChargingSession("s2", "204", Decimal("95.0"), idle_minutes=210),
            ChargingSession("s3", "307", Decimal("70.0")),
        ]
        result = calculate_billing(
            sessions,
            bill_value_rs=Decimal("4410"),
            bill_energy_kwh=Decimal("4200"),
            charger_energy_kwh=Decimal("312"),
            fixed_cost_rs=Decimal("90"),
        )

        self.assertTrue(result.close_allowed)
        self.assertEqual(result.tariff_rs_kwh, Decimal("1.05"))
        self.assertEqual(result.delta_kwh, Decimal("7.0"))
        self.assertEqual(result.total_rs, Decimal("432.60"))
        self.assertEqual(
            [invoice.total_rs for invoice in result.invoices],
            [Decimal("180.37"), Decimal("147.04"), Decimal("105.19")],
        )
        self.assertNotIn("410", [invoice.unit_id for invoice in result.invoices])

    def test_blocks_closing_when_meter_divergence_exceeds_five_percent(self):
        result = calculate_billing(
            [ChargingSession("s1", "101", Decimal("50"))],
            bill_value_rs=Decimal("100"),
            bill_energy_kwh=Decimal("100"),
            charger_energy_kwh=Decimal("100"),
            fixed_cost_rs=Decimal("0"),
        )

        self.assertFalse(result.close_allowed)
        self.assertIn("5%", result.blocking_reason)
        self.assertEqual(result.invoices, [])


if __name__ == "__main__":
    unittest.main()