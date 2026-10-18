"""Deixa o FTP enviar só o que mudou.

O build regrava todos os arquivos a cada rodada, então todos parecem "novos" para o lftp. Este script guarda
o hash e a data de cada arquivo publicado (.deploy/manifesto.json, mantido pelo cache do GitHub Actions):
arquivo com o mesmo conteúdo da última publicação volta a ter a data antiga, e o `mirror -R` o ignora.

Uso: uv run ferramentas/preparar_deploy.py
"""
import hashlib
import json
import os
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITE = RAIZ / "entrega" / "1-site-para-publicar"
MANIFESTO = RAIZ / ".deploy" / "manifesto.json"

antigo = json.loads(MANIFESTO.read_text(encoding="utf-8")) if MANIFESTO.exists() else {}
novo, iguais, agora = {}, 0, int(time.time())
for arq in SITE.rglob("*"):
    if not arq.is_file():
        continue
    rel = arq.relative_to(SITE).as_posix()
    h = hashlib.sha1(arq.read_bytes()).hexdigest()
    if rel in antigo and antigo[rel][0] == h:
        os.utime(arq, (antigo[rel][1], antigo[rel][1]))
        novo[rel] = antigo[rel]
        iguais += 1
    else:
        os.utime(arq, (agora, agora))
        novo[rel] = [h, agora]
MANIFESTO.parent.mkdir(exist_ok=True)
MANIFESTO.write_text(json.dumps(novo), encoding="utf-8")
print(f"{len(novo)} arquivos · {len(novo) - iguais} mudaram desde a última publicação")
