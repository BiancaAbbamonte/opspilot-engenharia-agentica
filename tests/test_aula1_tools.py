"""Testes OFFLINE das ferramentas (não chamam o LLM; rodam no CI sem chave).

Ferramentas são código comum: devem ter testes comuns. Repare que testamos
inclusive o caminho de ERRO — é ele que permite a autocorreção do agente.
"""

import json
from datetime import UTC, datetime, timedelta

from opspilot import tools


def test_consultar_metricas_servico_valido():
    saida = json.loads(tools.consultar_metricas.invoke({"servico": "pagamentos-db"}))
    assert saida["conexoes_max_pool"] == 10
    assert saida["baseline_conexoes_max_pool"] == 50


def test_consultar_metricas_erro_vira_observacao():
    saida = tools.consultar_metricas.invoke({"servico": "checkout"})
    assert saida.startswith("ERRO")
    assert "checkout-api" in saida  # lista os nomes válidos para o agente se corrigir


def test_ler_logs_com_filtro():
    saida = tools.ler_logs.invoke({"servico": "pagamentos-db", "filtro": "pool_size"})
    assert "default_pool_size=10" in saida


def test_ler_logs_limita_linhas():
    saida = tools.ler_logs.invoke({"servico": "checkout-api", "max_linhas": 3})
    assert len(saida.splitlines()) == 3


def test_buscar_runbook_encontra_pool():
    saida = tools.buscar_runbook.invoke({"consulta": "pool de conexões esgotado"})
    assert "banco-conexoes-esgotadas.md" in saida


def test_abrir_ticket_grava_arquivo(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "DIR_TICKETS", tmp_path)
    saida = tools.abrir_ticket.invoke(
        {"titulo": "Teste", "servico": "pagamentos-db", "severidade": "SEV2", "resumo": "teste"}
    )
    assert "aberto" in saida
    assert len(list(tmp_path.glob("OPS-*.json"))) == 1


def test_schema_da_ferramenta_tem_descricao():
    """O LLM só usa bem o que entende: docstring e parâmetros precisam chegar no schema."""
    schema = tools.consultar_metricas.args
    assert "servico" in schema
    assert "métricas" in tools.consultar_metricas.description.lower()


def test_listar_deploys_filtra_e_ordena_logs(tmp_path, monkeypatch):
    agora = datetime.now(UTC)
    horario_recente = agora.replace(microsecond=0)
    horario_anterior = (horario_recente - timedelta(minutes=20)).isoformat()
    horario_antigo = (horario_recente - timedelta(hours=8)).isoformat()
    linha_recente = f"{horario_recente.isoformat()} INFO deploy recente"
    linha_anterior = f"{horario_anterior} INFO deploy anterior"
    (tmp_path / "checkout.log").write_text(f"{linha_recente}\n", encoding="utf-8")
    (tmp_path / "pagamentos.log").write_text(
        f"{horario_antigo} INFO deploy antigo\n"
        f"{linha_anterior}\n"
        f"{horario_recente.isoformat()} INFO sem alteracao\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(tools, "DIR_LOGS", tmp_path)

    saida = tools.listar_deploys.invoke({"horas": 6})

    assert saida.splitlines() == [linha_anterior, linha_recente]


def test_listar_deploys_sem_resultados_na_janela(tmp_path, monkeypatch):
    (tmp_path / "checkout.log").write_text(
        "2026-10-12T17:55:00Z INFO deploy antigo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(tools, "DIR_LOGS", tmp_path)

    saida = tools.listar_deploys.invoke({"horas": 6})

    assert saida == "Nenhum deploy encontrado nos logs nas últimas 6 horas."
