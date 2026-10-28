"""
Dados da escala em SQLite: membros, funções, missas fixas (horários), missas e escalas
(quem serve em cada vaga/reserva). Toda alteração feita pela interface fica na tabela `historico`.
Na 1ª execução, com o banco vazio, carrega `carga_inicial/backup-inicial.json` (se existir).
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
import uuid
from contextlib import closing, contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from . import regras
from .padrao import CONFIG_PADRAO, FUNCOES_PADRAO, HORARIOS_PADRAO


class ErroCoroinhas(Exception):
    """Erro de validação com mensagem amigável."""


_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_COR = re.compile(r"^#[0-9a-fA-F]{6}$")
_ID = re.compile(r"^[\w-]{1,40}$")
CAMPOS_MEMBRO = ("nome", "apelido", "tipo", "nascimento", "telefone", "responsavel", "observacoes",
                 "ausente", "motivo_ausencia", "ausente_ate")

SCHEMA = """
CREATE TABLE IF NOT EXISTS membros (
    id TEXT PRIMARY KEY, nome TEXT NOT NULL, apelido TEXT NOT NULL, tipo TEXT NOT NULL,
    nascimento TEXT, telefone TEXT, responsavel TEXT, observacoes TEXT,
    ausente INTEGER NOT NULL DEFAULT 0, motivo_ausencia TEXT, ausente_ate TEXT);
CREATE TABLE IF NOT EXISTS funcoes (
    id TEXT PRIMARY KEY, nome TEXT NOT NULL, emoji TEXT NOT NULL, cor TEXT NOT NULL, ordem INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS horarios (
    id TEXT PRIMARY KEY, dia_semana INTEGER NOT NULL, hora TEXT NOT NULL, titulo TEXT,
    reservas INTEGER NOT NULL DEFAULT 0, vagas TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS missas (id TEXT PRIMARY KEY, data TEXT NOT NULL, hora TEXT NOT NULL, titulo TEXT);
CREATE INDEX IF NOT EXISTS ix_missas_data ON missas(data);
CREATE TABLE IF NOT EXISTS escalas (
    id TEXT PRIMARY KEY,
    missa_id TEXT NOT NULL REFERENCES missas(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL CHECK (tipo IN ('vaga', 'reserva')),
    posicao INTEGER NOT NULL,
    funcoes TEXT NOT NULL DEFAULT '[]',
    membro_id TEXT REFERENCES membros(id) ON DELETE SET NULL);
CREATE INDEX IF NOT EXISTS ix_escalas_missa ON escalas(missa_id);
CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT, quando TEXT, usuario TEXT, acao TEXT, descricao TEXT);
"""


def novo_id() -> str:
    return uuid.uuid4().hex[:12]


# ------------------------------------------------------------------ validação
def _texto(v, rotulo: str, maximo: int, obrigatorio: bool = False) -> str | None:
    s = str(v).strip() if v is not None else ""
    if not s:
        if obrigatorio:
            raise ErroCoroinhas(f"Preencha o campo {rotulo}.")
        return None
    if len(s) > maximo:
        raise ErroCoroinhas(f"{rotulo}: no máximo {maximo} caracteres.")
    return s


def _data(v, rotulo: str, obrigatorio: bool = False) -> str | None:
    if not v:
        if obrigatorio:
            raise ErroCoroinhas(f"Informe {rotulo}.")
        return None
    try:
        if not isinstance(v, str) or not _DATA.match(v):
            raise ValueError
        date.fromisoformat(v)
    except ValueError:
        raise ErroCoroinhas(f"{rotulo}: data inválida.") from None
    return v


def _hora(v) -> str:
    if not isinstance(v, str) or not _HORA.match(v):
        raise ErroCoroinhas("Horário inválido (use HH:MM).")
    return v


def _inteiro(v, rotulo: str, minimo: int, maximo: int) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ErroCoroinhas(f"{rotulo}: número inválido.") from None
    if not minimo <= n <= maximo:
        raise ErroCoroinhas(f"{rotulo}: use um valor entre {minimo} e {maximo}.")
    return n


def _id(v) -> str:
    if not isinstance(v, str) or not _ID.match(v):
        raise ErroCoroinhas("Identificador inválido.")
    return v


class RepositorioCoroinhas:
    def __init__(self, db_path: Path, carga_inicial: Path | None = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._tx() as con:
            con.executescript(SCHEMA)
        if self._vazio():
            if carga_inicial and Path(carga_inicial).exists():
                self.restaurar(json.loads(Path(carga_inicial).read_text(encoding="utf-8")),
                               usuario="sistema", origem="carga inicial")
            else:
                self.restaurar({"membros": []}, usuario="sistema", origem="padrões")

    # ------------------------------------------------------------------ infraestrutura
    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        return con

    @contextmanager
    def _tx(self):
        """Transação única: grava tudo ou nada."""
        with self._lock, closing(self._con()) as con:
            try:
                yield con
                con.commit()
            except Exception:
                con.rollback()
                raise

    def _ler(self, sql: str, params=()) -> list[dict]:
        with closing(self._con()) as con:
            return [dict(r) for r in con.execute(sql, params)]

    def _vazio(self) -> bool:
        return not self._ler("SELECT 1 FROM funcoes LIMIT 1") and not self._ler("SELECT 1 FROM membros LIMIT 1")

    @staticmethod
    def _log(con, usuario: str, acao: str, descricao: str) -> None:
        con.execute("INSERT INTO historico (quando, usuario, acao, descricao) VALUES (?, ?, ?, ?)",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), usuario, acao, descricao))

    # ------------------------------------------------------------------ leitura
    def membros(self) -> list[dict]:
        saida = self._ler("SELECT * FROM membros ORDER BY apelido COLLATE NOCASE")
        for m in saida:
            m["ausente"] = bool(m["ausente"])
            m["cor"] = regras.cor_avatar(m["nome"])
            m["iniciais"] = regras.iniciais(m["apelido"] or m["nome"])
        return saida

    def funcoes(self) -> list[dict]:
        return self._ler("SELECT id, nome, emoji, cor FROM funcoes ORDER BY ordem, nome")

    def horarios(self) -> list[dict]:
        saida = self._ler("SELECT * FROM horarios ORDER BY (dia_semana + 6) % 7, hora")   # sábado antes de domingo
        for h in saida:
            h["vagas"] = json.loads(h["vagas"])
        return saida

    def config(self) -> dict:
        r = self._ler("SELECT valor FROM config WHERE chave = 'geral'")
        return {**CONFIG_PADRAO, **(json.loads(r[0]["valor"]) if r else {})}

    def historico(self, limite: int = 300) -> list[dict]:
        return self._ler("SELECT * FROM historico ORDER BY id DESC LIMIT ?", (limite,))

    def missas_entre(self, inicio: date, fim: date) -> list[dict]:
        """Missas do período com as vagas e reservas na ordem."""
        ini, fi = inicio.isoformat(), fim.isoformat()
        missas = self._ler("SELECT * FROM missas WHERE data BETWEEN ? AND ? ORDER BY data, hora", (ini, fi))
        por_id = {m["id"]: {**m, "vagas": [], "reservas": []} for m in missas}
        for e in self._ler("""SELECT e.* FROM escalas e JOIN missas m ON m.id = e.missa_id
                              WHERE m.data BETWEEN ? AND ? ORDER BY e.posicao""", (ini, fi)):
            item = {"id": e["id"], "funcoes": json.loads(e["funcoes"]), "membro_id": e["membro_id"]}
            por_id[e["missa_id"]]["vagas" if e["tipo"] == "vaga" else "reservas"].append(item)
        return list(por_id.values())

    def horarios_faltando(self, segunda: date) -> int:
        """Quantas missas dos horários fixos ainda não foram criadas na semana."""
        existentes = {(m["data"], m["hora"]) for m in self.missas_entre(segunda, segunda + timedelta(days=6))}
        horarios = self.horarios()
        return sum(1 for i in range(7) for h in horarios
                   if h["dia_semana"] == regras.dia_semana(segunda + timedelta(days=i))
                   and ((segunda + timedelta(days=i)).isoformat(), h["hora"]) not in existentes)

    # ------------------------------------------------------------------ membros
    def _validar_membro(self, d: dict, existentes: list[str]) -> dict:
        nome = regras.nome_proprio(_texto(d.get("nome"), "Nome", 200, True))
        tipo = d.get("tipo") or "coroinha"
        if tipo not in regras.TIPOS:
            raise ErroCoroinhas("Função na pastoral inválida.")
        ausente = bool(d.get("ausente"))
        return {
            "nome": nome,
            "apelido": _texto(d.get("apelido"), "Nome na escala", 80) or regras.sugerir_apelido(nome, existentes),
            "tipo": tipo,
            "nascimento": _data(d.get("nascimento"), "Data de nascimento"),
            "telefone": _texto(d.get("telefone"), "Telefone", 40),
            "responsavel": _texto(d.get("responsavel"), "Responsável", 200),
            "observacoes": _texto(d.get("observacoes"), "Observações", 2000),
            "ausente": int(ausente),
            "motivo_ausencia": _texto(d.get("motivo_ausencia"), "Motivo", 200) if ausente else None,
            "ausente_ate": _data(d.get("ausente_ate"), "Ausente até") if ausente else None,
        }

    def salvar_membro(self, dados: dict, membro_id: str | None = None, usuario: str = "") -> dict:
        outros = [m["apelido"] for m in self.membros() if m["id"] != membro_id]
        reg = self._validar_membro(dados, outros)
        with self._tx() as con:
            if membro_id:
                if not con.execute("SELECT 1 FROM membros WHERE id = ?", (membro_id,)).fetchone():
                    raise ErroCoroinhas("Cadastro não encontrado.")
                con.execute(f"UPDATE membros SET {', '.join(f'{c} = ?' for c in reg)} WHERE id = ?",
                            [*reg.values(), membro_id])
                self._log(con, usuario, "Alteração", f"Cadastro de {reg['apelido']} atualizado")
            else:
                membro_id = novo_id()
                con.execute(f"INSERT INTO membros (id, {', '.join(reg)}) VALUES (?, {', '.join('?' * len(reg))})",
                            [membro_id, *reg.values()])
                self._log(con, usuario, "Inclusão", f"{reg['apelido']} cadastrado(a) como {regras.TIPOS[reg['tipo']]}")
        return {"id": membro_id, **reg}

    def remover_membro(self, membro_id: str, usuario: str = "") -> None:
        with self._tx() as con:
            r = con.execute("SELECT apelido FROM membros WHERE id = ?", (membro_id,)).fetchone()
            if not r:
                raise ErroCoroinhas("Cadastro não encontrado.")
            con.execute("DELETE FROM membros WHERE id = ?", (membro_id,))   # escalas: ON DELETE SET NULL
            self._log(con, usuario, "Exclusão", f"Cadastro de {r['apelido']} removido")

    def definir_ausencia(self, membro_id: str, ausente: bool, motivo=None, ate=None, usuario: str = "") -> None:
        """Ligar de novo limpa uma data "até" antiga (senão a ausência já nasceria vencida)."""
        motivo = _texto(motivo, "Motivo", 200)
        ate = _data(ate, "Ausente até")
        with self._tx() as con:
            r = con.execute("SELECT apelido, motivo_ausencia FROM membros WHERE id = ?", (membro_id,)).fetchone()
            if not r:
                raise ErroCoroinhas("Cadastro não encontrado.")
            if ausente:
                con.execute("UPDATE membros SET ausente = 1, motivo_ausencia = ?, ausente_ate = ? WHERE id = ?",
                            (motivo or r["motivo_ausencia"], ate, membro_id))
            else:
                con.execute("UPDATE membros SET ausente = 0, motivo_ausencia = NULL, ausente_ate = NULL WHERE id = ?",
                            (membro_id,))
            self._log(con, usuario, "Ausência", f"{r['apelido']} {'marcado(a) como ausente' if ausente else 'voltou'}")

    def importar_membros(self, novos: list[dict], arquivo: str, usuario: str = "") -> tuple[int, int]:
        """Junta a planilha da Pastoral: atualiza quem já existe (mesmo nome) e inclui os novos."""
        atuais = {regras.normalizar(m["nome"]): m for m in self.membros()}
        apelidos = [m["apelido"] for m in atuais.values()]
        incluidos = atualizados = 0
        with self._tx() as con:
            for n in novos:
                ex = atuais.get(regras.normalizar(n["nome"]))
                if ex:
                    con.execute("UPDATE membros SET tipo = ?, nascimento = COALESCE(?, nascimento) WHERE id = ?",
                                (n["tipo"], n.get("nascimento"), ex["id"]))
                    atualizados += 1
                else:
                    reg = self._validar_membro(n, apelidos)
                    apelidos.append(reg["apelido"])
                    con.execute(f"INSERT INTO membros (id, {', '.join(reg)}) VALUES (?, {', '.join('?' * len(reg))})",
                                [novo_id(), *reg.values()])
                    incluidos += 1
            self._log(con, usuario, "Importação", f"Planilha {arquivo}: {incluidos} novo(s), {atualizados} atualizado(s)")
        return incluidos, atualizados

    # ------------------------------------------------------------------ funções
    def salvar_funcao(self, dados: dict, funcao_id: str | None = None, usuario: str = "") -> dict:
        nome = _texto(dados.get("nome"), "Nome", 60, True)
        emoji = _texto(dados.get("emoji"), "Ícone", 16, True)
        cor = dados.get("cor")
        if not isinstance(cor, str) or not _COR.match(cor):
            raise ErroCoroinhas("Cor inválida.")
        with self._tx() as con:
            if con.execute("SELECT 1 FROM funcoes WHERE lower(nome) = lower(?) AND id IS NOT ?", (nome, funcao_id)).fetchone():
                raise ErroCoroinhas(f"Já existe a função “{nome}”.")
            if funcao_id:
                if con.execute("UPDATE funcoes SET nome = ?, emoji = ?, cor = ? WHERE id = ?",
                               (nome, emoji, cor, funcao_id)).rowcount == 0:
                    raise ErroCoroinhas("Função não encontrada.")
                self._log(con, usuario, "Alteração", f"Função {nome} atualizada")
            else:
                funcao_id = novo_id()
                ordem = con.execute("SELECT COALESCE(MAX(ordem), -1) + 1 FROM funcoes").fetchone()[0]
                con.execute("INSERT INTO funcoes (id, nome, emoji, cor, ordem) VALUES (?, ?, ?, ?, ?)",
                            (funcao_id, nome, emoji, cor, ordem))
                self._log(con, usuario, "Inclusão", f"Função {nome} criada")
        return {"id": funcao_id, "nome": nome, "emoji": emoji, "cor": cor}

    def remover_funcao(self, funcao_id: str, usuario: str = "") -> None:
        """Remove a função e tira ela de todas as vagas (horários fixos e escalas)."""
        with self._tx() as con:
            r = con.execute("SELECT nome FROM funcoes WHERE id = ?", (funcao_id,)).fetchone()
            if not r:
                raise ErroCoroinhas("Função não encontrada.")
            con.execute("DELETE FROM funcoes WHERE id = ?", (funcao_id,))
            for h in con.execute("SELECT id, vagas FROM horarios").fetchall():
                vagas = [[f for f in v if f != funcao_id] for v in json.loads(h["vagas"])]
                con.execute("UPDATE horarios SET vagas = ? WHERE id = ?", (json.dumps(vagas), h["id"]))
            for e in con.execute("SELECT id, funcoes FROM escalas WHERE funcoes LIKE ?", (f'%"{funcao_id}"%',)).fetchall():
                fs = [f for f in json.loads(e["funcoes"]) if f != funcao_id]
                con.execute("UPDATE escalas SET funcoes = ? WHERE id = ?", (json.dumps(fs), e["id"]))
            self._log(con, usuario, "Exclusão", f"Função {r['nome']} removida")

    def _vagas_validas(self, con, vagas) -> list[list[str]]:
        if not isinstance(vagas, list) or len(vagas) > 40:
            raise ErroCoroinhas("Lista de vagas inválida.")
        validas = {r["id"] for r in con.execute("SELECT id FROM funcoes")}
        return [[f for f in v if f in validas] for v in vagas if isinstance(v, list)]

    # ------------------------------------------------------------------ horários fixos
    def salvar_horario(self, dados: dict, horario_id: str | None = None, usuario: str = "") -> None:
        dia = _inteiro(dados.get("dia_semana"), "Dia da semana", 0, 6)
        hora = _hora(dados.get("hora"))
        titulo = _texto(dados.get("titulo"), "Título", 120)
        reservas = _inteiro(dados.get("reservas", 0), "Reservas", 0, 20)
        rotulo = f"{regras.DIAS[dia]} {regras.formatar_hora(hora)}"
        with self._tx() as con:
            vagas = json.dumps(self._vagas_validas(con, dados.get("vagas", [])))
            if horario_id:
                if con.execute("UPDATE horarios SET dia_semana = ?, hora = ?, titulo = ?, reservas = ?, vagas = ? WHERE id = ?",
                               (dia, hora, titulo, reservas, vagas, horario_id)).rowcount == 0:
                    raise ErroCoroinhas("Horário não encontrado.")
                self._log(con, usuario, "Alteração", f"Missa fixa {rotulo} atualizada")
            else:
                con.execute("INSERT INTO horarios (id, dia_semana, hora, titulo, reservas, vagas) VALUES (?, ?, ?, ?, ?, ?)",
                            (novo_id(), dia, hora, titulo, reservas, vagas))
                self._log(con, usuario, "Inclusão", f"Missa fixa {rotulo} criada")

    def remover_horario(self, horario_id: str, usuario: str = "") -> None:
        with self._tx() as con:
            r = con.execute("SELECT dia_semana, hora FROM horarios WHERE id = ?", (horario_id,)).fetchone()
            if not r:
                raise ErroCoroinhas("Horário não encontrado.")
            con.execute("DELETE FROM horarios WHERE id = ?", (horario_id,))
            self._log(con, usuario, "Exclusão", f"Missa fixa {regras.DIAS[r['dia_semana']]} {regras.formatar_hora(r['hora'])} removida")

    # ------------------------------------------------------------------ missas e escalas
    @staticmethod
    def _inserir_escalas(con, missa_id: str, vagas: list[tuple], reservas: list[tuple]) -> None:
        """vagas: [(id, funcoes, membro_id)] · reservas: [(id, membro_id)]"""
        for i, (eid, funcoes, membro) in enumerate(vagas):
            con.execute("INSERT INTO escalas (id, missa_id, tipo, posicao, funcoes, membro_id) VALUES (?, ?, 'vaga', ?, ?, ?)",
                        (eid, missa_id, i, json.dumps(funcoes), membro))
        for i, (eid, membro) in enumerate(reservas):
            con.execute("INSERT INTO escalas (id, missa_id, tipo, posicao, funcoes, membro_id) VALUES (?, ?, 'reserva', ?, '[]', ?)",
                        (eid, missa_id, i, membro))

    def gerar_semana(self, segunda: date, usuario: str = "") -> int:
        """Cria as missas da semana a partir dos horários fixos, sem duplicar as que já existem."""
        horarios = self.horarios()
        criadas = 0
        with self._tx() as con:
            for i in range(7):
                dia = segunda + timedelta(days=i)
                for h in (h for h in horarios if h["dia_semana"] == regras.dia_semana(dia)):
                    if con.execute("SELECT 1 FROM missas WHERE data = ? AND hora = ?", (dia.isoformat(), h["hora"])).fetchone():
                        continue
                    mid = novo_id()
                    con.execute("INSERT INTO missas (id, data, hora, titulo) VALUES (?, ?, ?, ?)",
                                (mid, dia.isoformat(), h["hora"], h["titulo"]))
                    self._inserir_escalas(con, mid, [(novo_id(), v, None) for v in h["vagas"]],
                                          [(novo_id(), None) for _ in range(h["reservas"])])
                    criadas += 1
            if criadas:
                self._log(con, usuario, "Escala", f"{criadas} missa(s) criada(s) na semana de {regras.data_curta(segunda.isoformat())}")
        return criadas

    def salvar_missa(self, dados: dict, missa_id: str | None = None, usuario: str = "") -> str:
        """Cria/edita a missa. Quem já estava escalado continua na vaga (pelo id da vaga) e nas reservas (pela ordem)."""
        data = _data(dados.get("data"), "Data", True)
        hora = _hora(dados.get("hora"))
        titulo = _texto(dados.get("titulo"), "Título", 120)
        n_reservas = _inteiro(dados.get("reservas", 0), "Reservas", 0, 20)
        vagas_in = dados.get("vagas", [])
        if not isinstance(vagas_in, list):
            raise ErroCoroinhas("Lista de vagas inválida.")
        with self._tx() as con:
            funcoes = self._vagas_validas(con, [v.get("funcoes", []) if isinstance(v, dict) else [] for v in vagas_in])
            antes_vagas, antes_reservas = {}, []
            if missa_id:
                if con.execute("UPDATE missas SET data = ?, hora = ?, titulo = ? WHERE id = ?",
                               (data, hora, titulo, missa_id)).rowcount == 0:
                    raise ErroCoroinhas("Missa não encontrada.")
                for e in con.execute("SELECT * FROM escalas WHERE missa_id = ? ORDER BY posicao", (missa_id,)):
                    if e["tipo"] == "vaga":
                        antes_vagas[e["id"]] = e["membro_id"]
                    else:
                        antes_reservas.append((e["id"], e["membro_id"]))
                con.execute("DELETE FROM escalas WHERE missa_id = ?", (missa_id,))
                acao, desc = "Alteração", "atualizada"
            else:
                missa_id = novo_id()
                con.execute("INSERT INTO missas (id, data, hora, titulo) VALUES (?, ?, ?, ?)", (missa_id, data, hora, titulo))
                acao, desc = "Inclusão", "criada"
            vagas = []
            for v, fs in zip(vagas_in, funcoes):
                vid = v.get("id") if isinstance(v, dict) else None
                if vid in antes_vagas:
                    vagas.append((vid, fs, antes_vagas[vid]))
                else:
                    vagas.append((novo_id(), fs, None))
            reservas = [antes_reservas[i] if i < len(antes_reservas) else (novo_id(), None) for i in range(n_reservas)]
            self._inserir_escalas(con, missa_id, vagas, reservas)
            self._log(con, usuario, acao, f"Missa de {regras.rotulo_missa({'data': data, 'hora': hora})} {desc}")
        return missa_id

    def remover_missa(self, missa_id: str, usuario: str = "") -> None:
        with self._tx() as con:
            r = con.execute("SELECT data, hora FROM missas WHERE id = ?", (missa_id,)).fetchone()
            if not r:
                raise ErroCoroinhas("Missa não encontrada.")
            con.execute("DELETE FROM missas WHERE id = ?", (missa_id,))
            self._log(con, usuario, "Exclusão", f"Missa de {regras.rotulo_missa(dict(r))} removida")

    def escalar(self, escala_id: str, membro_id: str | None, usuario: str = "") -> str | None:
        """Põe (ou tira) alguém de uma vaga/reserva. Devolve quem estava antes (para o "Desfazer")."""
        with self._tx() as con:
            e = con.execute("""SELECT e.*, m.data, m.hora FROM escalas e JOIN missas m ON m.id = e.missa_id
                               WHERE e.id = ?""", (escala_id,)).fetchone()
            if not e:
                raise ErroCoroinhas("Vaga não encontrada.")
            nome = None
            if membro_id:
                r = con.execute("SELECT apelido FROM membros WHERE id = ?", (membro_id,)).fetchone()
                if not r:
                    raise ErroCoroinhas("Cadastro não encontrado.")
                nome = r["apelido"]
            con.execute("UPDATE escalas SET membro_id = ? WHERE id = ?", (membro_id, escala_id))
            onde = f"{regras.rotulo_missa(dict(e))} ({'reserva' if e['tipo'] == 'reserva' else 'vaga'} {e['posicao'] + 1})"
            self._log(con, usuario, "Escala", f"{nome} escalado(a) em {onde}" if nome else f"Vaga liberada em {onde}")
            return e["membro_id"]

    def copiar_semana_anterior(self, segunda: date, usuario: str = "") -> int:
        """Repete, em cada missa da semana, as vagas e quem serviu na mesma missa (dia + hora) 7 dias antes."""
        atuais = self.missas_entre(segunda, segunda + timedelta(days=6))
        anteriores = {(m["data"], m["hora"]): m for m in self.missas_entre(segunda - timedelta(days=7), segunda - timedelta(days=1))}
        copiadas = 0
        with self._tx() as con:
            for m in atuais:
                ant = anteriores.get(((date.fromisoformat(m["data"]) - timedelta(days=7)).isoformat(), m["hora"]))
                if not ant:
                    continue
                con.execute("DELETE FROM escalas WHERE missa_id = ?", (m["id"],))
                self._inserir_escalas(con, m["id"], [(novo_id(), v["funcoes"], v["membro_id"]) for v in ant["vagas"]],
                                      [(novo_id(), r["membro_id"]) for r in ant["reservas"]])
                copiadas += 1
            if copiadas:
                self._log(con, usuario, "Escala", f"Semana de {regras.data_curta(segunda.isoformat())} copiada da anterior")
        return copiadas

    # ------------------------------------------------------------------ configuração
    def salvar_config(self, dados: dict, usuario: str = "") -> dict:
        tipos = dados.get("tipos_escalaveis")
        if not isinstance(tipos, list) or not set(tipos) <= set(regras.TIPOS):
            raise ErroCoroinhas("Tipos inválidos.")
        valor = {"tipos_escalaveis": list(dict.fromkeys(tipos))}
        with self._tx() as con:
            con.execute("INSERT INTO config (chave, valor) VALUES ('geral', ?) "
                        "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor", (json.dumps(valor),))
            self._log(con, usuario, "Ajuste", "Alertas: " + (", ".join(regras.TIPOS[t] for t in valor["tipos_escalaveis"]) or "ninguém"))
        return valor

    # ------------------------------------------------------------------ backup
    def exportar(self) -> dict:
        missas = self.missas_entre(date.min, date.max)
        return {
            "versao": 2,
            "exportado_em": datetime.now().isoformat(timespec="seconds"),
            "membros": [{k: m[k] for k in ("id", *CAMPOS_MEMBRO)} for m in self.membros()],
            "funcoes": self.funcoes(),
            "horarios": self.horarios(),
            "missas": [{"id": m["id"], "data": m["data"], "hora": m["hora"], "titulo": m["titulo"],
                        "vagas": [{"funcoes": v["funcoes"], "membro_id": v["membro_id"]} for v in m["vagas"]],
                        "reservas": [r["membro_id"] for r in m["reservas"]]} for m in missas],
            "config": self.config(),
        }

    @staticmethod
    def _normalizar_backup(d: dict) -> dict:
        """Aceita o backup deste sistema (versão 2) e o da versão anterior em React (camelCase)."""
        if not isinstance(d, dict) or not isinstance(d.get("membros"), list):
            raise ErroCoroinhas("O arquivo não parece um backup do sistema de coroinhas.")
        camel = {"motivoAusencia": "motivo_ausencia", "ausenteAte": "ausente_ate", "diaSemana": "dia_semana",
                 "membroId": "membro_id", "tiposEscalaveis": "tipos_escalaveis"}
        snake = lambda o: {camel.get(k, k): v for k, v in o.items()} if isinstance(o, dict) else o  # noqa: E731
        vaga_ids = lambda v: v.get("funcoes", []) if isinstance(v, dict) else v  # noqa: E731
        reserva = lambda r: r.get("membro_id") if isinstance(r, dict) else r  # noqa: E731
        horarios = [snake(h) for h in d.get("horarios") or []]
        for h in horarios:
            h["vagas"] = [vaga_ids(v) for v in h.get("vagas", [])]
        missas = [snake(m) for m in d.get("missas") or []]
        for m in missas:
            m["vagas"] = [snake(v) for v in m.get("vagas", [])]
            m["reservas"] = [reserva(snake(r)) for r in m.get("reservas", [])]
        return {"membros": [snake(m) for m in d["membros"]], "funcoes": d.get("funcoes"), "horarios": horarios,
                "missas": missas, "config": snake(d.get("config") or {})}

    def restaurar(self, dados: dict, usuario: str = "", origem: str = "backup") -> dict:
        """Substitui tudo pelo conteúdo do backup, numa transação só (inválido = nada muda)."""
        d = self._normalizar_backup(dados)
        # backup sem funções (ex.: a carga inicial) recebe as funções e as missas fixas padrão
        sem_funcoes = d["funcoes"] is None
        funcoes = FUNCOES_PADRAO if sem_funcoes else d["funcoes"]
        horarios = HORARIOS_PADRAO if sem_funcoes else d["horarios"]
        with self._tx() as con:
            for t in ("escalas", "missas", "horarios", "funcoes", "membros"):
                con.execute(f"DELETE FROM {t}")
            ids_membros = set()
            for m in d["membros"]:
                reg = self._validar_membro(m, [])
                mid = _id(m.get("id") or novo_id())
                con.execute(f"INSERT INTO membros (id, {', '.join(reg)}) VALUES (?, {', '.join('?' * len(reg))})",
                            [mid, *reg.values()])
                ids_membros.add(mid)
            for i, f in enumerate(funcoes):
                con.execute("INSERT INTO funcoes (id, nome, emoji, cor, ordem) VALUES (?, ?, ?, ?, ?)",
                            (_id(f["id"]), _texto(f.get("nome"), "Nome", 60, True), _texto(f.get("emoji"), "Ícone", 16, True),
                             f["cor"] if _COR.match(str(f.get("cor"))) else "#2f4ac2", i))
            for h in horarios:
                con.execute("INSERT INTO horarios (id, dia_semana, hora, titulo, reservas, vagas) VALUES (?, ?, ?, ?, ?, ?)",
                            (_id(h.get("id") or novo_id()), _inteiro(h.get("dia_semana"), "Dia", 0, 6), _hora(h.get("hora")),
                             _texto(h.get("titulo"), "Título", 120), _inteiro(h.get("reservas", 0), "Reservas", 0, 20),
                             json.dumps(self._vagas_validas(con, h.get("vagas", [])))))
            membro = lambda x: x if x in ids_membros else None  # noqa: E731
            for m in d["missas"]:
                mid = _id(m.get("id") or novo_id())
                con.execute("INSERT INTO missas (id, data, hora, titulo) VALUES (?, ?, ?, ?)",
                            (mid, _data(m.get("data"), "Data", True), _hora(m.get("hora")), _texto(m.get("titulo"), "Título", 120)))
                fs = self._vagas_validas(con, [v.get("funcoes", []) for v in m["vagas"]])
                self._inserir_escalas(con, mid, [(novo_id(), f, membro(v.get("membro_id"))) for v, f in zip(m["vagas"], fs)],
                                      [(novo_id(), membro(r)) for r in m["reservas"]])
            config = {**CONFIG_PADRAO, **{k: v for k, v in d["config"].items() if k == "tipos_escalaveis"}}
            con.execute("INSERT INTO config (chave, valor) VALUES ('geral', ?) "
                        "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor", (json.dumps(config),))
            self._log(con, usuario, "Restauração",
                      f"Dados carregados ({origem}): {len(d['membros'])} pessoas, {len(d['missas'])} missas")
        return {"membros": len(d["membros"]), "missas": len(d["missas"])}

    def apagar_tudo(self, usuario: str = "") -> None:
        self.restaurar({"membros": []}, usuario=usuario, origem="recomeço do zero")
