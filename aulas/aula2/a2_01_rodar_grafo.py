"""Aula 2 · Exercício 1 — Rodar a FSM, pausar na aprovação e RETOMAR depois.

O ponto alto desta aula: o estado fica salvo em SQLite (``.checkpoints.sqlite``).
Você pode responder "depois", FECHAR o terminal e retomar mais tarde com o mesmo
``--thread``. Isso é persistência de verdade — o mesmo mecanismo que permite
agentes de longa duração em produção.

Como rodar::

    # 1) inicia uma investigação (thread nova)
    python -m aulas.aula2.a2_01_rodar_grafo --thread inc-2041

    # 2) se respondeu "depois", retome quando quiser:
    python -m aulas.aula2.a2_01_rodar_grafo --thread inc-2041 --retomar sim

    # outros testes de rota
    python -m aulas.aula2.a2_01_rodar_grafo --thread t2 --pergunta "Como renovo o certificado TLS?"
    python -m aulas.aula2.a2_01_rodar_grafo --thread t3 --pergunta "Qual o melhor time do Brasileirão?"
"""

from __future__ import annotations

import argparse
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from opspilot.config import ARQ_CHECKPOINTS, LIMITE_RECURSAO
from opspilot.grafo import construir_grafo
from opspilot.util import imprimir_passo

PERGUNTA_PADRAO = "O checkout está lento e dando erro 503 desde as 18h. Investigue."


def executar(grafo, entrada, config) -> dict:
    """Roda o grafo em modo streaming, imprimindo cada mensagem nova e o nó ativo."""
    estado_final: dict = {}
    vistas = 0
    for evento in grafo.stream(entrada, config=config, stream_mode=["updates", "values"]):
        modo, dados = evento
        if modo == "updates":
            for no in dados:
                if no != "__interrupt__":
                    print(f"   ⚙️  nó executado: {no}")
        else:  # values
            estado_final = dados
            mensagens = dados.get("messages", [])
            for m in mensagens[vistas:]:
                imprimir_passo(m)
            vistas = len(mensagens)
    return estado_final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pergunta", default=PERGUNTA_PADRAO)
    parser.add_argument("--thread", default="inc-2041", help="ID da conversa (chave da persistência)")
    parser.add_argument("--retomar", choices=["sim", "nao"], help="Retoma uma thread pausada com essa decisão")
    args = parser.parse_args()

    # check_same_thread=False: o LangGraph pode acessar a conexão de outra thread.
    conexao = sqlite3.connect(ARQ_CHECKPOINTS, check_same_thread=False)
    grafo = construir_grafo(aprovacao_humana=True, checkpointer=SqliteSaver(conexao))
    config = {"configurable": {"thread_id": args.thread}, "recursion_limit": LIMITE_RECURSAO}

    if args.retomar:
        print(f"▶️  Retomando thread '{args.thread}' com decisão: {args.retomar}")
        entrada = Command(resume=args.retomar)
    else:
        entrada = {"messages": [{"role": "user", "content": args.pergunta}]}

    executar(grafo, entrada, config)

    # Se o grafo parou num interrupt, o snapshot mostra o que está pendente.
    snapshot = grafo.get_state(config)
    while snapshot.next and snapshot.interrupts:  # há nós pendentes por causa de um interrupt
        pendente = snapshot.interrupts[0].value  # o dicionário que passamos ao interrupt()
        print("\n⏸️  GRAFO PAUSADO aguardando humano")
        print(f"   {pendente['pergunta']}")
        for chave, valor in pendente["rascunho"].items():
            print(f"   • {chave}: {valor}")
        decisao = input("\nSua decisão [sim / nao / depois]: ").strip().lower() or "depois"
        if decisao == "depois":
            print(
                "\n💾 Estado salvo em .checkpoints.sqlite. Para retomar (até em outro terminal):\n"
                f"   python -m aulas.aula2.a2_01_rodar_grafo --thread {args.thread} --retomar sim"
            )
            return
        executar(grafo, Command(resume=decisao), config)
        snapshot = grafo.get_state(config)

    tentativas = snapshot.values.get("tentativas")
    print(f"\n🏁 Fim. Categoria: {snapshot.values.get('categoria')} | tentativas de validação: {tentativas}")


if __name__ == "__main__":
    main()
