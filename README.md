# fila-no-sqlite

Fila de tarefas durável com SQLite, sem Redis e sem Celery

Código do carrossel publicado no [@python_brasil](https://instagram.com/python_brasil).

## Como rodar

```bash
python main.py --help
```

```bash
python main.py enfileira "enviar email" --dados '{"para":"ana@exemplo.com"}'
python main.py trabalha
python main.py status
```

## O que este código NÃO faz

- um escritor por vez: para dezenas de workers distribuídos, use Redis ou Postgres
- não agenda tarefa para o futuro, só enfileira

---

Feito pela comunidade [@python_brasil](https://instagram.com/python_brasil).
