"""Testes OFFLINE da FSM da Aula 2.

A grande vantagem de modelar o agente como grafo: as decisões de fluxo são
funções puras. Dá para testar TODAS as rotas sem gastar um token sequer.
"""

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from opspilot import grafo as g


def test_rota_por_categoria():
    assert g.rota_por_categoria({"messages": [], "categoria": "incidente"}) == "investigar"
    assert g.rota_por_categoria({"messages": [], "categoria": "duvida"}) == "responder_duvida"
    assert g.rota_por_categoria({"messages": [], "categoria": "fora_escopo"}) == "recusar"
    assert g.rota_por_categoria({"messages": []}) == "recusar"  # default seguro


def test_rota_investigacao_ciclo():
    com_ferramenta = AIMessage("", tool_calls=[{"name": "ler_logs", "args": {}, "id": "1"}])
    assert g.rota_investigacao({"messages": [com_ferramenta]}) == "ferramentas"
    assert g.rota_investigacao({"messages": [AIMessage("diagnóstico pronto")]}) == "validar"


def test_rota_validacao_erro_e_retry():
    base = {"messages": [], "erros_validacao": ["faltam evidências"]}
    assert g.rota_validacao({**base, "tentativas": 1}) == "investigar"
    assert g.rota_validacao({**base, "tentativas": g.MAX_TENTATIVAS}) == "escalar_humano"


def test_rota_validacao_sucesso():
    ok = {"messages": [], "erros_validacao": [], "tentativas": 1}
    assert g.rota_validacao({**ok, "diagnostico": {"severidade": "SEV1"}}) == "aprovar_ticket"
    assert g.rota_validacao({**ok, "diagnostico": {"severidade": "SEV3"}}) == "responder"


def test_evidencia_ancorada_detecta_alucinacao():
    saidas = "pgbouncer restart: default_pool_size=10 (antes: 50)"
    assert g.evidencia_ancorada("default_pool_size=10 no pgbouncer", saidas)
    assert not g.evidencia_ancorada("CPU do banco em 97%", saidas)  # número inventado


def test_validar_diagnostico():
    saidas = "default_pool_size=10 ... PoolTimeout within 3000ms"
    bom = g.Diagnostico(
        servico_causa_raiz="pagamentos-db",
        causa_raiz="Pool reduzido de 50 para 10",
        evidencias=["default_pool_size=10", "PoolTimeout em 3000ms"],
        acao_recomendada="Reverter config",
        severidade="SEV1",
    )
    assert g.validar_diagnostico(bom, saidas) == []

    ruim = bom.model_copy(update={"servico_causa_raiz": "banco", "evidencias": ["CPU 99%"]})
    problemas = g.validar_diagnostico(ruim, saidas)
    assert len(problemas) == 3  # serviço inexistente, <2 evidências, evidência não ancorada


def test_pergunta_original_ignora_feedback_do_validador():
    estado = {"messages": [HumanMessage("checkout lento"), HumanMessage("[VALIDADOR] refaça")]}
    assert g._pergunta_original(estado) == "checkout lento"


def test_grafo_compila_com_todos_os_nos():
    """Montar o grafo não chama o LLM — dá para validar a estrutura no CI."""
    compilado = g.construir_grafo(aprovacao_humana=True, checkpointer=InMemorySaver())
    nos = set(compilado.get_graph().nodes)
    esperados = {"classificar", "investigar", "ferramentas", "validar", "aprovar_ticket", "abrir_ticket", "responder","notificar_canal"}
    assert esperados <= nos


def test_grafo_sem_aprovacao_nao_tem_interrupt():
    compilado = g.construir_grafo(aprovacao_humana=False)
    assert "aprovar_ticket" not in set(compilado.get_graph().nodes)
