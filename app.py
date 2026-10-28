"""
Coroinhas · Basílica Nossa Senhora de Lourdes (Vila Isabel).

Cada área é um blueprint em `projetos/<projeto>/` (mesmo padrão do portal de Planejamento).
Para adicionar um projeto novo: crie o pacote com `bp` e `PROJETO` e inclua-o em MODULOS abaixo.

Execução:
    pip install -r requirements.txt
    python app.py criar-usuario marcus     # uma vez: cria o 1º coordenador (os outros são criados em "Minha conta")
    python app.py                          # http://127.0.0.1:5000
"""
from __future__ import annotations

import getpass
import os
import secrets
import sys
from datetime import datetime, timedelta

from flask import Flask, jsonify, redirect, request, url_for

import acesso
from projetos import coroinhas

# Projetos do sistema (o primeiro abre ao entrar)
MODULOS = [coroinhas]
PROJETOS = [m.PROJETO for m in MODULOS]


def _chave_secreta() -> str:
    """SECRET_KEY do ambiente; senão uma chave gerada e guardada em dados/ (fora do git)."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    arq = acesso.DADOS / "secret_key"
    if not arq.exists():
        arq.write_text(secrets.token_hex(32))
    return arq.read_text().strip()


app = Flask(__name__)
app.config.update(
    SECRET_KEY=_chave_secreta(),
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,                         # 10 MB por arquivo
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SEGURO") == "1",  # ligue quando o site estiver em HTTPS
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)
app.json.ensure_ascii = False
app.register_blueprint(acesso.bp)
for m in MODULOS:
    app.register_blueprint(m.bp)
acesso.proteger(app)


@app.context_processor
def _ctx():
    return {"ano": datetime.now().year, "projetos": PROJETOS, "projeto_atual": request.blueprint}


@app.get("/")
def inicio():
    return redirect(url_for(PROJETOS[0]["endpoint"]))


@app.errorhandler(413)
def muito_grande(_):
    return jsonify({"erro": "Arquivo muito grande (limite de 10 MB)."}), 413


def _criar_usuario(login: str) -> None:
    nome = input("Nome para exibir: ").strip() or login
    while True:
        senha = getpass.getpass("Senha (mín. 8 caracteres): ")
        if len(senha) < 8:
            print("Senha curta demais.")
        elif senha != getpass.getpass("Repita a senha: "):
            print("As senhas não conferem.")
        else:
            break
    acesso.usuarios.salvar(login, nome, senha, coordenador=True)
    print(f'Coordenador "{login.lower()}" pronto. Agora rode: python app.py (as outras contas são criadas em "Minha conta")')


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "criar-usuario":
        _criar_usuario(sys.argv[2])
    elif len(sys.argv) > 1:
        print(__doc__)
    else:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, threaded=True)
