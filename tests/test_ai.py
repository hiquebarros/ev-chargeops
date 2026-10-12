import random
import unittest
from datetime import datetime
from types import SimpleNamespace

from ev_chargeops.ai import detect_anomalies


def normal_month(count=150, seed=7):
    rng = random.Random(seed)
    sessions = []
    for index in range(count):
        energy = round(rng.uniform(12, 31), 2)
        sessions.append(SimpleNamespace(
            id="S-%03d" % index,
            energy_kwh=energy,
            charge_minutes=max(20, round(energy / rng.uniform(5.2, 6.6) * 60)),
            idle_minutes=rng.choice([0, 8, 20, 35, 45, 60, 95]),
            started_at=datetime(2026, 9, 1 + index % 28, rng.randint(7, 18)),
            charger_power_kw=7.0,
        ))
    return sessions


class AnomalyDetectionTests(unittest.TestCase):
    def test_normal_month_raises_no_alerts(self):
        self.assertEqual(detect_anomalies(normal_month()), [])

    def test_flags_only_the_physically_impossible_session(self):
        sessions = normal_month()
        sessions[10].energy_kwh = 42.0
        sessions[10].charge_minutes = 60

        findings = detect_anomalies(sessions)

        self.assertEqual([finding["session_id"] for finding in findings], ["S-010"])
        self.assertEqual(findings[0]["kind"], "energia_acima_do_fisico")

    def test_flags_atypical_session_that_is_physically_possible(self):
        sessions = normal_month()
        sessions[20].energy_kwh = 55.0
        sessions[20].charge_minutes = 480

        findings = detect_anomalies(sessions)

        self.assertEqual([finding["session_id"] for finding in findings], ["S-020"])
        self.assertEqual(findings[0]["kind"], "perfil_atipico")
        self.assertIn("energia muito acima", findings[0]["explanation"])


if __name__ == "__main__":
    unittest.main()
