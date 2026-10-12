from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ev_chargeops.database import SessionLocal, initialize_database
from ev_chargeops.services import (
    analyze_month,
    billing_summary,
    close_month,
    get_close,
    list_anomalies,
    list_competences,
    month_sessions,
    review_anomaly,
    seed_demo,
    session_payload,
)


app = FastAPI(
    title="EV ChargeOps API",
    description="API de demonstração para sessões, revisão de anomalias e rateio reconciliado.",
    version="0.1.0",
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup():
    initialize_database()
    with SessionLocal() as db:
        seed_demo(db)


class ReviewRequest(BaseModel):
    decision: Literal["aprovada", "rejeitada"]


def anomaly_payload(anomaly):
    return {
        "id": anomaly.id,
        "sessao_id": anomaly.session_id,
        "tipo": anomaly.kind,
        "score": anomaly.score,
        "explicacao": anomaly.explanation,
        "decisao": anomaly.decision,
        "unidade": anomaly.session.unit.name if anomaly.session.unit else "Não atribuída",
        "competencia": anomaly.session.competence,
    }


@app.get("/health")
def health():
    return {"status": "ok", "servico": "EV ChargeOps"}


@app.get("/competencias")
def competences(db: Session = Depends(get_db)):
    return {"competencias": list_competences(db)}


@app.get("/sessoes")
def sessions(competencia: str, db: Session = Depends(get_db)):
    if competencia not in list_competences(db):
        raise HTTPException(status_code=404, detail="Competência não encontrada.")
    return [session_payload(row) for row in month_sessions(db, competencia)]


@app.post("/anomalias/analisar")
def analyze(competencia: str, db: Session = Depends(get_db)):
    if competencia not in list_competences(db):
        raise HTTPException(status_code=404, detail="Competência não encontrada.")
    return [anomaly_payload(row) for row in analyze_month(db, competencia)]


@app.get("/anomalias")
def anomalies(competencia: str, db: Session = Depends(get_db)):
    if competencia not in list_competences(db):
        raise HTTPException(status_code=404, detail="Competência não encontrada.")
    return [anomaly_payload(row) for row in list_anomalies(db, competencia)]


@app.post("/anomalias/{anomaly_id}/revisao")
def review(anomaly_id: int, request: ReviewRequest, db: Session = Depends(get_db)):
    try:
        anomaly = review_anomaly(db, anomaly_id, request.decision)
        return anomaly_payload(anomaly)
    except Exception as error:
        raise HTTPException(status_code=404, detail="Anomalia não encontrada ou decisão inválida.") from error


@app.get("/fechamento/{competencia}/previa")
def billing_preview(competencia: str, db: Session = Depends(get_db)):
    try:
        result, reason = billing_summary(db, competencia)
    except Exception as error:
        raise HTTPException(status_code=404, detail="Competência não encontrada.") from error
    if reason:
        raise HTTPException(status_code=409, detail=reason)
    return {
        "competencia": competencia,
        "tarifa_efetiva_rs_kwh": str(result.tariff_rs_kwh),
        "energia_sessoes_kwh": str(result.session_energy_kwh),
        "energia_carregador_kwh": str(result.charger_energy_kwh),
        "divergencia_percentual": str(result.delta_percent),
        "total_rs": str(result.total_rs),
        "faturas": [
            {
                "unidade": invoice.unit_id,
                "energia_rs": str(invoice.energy_rs),
                "ajuste_rs": str(invoice.adjustment_rs),
                "fixo_rs": str(invoice.fixed_rs),
                "ociosidade_rs": str(invoice.idle_rs),
                "total_rs": str(invoice.total_rs),
            }
            for invoice in result.invoices
        ],
    }


@app.post("/fechamento/{competencia}")
def finalize(competencia: str, db: Session = Depends(get_db)):
    existing = get_close(db, competencia)
    if existing:
        raise HTTPException(status_code=409, detail="Esta competência já foi fechada.")
    try:
        close, result = close_month(db, competencia)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {
        "id": close.id,
        "competencia": competencia,
        "total_rs": str(result.total_rs),
        "faturas_geradas": len(result.invoices),
    }


@app.get("/fechamento/{competencia}")
def closed_invoices(competencia: str, db: Session = Depends(get_db)):
    close = get_close(db, competencia)
    if close is None:
        raise HTTPException(status_code=404, detail="Competência ainda não fechada.")
    return {
        "competencia": competencia,
        "total_rs": close.total_rs,
        "faturas": [
            {"unidade": item.unit.name, "energia_kwh": item.energy_kwh, "total_rs": item.total_rs}
            for item in close.invoices
        ],
    }