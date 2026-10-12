from typing import Dict, List

import numpy as np
from sklearn.ensemble import IsolationForest

from ev_chargeops.models import ChargingSessionRecord


FEATURE_LABELS = ["energia", "duração da recarga", "potência média", "ociosidade", "horário de início"]
# Desvio robusto (mediana/MAD) a partir do qual uma medida é considerada muito fora do padrão do condomínio.
ROBUST_Z_LIMIT = 3.5


def robust_z_scores(values: np.ndarray) -> np.ndarray:
    median = np.median(values, axis=0)
    mad = np.median(np.abs(values - median), axis=0) * 1.4826
    mad[mad == 0] = np.inf
    return (values - median) / mad


def detect_anomalies(sessions: List[ChargingSessionRecord]) -> List[Dict[str, object]]:
    if not sessions:
        return []

    features = []
    for session in sessions:
        average_power = session.energy_kwh / (session.charge_minutes / 60) if session.charge_minutes else 0
        features.append([
            session.energy_kwh,
            session.charge_minutes,
            average_power,
            session.idle_minutes,
            session.started_at.hour,
        ])
    matrix = np.asarray(features, dtype=float)

    # O Isolation Forest faz a triagem; o alerta só é emitido se a sessão também estiver muito fora
    # do padrão em alguma medida concreta. Isso evita que o modelo aponte sempre os "menos comuns"
    # de um mês normal e mantém a fila de revisão curta.
    model_flags = [False] * len(sessions)
    model_scores = [0.0] * len(sessions)
    deviations = np.zeros_like(matrix)
    if len(sessions) >= 8:
        model = IsolationForest(contamination=0.08, random_state=42, n_estimators=200)
        predictions = model.fit_predict(matrix)
        model_scores = [-float(score) for score in model.decision_function(matrix)]
        deviations = robust_z_scores(matrix)
        model_flags = [
            prediction == -1 and bool(np.any(np.abs(deviation) > ROBUST_Z_LIMIT))
            for prediction, deviation in zip(predictions, deviations)
        ]

    findings = []
    for index, session in enumerate(sessions):
        physical_limit = session.charger_power_kw * session.charge_minutes / 60 * 1.15
        physically_impossible = session.energy_kwh > physical_limit
        if physically_impossible:
            kind = "energia_acima_do_fisico"
            explanation = (
                "Energia informada excede em mais de 15% o máximo compatível com "
                "a potência e o tempo da sessão."
            )
            score = min(0.99, session.energy_kwh / max(physical_limit, 0.01) - 1)
        elif model_flags[index]:
            kind = "perfil_atipico"
            outliers = [
                "%s %s do padrão" % (label, "muito acima" if value > 0 else "muito abaixo")
                for label, value in zip(FEATURE_LABELS, deviations[index])
                if abs(value) > ROBUST_Z_LIMIT
            ]
            explanation = "Sessão atípica para o condomínio: " + ", ".join(outliers) + "."
            score = min(0.99, max(0.51, model_scores[index]))
        else:
            continue
        findings.append({
            "session_id": session.id,
            "kind": kind,
            "score": score,
            "explanation": explanation,
        })
    return findings
