#!/usr/bin/env python3
"""Uma fila de tarefas com SQLite. Sem Redis, sem Celery, sem servidor.

    python main.py enfileira "enviar e-mail" --dados '{"para": "ana@exemplo.com"}'
    python main.py trabalha
    python main.py status

Serve para o caso mais comum de todos: um processo produz trabalho, outro
consome, e os dois cabem na mesma máquina.
"""
import argparse
import json
import sqlite3
import time
from pathlib import Path

BANCO = Path("fila.db")

ESQUEMA = """
create table if not exists tarefas (
  id        integer primary key,
  tipo      text not null,
  dados     text not null default '{}',
  estado    text not null default 'pendente'
            check (estado in ('pendente','processando','feita','falhou')),
  tentativas integer not null default 0,
  erro      text,
  criada_em real not null,
  pega_em   real
);
create index if not exists tarefas_pendentes on tarefas (estado, id);
"""


def conectar():
    c = sqlite3.connect(BANCO, isolation_level=None)
    c.row_factory = sqlite3.Row
    # WAL deixa um leitor e um escritor trabalharem ao mesmo tempo. Sem ele,
    # o worker trava o status e vice-versa.
    c.execute("pragma journal_mode=wal")
    c.executescript(ESQUEMA)
    return c


def pegar_uma(c):
    """Reivindica UMA tarefa, sem que dois workers peguem a mesma.

    `begin immediate` tranca a escrita antes do select. Sem isso, dois
    processos leem a mesma linha 'pendente' e os dois a marcam -- a tarefa roda
    duas vezes, e é sempre a de enviar e-mail.
    """
    c.execute("begin immediate")
    linha = c.execute(
        "select * from tarefas where estado='pendente' order by id limit 1").fetchone()
    if not linha:
        c.execute("commit")
        return None
    c.execute("update tarefas set estado='processando', tentativas=tentativas+1,"
              " pega_em=? where id=?", (time.time(), linha["id"]))
    c.execute("commit")
    return linha


def executar(tarefa):
    """Aqui entra o seu trabalho de verdade."""
    print(f"  [{tarefa['id']}] {tarefa['tipo']} {tarefa['dados']}")
    time.sleep(0.2)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enfileira"); e.add_argument("tipo"); e.add_argument("--dados", default="{}")
    t = sub.add_parser("trabalha"); t.add_argument("--max", type=int, default=0)
    sub.add_parser("status")
    a = ap.parse_args()

    c = conectar()
    if a.cmd == "enfileira":
        json.loads(a.dados)  # falha agora se o JSON estiver torto, não no worker
        cur = c.execute("insert into tarefas (tipo, dados, criada_em) values (?,?,?)",
                        (a.tipo, a.dados, time.time()))
        print(f"tarefa {cur.lastrowid} enfileirada")

    elif a.cmd == "trabalha":
        feitas = 0
        while True:
            tarefa = pegar_uma(c)
            if not tarefa:
                if a.max:
                    break
                time.sleep(0.5)
                continue
            try:
                executar(tarefa)
                c.execute("update tarefas set estado='feita' where id=?", (tarefa["id"],))
            except Exception as exc:
                destino = "falhou" if tarefa["tentativas"] >= 3 else "pendente"
                c.execute("update tarefas set estado=?, erro=? where id=?",
                          (destino, str(exc)[:300], tarefa["id"]))
            feitas += 1
            if a.max and feitas >= a.max:
                break
        print(f"{feitas} tarefa(s) processadas")

    else:
        for linha in c.execute("select estado, count(*) n from tarefas group by estado"):
            print(f"  {linha['estado']:12} {linha['n']}")


if __name__ == "__main__":
    main()
