"""
Login (sessão do Flask) e contas. Os usuários ficam em `dados/usuarios.db`. O primeiro coordenador é criado pelo terminal:

    python app.py criar-usuario marcus

Depois disso, coordenadores criam, editam e removem contas na tela "Minha conta"; cada um troca a própria senha lá.
"""
from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
from collections import defaultdict, deque
from contextlib import closing
from pathlib import Path
from urllib.parse import urlparse

from flask import Blueprint, abort, g, jsonify, make_response, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

DADOS = Path(os.environ.get("COROINHAS_DADOS") or Path(__file__).resolve().parent / "dados")
APK = os.environ.get("COROINHAS_APK") == "1"     # rodando dentro do app Android (pasta apk/): sem terminal para criar o 1º usuário

bp = Blueprint("acesso", __name__)

# Limite contra chute de senha: 10 erros por IP a cada 10 minutos
_JANELA, _MAX_ERROS = 600, 10
_erros: dict[str, deque] = defaultdict(deque)

SENHA_MIN = 8
_LOGIN_OK = re.compile(r"^[a-z0-9._-]{2,40}$")
PAPEIS = {
    "coordenacao": "Coordenador(a)",
    "cerimoniario": "Cerimoniário(a)",
    "coroinha": "Coroinha",
}


def _normalizar_papel(papel: str | None, coordenador: bool | None = None) -> tuple[str, bool]:
    if papel in PAPEIS:
        return papel, (papel == "coordenacao")
    eh_coord = bool(coordenador)
    return ("coordenacao" if eh_coord else "coroinha"), eh_coord


class ErroAcesso(Exception):
    """Erro de validação mostrado ao usuário (vira JSON 400)."""


def _marca(senha_hash: str) -> str:
    """Pedaço do hash guardado na sessão: trocar a senha derruba as sessões abertas com a senha antiga."""
    return senha_hash[-16:]


def _validar_senha(senha: str) -> str:
    if len(senha or "") < SENHA_MIN:
        raise ErroAcesso(f"A senha precisa ter pelo menos {SENHA_MIN} caracteres.")
    return senha


class Usuarios:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._lock, closing(self._con()) as con:
            con.execute("""CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT UNIQUE NOT NULL, nome TEXT NOT NULL, senha_hash TEXT NOT NULL,
                coordenador INTEGER NOT NULL DEFAULT 0, papel TEXT NOT NULL DEFAULT 'coroinha')""")
            colunas = {c["name"] for c in con.execute("PRAGMA table_info(usuarios)")}
            if "coordenador" not in colunas:
                # bancos antigos: quem já existia foi criado pelo terminal, ou seja, é da coordenação
                con.execute("ALTER TABLE usuarios ADD COLUMN coordenador INTEGER NOT NULL DEFAULT 0")
                con.execute("UPDATE usuarios SET coordenador = 1")
            if "papel" not in colunas:
                con.execute("ALTER TABLE usuarios ADD COLUMN papel TEXT NOT NULL DEFAULT 'coroinha'")
                con.execute("UPDATE usuarios SET papel = CASE WHEN coordenador = 1 THEN 'coordenacao' ELSE 'coroinha' END")
            con.commit()

    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=15)
        con.row_factory = sqlite3.Row
        return con

    @staticmethod
    def _publico(r: sqlite3.Row) -> dict:
        eh_coord = bool(r["coordenador"])
        papel_bruto = r["papel"] if "papel" in r.keys() else None
        papel = "coordenacao" if eh_coord else (papel_bruto if papel_bruto in ("cerimoniario", "coroinha") else "coroinha")
        return {
            "id": r["id"],
            "login": r["login"],
            "nome": r["nome"],
            "coordenador": eh_coord,
            "papel": papel,
            "papel_rotulo": PAPEIS[papel],
            "marca": _marca(r["senha_hash"]),
        }

    def salvar(self, login: str, nome: str, senha: str, coordenador: bool = True, papel: str | None = None) -> None:
        """Pelo terminal: cria o usuário ou troca nome/senha de quem já existe (como coordenador)."""
        papel_norm, eh_coord = _normalizar_papel(papel, coordenador)
        with self._lock, closing(self._con()) as con:
            con.execute("""INSERT INTO usuarios (login, nome, senha_hash, coordenador, papel) VALUES (?, ?, ?, ?, ?)
                           ON CONFLICT(login) DO UPDATE SET nome = excluded.nome, senha_hash = excluded.senha_hash,
                                                            coordenador = excluded.coordenador, papel = excluded.papel""",
                        (login.strip().lower(), nome.strip(), generate_password_hash(senha), int(eh_coord), papel_norm))
            con.commit()

    def verificar(self, login: str, senha: str) -> dict | None:
        with closing(self._con()) as con:
            r = con.execute("SELECT * FROM usuarios WHERE login = ?", (login.strip().lower(),)).fetchone()
        return self._publico(r) if r and check_password_hash(r["senha_hash"], senha) else None

    def obter(self, uid: int) -> dict | None:
        with closing(self._con()) as con:
            r = con.execute("SELECT * FROM usuarios WHERE id = ?", (uid,)).fetchone()
        return self._publico(r) if r else None

    def listar(self) -> list[dict]:
        with closing(self._con()) as con:
            rows = con.execute("SELECT * FROM usuarios ORDER BY coordenador DESC, nome COLLATE NOCASE").fetchall()
        return [{k: v for k, v in self._publico(r).items() if k != "marca"} for r in rows]

    def total(self) -> int:
        with closing(self._con()) as con:
            return con.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]

    # ---- pela tela "Minha conta" ou "Criar conta" (com validação)
    def criar(self, login: str, nome: str, senha: str, coordenador: bool = False, papel: str | None = None) -> dict:
        login, nome = (login or "").strip().lower(), (nome or "").strip()
        if not _LOGIN_OK.match(login):
            raise ErroAcesso("Usuário inválido: use de 2 a 40 letras minúsculas, números, ponto, hífen ou _ (sem espaços).")
        if not nome:
            raise ErroAcesso("Informe o nome.")
        _validar_senha(senha)
        papel_norm, eh_coord = _normalizar_papel(papel, coordenador)
        with self._lock, closing(self._con()) as con:
            try:
                cur = con.execute("INSERT INTO usuarios (login, nome, senha_hash, coordenador, papel) VALUES (?, ?, ?, ?, ?)",
                                  (login, nome[:120], generate_password_hash(senha), int(eh_coord), papel_norm))
            except sqlite3.IntegrityError:
                raise ErroAcesso(f'Já existe uma conta com o usuário "{login}".') from None
            con.commit()
        return self.obter(cur.lastrowid)

    def atualizar(self, uid: int, nome: str, coordenador: bool = False, senha: str | None = None, papel: str | None = None) -> None:
        nome = (nome or "").strip()
        if not nome:
            raise ErroAcesso("Informe o nome.")
        papel_norm, eh_coord = _normalizar_papel(papel, coordenador)
        with self._lock, closing(self._con()) as con:
            if senha:
                con.execute("UPDATE usuarios SET nome = ?, coordenador = ?, papel = ?, senha_hash = ? WHERE id = ?",
                            (nome[:120], int(eh_coord), papel_norm, generate_password_hash(_validar_senha(senha)), uid))
            else:
                con.execute("UPDATE usuarios SET nome = ?, coordenador = ?, papel = ? WHERE id = ?",
                            (nome[:120], int(eh_coord), papel_norm, uid))
            con.commit()

    def trocar_senha(self, uid: int, nova: str) -> None:
        with self._lock, closing(self._con()) as con:
            con.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (generate_password_hash(_validar_senha(nova)), uid))
            con.commit()

    def senha_confere(self, uid: int, senha: str) -> bool:
        with closing(self._con()) as con:
            r = con.execute("SELECT senha_hash FROM usuarios WHERE id = ?", (uid,)).fetchone()
        return bool(r) and check_password_hash(r["senha_hash"], senha or "")

    def remover(self, uid: int) -> None:
        with self._lock, closing(self._con()) as con:
            con.execute("DELETE FROM usuarios WHERE id = ?", (uid,))
            con.commit()


usuarios = Usuarios(DADOS / "usuarios.db")


def _bloqueado(ip: str) -> bool:
    fila = _erros[ip]
    while fila and fila[0] < time.monotonic() - _JANELA:
        fila.popleft()
    return len(fila) >= _MAX_ERROS


def _destino_seguro(url: str | None) -> str | None:
    """Só aceita caminhos do próprio site (evita redirecionar para outro domínio)."""
    return url if url and url.startswith("/") and not url.startswith("//") else None


def _logar(u: dict):
    session.clear()
    session["usuario_id"] = u["id"]
    session["marca"] = u["marca"]
    session.permanent = True
    return redirect(_destino_seguro(request.args.get("proximo")) or "/")


@bp.route("/entrar", methods=["GET", "POST"])
def entrar():
    erro = None
    sem_usuarios = usuarios.total() == 0
    primeira_vez = APK and sem_usuarios
    modo_criar = request.args.get("modo") == "criar" or (request.method == "POST" and request.form.get("acao") == "criar")
    if request.method == "POST" and (primeira_vez or modo_criar):
        f = request.form
        try:
            if f.get("senha", "") != f.get("repetir", ""):
                raise ErroAcesso("As senhas não conferem.")
            if sem_usuarios:
                # A 1ª conta criada no sistema é sempre Coordenador(a)
                u = usuarios.criar(f.get("login", ""), f.get("nome", ""), f.get("senha", ""), coordenador=True, papel="coordenacao")
            else:
                # As demais contas criadas na tela de login entram como Coroinha ou Cerimoniário (somente visualização)
                papel_escolhido = "cerimoniario" if f.get("papel") == "cerimoniario" else "coroinha"
                u = usuarios.criar(f.get("login", ""), f.get("nome", ""), f.get("senha", ""), coordenador=False, papel=papel_escolhido)
            return _logar(u)
        except ErroAcesso as e:
            erro = str(e)
    elif request.method == "POST":
        ip = request.remote_addr or "?"
        if _bloqueado(ip):
            erro = "Muitas tentativas. Espere alguns minutos."
        else:
            u = usuarios.verificar(request.form.get("login", ""), request.form.get("senha", ""))
            if u:
                return _logar(u)
            _erros[ip].append(time.monotonic())
            erro = "Usuário ou senha incorretos."
    return render_template("entrar.html", erro=erro, sem_usuarios=sem_usuarios, primeira_vez=primeira_vez,
                           modo_criar=modo_criar, senha_min=SENHA_MIN), 401 if erro else 200


@bp.post("/sair")
def sair():
    session.clear()
    return redirect(url_for("acesso.entrar"))


# ---------------------------------------------------------------- Minha conta / contas
@bp.errorhandler(ErroAcesso)
def _erro(e):
    return jsonify({"erro": str(e)}), 400


def _corpo() -> dict:
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        raise ErroAcesso("Requisição inválida.")
    return d


def _so_coordenador() -> None:
    if not g.usuario["coordenador"]:
        abort(make_response(jsonify({"erro": "Só a coordenação pode alterar contas."}), 403))


def _outra_conta(uid: int) -> dict:
    """Conta de outra pessoa que o coordenador quer alterar."""
    _so_coordenador()
    alvo = usuarios.obter(uid)
    if alvo is None:
        abort(make_response(jsonify({"erro": "Conta não encontrada."}), 404))
    if alvo["id"] == g.usuario["id"]:
        raise ErroAcesso("Você não pode remover a própria conta nem tirar o seu acesso de coordenador.")
    return alvo


@bp.get("/conta")
def conta():
    return render_template("conta.html", contas=usuarios.listar() if g.usuario["coordenador"] else [],
                           senha_min=SENHA_MIN, papeis=PAPEIS)


@bp.post("/conta/api/senha")
def trocar_senha():
    d = _corpo()
    if not usuarios.senha_confere(g.usuario["id"], d.get("atual", "")):
        raise ErroAcesso("A senha atual não confere.")
    usuarios.trocar_senha(g.usuario["id"], d.get("nova", ""))
    session["marca"] = usuarios.obter(g.usuario["id"])["marca"]    # continua logado aqui; sai dos outros aparelhos
    return jsonify({"ok": True})


@bp.post("/conta/api/usuarios")
def criar_conta():
    _so_coordenador()
    d = _corpo()
    u = usuarios.criar(d.get("login", ""), d.get("nome", ""), d.get("senha", ""), bool(d.get("coordenador")), d.get("papel"))
    return jsonify({"conta": {k: v for k, v in u.items() if k != "marca"}}), 201


@bp.put("/conta/api/usuarios/<int:uid>")
def editar_conta(uid: int):
    d = _corpo()
    if uid == g.usuario["id"]:              # a própria conta: aqui só muda o nome (senha é por /conta/api/senha)
        _so_coordenador()
        usuarios.atualizar(uid, d.get("nome", ""), True, papel="coordenacao")
        return jsonify({"ok": True})
    _outra_conta(uid)
    usuarios.atualizar(uid, d.get("nome", ""), bool(d.get("coordenador")), d.get("senha") or None, d.get("papel"))
    return jsonify({"ok": True})


@bp.delete("/conta/api/usuarios/<int:uid>")
def remover_conta(uid: int):
    _outra_conta(uid)
    usuarios.remover(uid)
    return jsonify({"ok": True})


def proteger(app) -> None:
    """Exige login em tudo, menos na tela de entrar e nos arquivos estáticos."""
    @app.before_request
    def _exigir_login():
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origem = request.headers.get("Origin")
            if origem and urlparse(origem).netloc != request.host:     # outro site tentando enviar dados
                return jsonify({"erro": "Origem não permitida."}), 403
        ep = request.endpoint or ""
        if ep == "acesso.entrar" or ep == "static" or ep.endswith(".static"):
            return None
        uid = session.get("usuario_id")
        g.usuario = usuarios.obter(uid) if uid else None
        if g.usuario and g.usuario.pop("marca") != session.get("marca"):   # senha trocada depois deste login
            g.usuario = None
            session.clear()
        if g.usuario is None:
            if "/api/" in request.path or request.path.startswith("/chat"):
                return jsonify({"erro": "Sua sessão expirou. Entre de novo."}), 401
            return redirect(url_for("acesso.entrar", proximo=request.full_path.rstrip("?")))
        return None

    @app.context_processor
    def _usuario():
        return {"usuario": g.get("usuario")}
