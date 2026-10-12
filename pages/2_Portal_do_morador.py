import pandas as pd
import streamlit as st

from ev_chargeops.database import SessionLocal, initialize_database
from ev_chargeops.models import AnomalyRecord, ChargingSessionRecord, MonthlyAccount, Unit
from ev_chargeops.services import billing_summary, get_close, list_competences, seed_demo
from ev_chargeops.ui import apply_theme, footer, hero, sidebar_brand


st.set_page_config(page_title="EV ChargeOps · Morador", page_icon="⚡", layout="wide")
apply_theme()


def brl(value):
    return "R$ {:,.2f}".format(float(value)).replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_resource
def initialize():
    initialize_database()
    with SessionLocal() as db:
        seed_demo(db)


initialize()
sidebar_brand("Acesso individual do morador", "pages/2_Portal_do_morador.py")

with SessionLocal() as db:
    competences = list_competences(db)
    units = db.query(Unit).filter_by(active=True).order_by(Unit.name).all()

if not competences or not units:
    st.error("Não há dados disponíveis para esta competência.")
    st.stop()

competence = st.sidebar.selectbox("Competência", competences, index=0)
unit_name_to_id = {unit.name: unit.id for unit in units}
unit_name = st.sidebar.selectbox("Minha unidade", list(unit_name_to_id))
unit_id = unit_name_to_id[unit_name]

hero("Portal do morador · " + competence, "Minha unidade", unit_name.replace("Unidade ", ""), "Consumo individual e memória de cálculo da recarga compartilhada.")

with SessionLocal() as db:
    account = db.query(MonthlyAccount).filter_by(competence=competence).one()
    sessions = (
        db.query(ChargingSessionRecord)
        .filter_by(competence=competence, unit_id=unit_id)
        .order_by(ChargingSessionRecord.started_at.desc())
        .all()
    )
    pending_count = (
        db.query(AnomalyRecord)
        .join(ChargingSessionRecord)
        .filter(
            AnomalyRecord.decision == "pendente",
            ChargingSessionRecord.competence == competence,
        )
        .count()
    )
    closed = get_close(db, competence)
    invoice = next((row for row in closed.invoices if row.unit_id == unit_id), None) if closed else None

    energy_kwh = sum(row.energy_kwh for row in sessions if row.status != "rejeitada")
    metric_one, metric_two, metric_three = st.columns(3)
    metric_one.metric("Energia no mês", "%.1f kWh" % energy_kwh)
    metric_two.metric("Sessões", len(sessions))
    metric_three.metric("Ociosidade conectada", "%d min" % sum(row.idle_minutes for row in sessions))

    if invoice:
        st.success("Fatura fechada para %s." % competence)
        st.metric("Total da unidade", brl(invoice.total_rs))
        st.dataframe(pd.DataFrame([
            {"Componente": "Energia", "Valor": brl(invoice.energy_rs)},
            {"Componente": "Reconciliação do medidor", "Valor": brl(invoice.adjustment_rs)},
            {"Componente": "Custo fixo", "Valor": brl(invoice.fixed_rs)},
            {"Componente": "Ociosidade", "Valor": brl(invoice.idle_rs)},
            {"Componente": "Total", "Valor": brl(invoice.total_rs)},
        ]), hide_index=True, use_container_width=True)
    elif pending_count:
        st.warning("A competência está em revisão. A fatura ainda não foi emitida; o valor só ficará disponível após a análise das sessões suspeitas.")
    else:
        summary, reason = billing_summary(db, competence)
        if reason:
            st.warning("Fatura provisória indisponível: " + reason)
        else:
            unit_invoice = next((row for row in summary.invoices if row.unit_id == unit_id), None)
            if unit_invoice:
                st.info("Estimativa não final. O valor pode mudar até o fechamento da competência.")
                st.metric("Estimativa da unidade", brl(unit_invoice.total_rs))
                st.dataframe(pd.DataFrame([
                    {"Componente": "Energia", "Valor": brl(unit_invoice.energy_rs)},
                    {"Componente": "Reconciliação do medidor", "Valor": brl(unit_invoice.adjustment_rs)},
                    {"Componente": "Custo fixo", "Valor": brl(unit_invoice.fixed_rs)},
                    {"Componente": "Ociosidade", "Valor": brl(unit_invoice.idle_rs)},
                ]), hide_index=True, use_container_width=True)
            else:
                st.info("Nenhuma sessão atribuída a esta unidade nesta competência.")

    st.subheader("Minhas sessões")
    session_frame = pd.DataFrame([{
        "Início": row.started_at.strftime("%d/%m/%Y %H:%M"),
        "Energia": "%.2f kWh" % row.energy_kwh,
        "Carregando": "%d min" % row.charge_minutes,
        "Ocioso": "%d min" % row.idle_minutes,
        "Status": "Rejeitada" if row.status == "rejeitada" else row.status.title(),
    } for row in sessions])
    st.dataframe(session_frame, hide_index=True, use_container_width=True)
    st.download_button(
        "Exportar minhas sessões CSV",
        data=session_frame.to_csv(index=False).encode("utf-8"),
        file_name="minhas-sessoes-%s.csv" % competence,
        mime="text/csv",
    )

footer("Você vê somente os dados associados à unidade selecionada · <span>dados de demonstração sintéticos</span>")