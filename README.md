# EV ChargeOps

Protótipo de gestão de recarga compartilhada desenvolvido para o Enterprise Challenge 2026 (FIAP × GoodWe). O fluxo registra sessões por unidade, valida dados com IA, bloqueia o fechamento para revisão humana e calcula faturas reconciliadas com a conta da distribuidora.

> [!IMPORTANT]
> ### ▶ Vídeo de demonstração do protótipo
> **[Assista no YouTube: https://youtu.be/hKh16p0JQUs](https://youtu.be/hKh16p0JQUs)**
>
> Percurso completo: painel do gestor, fila de anomalias da IA, revisão humana, fechamento da competência e portal do morador.

## Equipe

| Nome | RM | Curso |
|---|---|---|
| Henrique Schardosim de Barros | RM 572304 | Ciência da Computação (On-Line) |

Nome da equipe: Grupo 11

## Executar

Requer Python 3.9 ou superior. Python 3.11 é a versão prevista na pesquisa da Sprint 1.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

O banco SQLite é criado em `data/ev_chargeops_prototype.db`. Na primeira execução, são geradas 900 sessões sintéticas, distribuídas por dez unidades entre abril e setembro de 2026. A semente aleatória é fixa para manter a demonstração reproduzível.

Para abrir a API em outro terminal:

```bash
source .venv/bin/activate
uvicorn ev_chargeops.api:app --reload
```

Documentação interativa da API: <http://127.0.0.1:8000/docs>.

Para executar os testes:

```bash
python -m unittest discover -s tests -v
```

## Fluxo implementado

1. O adaptador de demonstração fornece sessões no modelo normalizado previsto na Sprint 1. Cada registro guarda unidade, credencial, horários, energia e ociosidade.
2. O detector combina limite físico (potência × duração) com Isolation Forest. O modelo faz a triagem, e só vira alerta a sessão que também está muito fora do padrão do mês em alguma medida concreta (desvio robusto acima de 3,5). Assim, meses normais não geram alertas e o gestor revisa poucos casos. Suspeitas ficam em uma fila persistente; nenhuma prévia de cobrança ou fechamento é liberada enquanto houver anomalias pendentes.
3. O gestor aprova uma sessão após revisão ou a rejeita, removendo-a do rateio.
4. A tarifa efetiva é o valor da conta dividido pelo consumo da área comum. Energia medida pelo carregador, diferença de reconciliação, custos fixos e ociosidade são apresentados separadamente por unidade.
5. Diferenças acima de 5% bloqueiam o fechamento. Custos fixos são divididos apenas entre unidades ativas; a ociosidade só é cobrada após carência de 30 minutos.
6. O fechamento grava as faturas e sua memória de cálculo no SQLite. Sessões e faturas podem ser exportadas em CSV.

O dashboard Streamlit oferece as interfaces do gestor e do morador. O morador seleciona sua unidade e vê apenas suas sessões e memória de cálculo. A API FastAPI expõe competências, sessões, análise/revisão de anomalias, prévia e fechamento. A API também fornece documentação OpenAPI.

## Decisões e limites do protótipo

- **Banco:** SQLite, como previsto para o protótipo local. `DATABASE_URL` pode apontar para PostgreSQL sem alterar as entidades, mas isso não faz parte desta demonstração.
- **Dados:** todos os carregamentos exibidos são sintéticos. A API GoodWe SEMS é restrita e depende de credenciais e autorização do parceiro; nenhum dado real do HCA G2 foi recebido ou presumido.
- **Acesso:** o portal de morador filtra os dados pela unidade escolhida na tela, mas não implementa autenticação. Não usar com dados pessoais nem como controle de acesso em produção.
- **IA estrutural:** o detector de anomalias é portão do faturamento, com regra física e Isolation Forest; a decisão final sobre alertas é humana. O conjunto sintético inclui uma sessão fisicamente impossível para demonstrar a fila.
- **Desvios do plano Sprint 1:** a integração SEMS/Modbus/OCPP ainda não foi implementada, pois faltam acesso, mapa de registradores e confirmação de suporte do HCA G2. A previsão de consumo e os perfis K-Means (IA 2 e IA 3) não fazem parte desta primeira versão; priorizamos a IA 1, necessária para evitar faturamento de dados suspeitos. Os resultados desta versão devem ser entendidos como demonstração com dados simulados, não como validação metrológica ou operacional do carregador real.
- **Rateio:** replica a fórmula documentada na Sprint 1: o medidor do carregador distribui o custo real; não há margem nem alegação de medição certificada.

## Estrutura

```text
app.py                 Portal do gestor em Streamlit
pages/                 Portal individual do morador
ev_chargeops/api.py    API FastAPI
ev_chargeops/ai.py     Detector de anomalias
ev_chargeops/billing.py Motor de rateio
ev_chargeops/models.py Entidades SQLAlchemy
ev_chargeops/services.py Simulador e fluxo de negócio
data/                  Banco SQLite local (ignorado pelo Git)
tests/                 Testes de cálculo, fechamento e detecção de anomalias
```