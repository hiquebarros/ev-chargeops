import pandas as pd
import streamlit as st

from ev_chargeops.database import SessionLocal, initialize_database
from ev_chargeops.models import MonthlyAccount
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
)
from ev_chargeops.ui import apply_theme, bar_chart, footer, hero, sidebar_brand


st.set_page_config(page_title="EV ChargeOps", page_icon="⚡", layout="wide")
apply_theme()


def brl(value):
    return "R$ {:,.2f}".format(float(value)).replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_resource
def initialize():
    initialize_database()
    with SessionLocal() as db:
        seed_demo(db)


initialize()
sidebar_brand("Gestão de recarga compartilhada", "app.py")

with SessionLocal() as db:
    competences = list_competences(db)

if not competences:
    st.error("Nenhuma competência disponível.")
    st.stop()

competence = st.sidebar.selectbox("Competência", competences, index=0)
st.sidebar.markdown("---")
st.sidebar.markdown("<span class='fiap-tag'>Protótipo</span>", unsafe_allow_html=True)
st.sidebar.caption("Dados sintéticos. A integração GoodWe SEMS ainda não foi habilitada.")

if st.session_state.get("analyzed_competence") != competence:
    with SessionLocal() as db:
        analyze_month(db, competence)
    st.session_state["analyzed_competence"] = competence

hero(
    None,
    "Centro de",
    "operação",
    "Consumo, anomalias e fechamento mensal da recarga compartilhada.",
)

with SessionLocal() as db:
    account = db.query(MonthlyAccount).filter_by(competence=competence).one()
    sessions = month_sessions(db, competence)
    anomalies = list_anomalies(db, competence)
    pending_count = sum(1 for anomaly in anomalies if anomaly.decision == "pendente")
    close_record = get_close(db, competence)
    summary, block_reason = billing_summary(db, competence)

    metric_one, metric_two, metric_three, metric_four = st.columns(4)
    metric_one.metric("Energia do carregador", "{:,.1f} kWh".format(account.charger_energy_kwh).replace(",", "X").replace(".", ",").replace("X", "."))
    metric_two.metric("Sessões", len(sessions))
    metric_three.metric("Anomalias pendentes", pending_count, delta="Revisão necessária" if pending_count else "Pronto para fechar", delta_color="inverse" if pending_count else "normal")
    metric_four.metric("Status do mês", "Fechado" if close_record else ("Em revisão" if pending_count else "Pronto"))

    tabs = st.tabs(["Resumo", "Anomalias", "Sessões e faturas"])

    with tabs[0]:
        left, right = st.columns([1.45, 1])
        with left:
            st.subheader("Consumo por unidade")
            unit_data = {}
            for session in sessions:
                if session.unit:
                    unit_data[session.unit.name] = unit_data.get(session.unit.name, 0) + session.energy_kwh
            consumption = pd.DataFrame(
                sorted(unit_data.items(), key=lambda row: row[1], reverse=True),
                columns=["Unidade", "Energia (kWh)"],
            )
            bar_chart(consumption, "Unidade", "Energia (kWh)")
        with right:
            st.subheader("Fechamento mensal")
            st.metric("Tarifa efetiva", brl(account.bill_value_rs / account.bill_energy_kwh) + "/kWh")
            st.metric("Conta da área comum", brl(account.bill_value_rs))
            if close_record:
                st.success("Fechamento concluído em " + close_record.closed_at.strftime("%d/%m/%Y %H:%M"))
                st.metric("Total rateado", brl(close_record.total_rs))
            elif block_reason:
                st.warning(block_reason)
            else:
                st.success("Dados consistentes. Competência liberada para fechamento.")
            st.markdown("<div class='fiap-note'>Fonte: simulação determinística · HCA G2 7 kW</div>", unsafe_allow_html=True)

        st.subheader("Atividade recente")
        recent = sorted(sessions, key=lambda row: row.started_at, reverse=True)[:8]
        st.dataframe(pd.DataFrame([{
            "Início": row.started_at.strftime("%d/%m %H:%M"),
            "Unidade": row.unit.name if row.unit else "Não atribuída",
            "Energia": "%.1f kWh" % row.energy_kwh,
            "Ociosidade": "%d min" % row.idle_minutes,
            "Status": "Rejeitada" if row.status == "rejeitada" else "Concluída",
        } for row in recent]), hide_index=True, use_container_width=True)

    with tabs[1]:
        head, button_col = st.columns([4, 1])
        with head:
            st.subheader("Fila de revisão")
            st.caption("A validação combina limite físico de potência e duração com Isolation Forest. Alertas pendentes bloqueiam a emissão de faturas.")
        with button_col:
            if st.button("Reanalisar", icon=":material/refresh:", use_container_width=True):
                analyze_month(db, competence)
                st.rerun()

        if not anomalies:
            st.success("Nenhuma anomalia identificada nesta competência.")
        for anomaly in anomalies:
            with st.container(border=True):
                session = anomaly.session
                col_info, col_score, col_decision = st.columns([3.6, 1.3, 1.6])
                col_info.markdown("**%s · %s**" % (anomaly.kind.replace("_", " ").title(), session.unit.name if session.unit else "Não atribuída"))
                col_info.caption("%s · %.1f kWh em %d min · %s" % (session.id, session.energy_kwh, session.charge_minutes, anomaly.explanation))
                col_score.metric(
                    "Suspeita",
                    "%.2f" % anomaly.score,
                    help="Indicador heurístico, não representa uma probabilidade calibrada.",
                )
                if anomaly.decision == "pendente":
                    with col_decision:
                        if st.button("Aprovar", key="approve-%s" % anomaly.id, help="Aceitar a sessão após revisão", use_container_width=True):
                            review_anomaly(db, anomaly.id, "aprovada")
                            st.rerun()
                        if st.button("Rejeitar", key="reject-%s" % anomaly.id, help="Excluir a sessão do rateio", use_container_width=True):
                            review_anomaly(db, anomaly.id, "rejeitada")
                            st.rerun()
                else:
                    col_decision.markdown("**%s**" % anomaly.decision.title())

    with tabs[2]:
        st.subheader("Sessões da competência")
        session_data = [{
            "Sessão": row.id,
            "Início": row.started_at.strftime("%d/%m/%Y %H:%M"),
            "Unidade": row.unit.name if row.unit else "Não atribuída",
            "Credencial": row.credential_id,
            "Energia (kWh)": row.energy_kwh,
            "Carregando (min)": row.charge_minutes,
            "Ocioso (min)": row.idle_minutes,
            "Status": "Rejeitada" if row.status == "rejeitada" else row.status.title(),
        } for row in sessions]
        sessions_frame = pd.DataFrame(session_data)
        st.dataframe(sessions_frame, hide_index=True, use_container_width=True, height=330)
        st.download_button(
            "Exportar sessões CSV",
            data=sessions_frame.to_csv(index=False).encode("utf-8"),
            file_name="sessoes-%s.csv" % competence,
            mime="text/csv",
        )

        st.subheader("Memória de cálculo")
        if close_record:
            invoice_rows = [{
                "Unidade": invoice.unit.name,
                "Energia": "%.2f kWh" % invoice.energy_kwh,
                "Consumo": brl(invoice.energy_rs),
                "Reconciliação": brl(invoice.adjustment_rs),
                "Custo fixo": brl(invoice.fixed_rs),
                "Ociosidade": brl(invoice.idle_rs),
                "Total": brl(invoice.total_rs),
            } for invoice in close_record.invoices]
            st.dataframe(pd.DataFrame(invoice_rows), hide_index=True, use_container_width=True)
            st.download_button(
                "Exportar faturas CSV",
                data=pd.DataFrame(invoice_rows).to_csv(index=False).encode("utf-8"),
                file_name="faturas-%s.csv" % competence,
                mime="text/csv",
            )
        elif block_reason:
            st.warning(block_reason)
        else:
            col_calc, col_close = st.columns([3, 1])
            col_calc.markdown("**Energia reconciliada:** %s kWh × %s = %s" % (
                "%.2f" % account.charger_energy_kwh,
                brl(account.bill_value_rs / account.bill_energy_kwh),
                brl(account.charger_energy_kwh * account.bill_value_rs / account.bill_energy_kwh),
            ))
            col_calc.caption("Custos fixos: %s · taxa de ociosidade: %s/h após %d min · divergência: %.2f%%" % (
                brl(account.fixed_cost_rs), brl(account.idle_rate_rs_hour), account.idle_grace_minutes,
                float(summary.delta_percent) if summary else 0,
            ))
            if col_close.button("Fechar competência", type="primary", use_container_width=True):
                try:
                    close_month(db, competence)
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

footer("EV ChargeOps · <span>FIAP × GoodWe</span> · protótipo acadêmico com valores e sessões simulados")