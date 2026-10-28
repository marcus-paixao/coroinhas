"""
Regras da escala (sem banco nem Flask): datas, ausências, pendências da semana,
participação no mês, aniversários e o texto para o WhatsApp.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from datetime import date, timedelta

DIAS = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]   # índice 0 = domingo
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
TIPOS = {"coroinha": "Coroinha", "cerimoniario": "Cerimoniário", "coordenacao": "Coordenação"}


# ------------------------------------------------------------------ datas
def dia_semana(d: date | str) -> int:
    """0 = domingo … 6 = sábado (mesma convenção dos horários fixos)."""
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return (d.weekday() + 1) % 7


def inicio_semana(d: date) -> date:
    """Segunda-feira da semana (seg–dom) que contém a data."""
    return d - timedelta(days=d.weekday())


def data_curta(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day:02d}/{d.month:02d}"


def formatar_hora(hora: str) -> str:
    h, m = hora.split(":")
    return f"{int(h)}h" if m == "00" else f"{int(h)}h{m}"


def rotulo_missa(m: dict) -> str:
    return f"{DIAS[dia_semana(m['data'])]} {data_curta(m['data'])} · {formatar_hora(m['hora'])}"


def titulo_semana(segunda: date, datas: list[str]) -> str:
    """'24 e 25 de outubro', '31/10 e 01/11'…"""
    datas = sorted(set(datas)) or [(segunda + timedelta(days=5)).isoformat(), (segunda + timedelta(days=6)).isoformat()]
    p, u = date.fromisoformat(datas[0]), date.fromisoformat(datas[-1])
    if len(datas) == 1:
        return f"{p.day} de {MESES[p.month - 1]}"
    juntar = "e" if len(datas) == 2 else "a"
    if p.month == u.month:
        return f"{p.day} {juntar} {u.day} de {MESES[u.month - 1]}"
    return f"{data_curta(datas[0])} {juntar} {data_curta(datas[-1])}"


def distancia_semana(segunda: date, hoje: date) -> str:
    n = (segunda - inicio_semana(hoje)).days // 7
    return {0: "esta semana", 1: "semana que vem", -1: "semana passada"}.get(
        n, f"daqui a {n} semanas" if n > 0 else f"há {-n} semanas")


def idade(nascimento: str, ref: date) -> int:
    n = date.fromisoformat(nascimento)
    return ref.year - n.year - ((ref.month, ref.day) < (n.month, n.day))


def dias_para_aniversario(nascimento: str, ref: date) -> int:
    n = date.fromisoformat(nascimento)
    for ano in (ref.year, ref.year + 1):
        try:
            prox = date(ano, n.month, n.day)
        except ValueError:          # 29/02 em ano não bissexto
            prox = date(ano, 3, 1)
        if prox >= ref:
            return (prox - ref).days
    return 0


# ------------------------------------------------------------------ nomes
_CONECTORES = {"da", "de", "do", "das", "dos", "e"}
_COMPOSTOS = {"maria", "joao", "ana", "anna", "jose", "pedro", "luiz", "luis"}
_PALETA_AVATAR = ["#3b5bdb", "#e8590c", "#0ca678", "#ae3ec9", "#f59f00", "#1098ad", "#d6336c", "#5c7cfa", "#74b816"]


def normalizar(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def nome_proprio(nome: str) -> str:
    partes = re.sub(r"\s+", " ", nome.strip()).split(" ")
    return " ".join(
        p.lower() if i > 0 and (p.lower() in _CONECTORES or len(p) <= 2) else p[0].upper() + p[1:].lower()
        for i, p in enumerate(partes) if p)


def sugerir_apelido(nome: str, existentes: list[str] = ()) -> str:
    """Primeiro nome; dois nomes se for composto comum (Maria Clara) ou se já houver alguém com o mesmo."""
    partes = [p for p in nome_proprio(nome).split(" ") if p.lower() not in _CONECTORES]
    if not partes:
        return ""
    usados = {normalizar(a) for a in existentes}
    n = 2 if normalizar(partes[0]) in _COMPOSTOS and len(partes) > 1 else 1
    apelido = " ".join(partes[:n])
    while normalizar(apelido) in usados and n < len(partes):
        n += 1
        apelido = " ".join(partes[:n])
    return apelido


def iniciais(nome: str) -> str:
    p = nome.split()
    return ((p[0][0] if p else "") + (p[-1][0] if len(p) > 1 else "")).upper()


def cor_avatar(nome: str) -> str:
    h = 0
    for c in nome:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return _PALETA_AVATAR[h % len(_PALETA_AVATAR)]


# ------------------------------------------------------------------ escala
def esta_ausente(m: dict, data: str) -> bool:
    """A ausência vale enquanto a flag estiver ligada e a data "até" (se houver) não tiver passado."""
    return bool(m["ausente"]) and (not m.get("ausente_ate") or data <= m["ausente_ate"])


def membros_da_missa(missa: dict) -> list[str]:
    return [e["membro_id"] for e in missa["vagas"] + missa["reservas"] if e["membro_id"]]


def participacao(missas: list[dict]) -> Counter:
    return Counter(i for m in missas for i in membros_da_missa(m))


def pendencias(membros: list[dict], missas: list[dict], tipos_escalaveis: list[str], segunda: date) -> dict:
    """Vagas abertas, quem ficou sem escala, ausentes e conflitos da semana."""
    ref = missas[0]["data"] if missas else (segunda + timedelta(days=5)).isoformat()
    vezes = participacao(missas)
    duplicados = []
    for missa in missas:
        contagem = Counter(membros_da_missa(missa))
        duplicados += [{"missa_id": missa["id"], "membro_id": i} for i, n in contagem.items() if n > 1]
    escalaveis = [m for m in membros if m["tipo"] in tipos_escalaveis]
    por_id = {m["id"]: m for m in membros}
    escalados_ausentes = sorted({
        i for missa in missas for i in membros_da_missa(missa)
        if i in por_id and esta_ausente(por_id[i], missa["data"])})
    return {
        "total_vagas": sum(len(m["vagas"]) for m in missas),
        "vagas_abertas": sum(1 for m in missas for v in m["vagas"] if not v["membro_id"]),
        "sem_escala": [m for m in escalaveis if not esta_ausente(m, ref) and m["id"] not in vezes],
        "ausentes": [m for m in escalaveis if esta_ausente(m, ref)],
        "escalados_ausentes": [por_id[i] for i in escalados_ausentes],
        "duplicados": duplicados,
        "vezes": vezes,
    }


def aniversariantes(membros: list[dict], hoje: date, dias: int = 31) -> list[dict]:
    saida = []
    for m in membros:
        if m.get("nascimento"):
            faltam = dias_para_aniversario(m["nascimento"], hoje)
            if faltam <= dias:
                saida.append({**m, "faltam": faltam, "fara": idade(m["nascimento"], hoje) + (1 if faltam else 0)})
    return sorted(saida, key=lambda x: x["faltam"])


def texto_whatsapp(missas: list[dict], membros: dict[str, dict], funcoes: dict[str, dict], titulo: str) -> str:
    """Texto formatado (negrito/itálico do WhatsApp) para colar no grupo."""
    nome = lambda i: membros[i]["apelido"] if i in membros else None  # noqa: E731
    linhas = [f"*⛪ Escala dos Coroinhas — {titulo}*", "_Basílica Nossa Senhora de Lourdes · Vila Isabel_", ""]
    for m in missas:
        linhas.append(f"*🗓️ {rotulo_missa(m)}*" + (f" — {m['titulo']}" if m.get("titulo") else ""))
        for v in m["vagas"]:
            fs = [funcoes[f] for f in v["funcoes"] if f in funcoes]
            quem = nome(v["membro_id"])
            linhas.append(f"{fs[0]['emoji'] if fs else '▫️'} {' / '.join(f['nome'] for f in fs) or 'Vaga'} — "
                          + (f"*{quem}*" if quem else "_a definir_"))
        reservas = [nome(r["membro_id"]) for r in m["reservas"] if nome(r["membro_id"])]
        if reservas:
            linhas.append(f"🙋 _Reservas:_ {', '.join(reservas)}")
        linhas.append("")
    return "\n".join(linhas).rstrip()
