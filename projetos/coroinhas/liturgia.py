"""
Liturgia diária católica (CNBB): cálculo do calendário litúrgico romano (tempo, semana,
Ano A/B/C, Ano Par/Ímpar e cor do paramento) + consulta automática das leituras na API
da Liturgia Diária (com cache no SQLite para abrir instantaneamente).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date, timedelta

from . import regras

CORES_LITURGICAS = {
    "Verde": {"hex": "#137a3f", "escuro": "#0b542a", "texto": "#ffffff", "borda": "#0b542a", "simbolo": "#e9f5ee"},
    "Branco": {"hex": "#fbf8f1", "escuro": "#ebe3d2", "texto": "#6e510b", "borda": "#d4a838", "simbolo": "#9c7111"},
    "Vermelho": {"hex": "#c92a2a", "escuro": "#961b1b", "texto": "#ffffff", "borda": "#961b1b", "simbolo": "#ffe8e8"},
    "Roxo": {"hex": "#5f3dc4", "escuro": "#422696", "texto": "#ffffff", "borda": "#422696", "simbolo": "#efeaff"},
    "Rosa": {"hex": "#d6336c", "escuro": "#a61e4d", "texto": "#ffffff", "borda": "#a61e4d", "simbolo": "#ffe6ef"},
}

_ROMANOS = {1: "I", 2: "II"}


def pascoa(ano: int) -> date:
    """Domingo de Páscoa pelo algoritmo de Butcher-Meeus."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, resto = divmod(h + l - 7 * m + 114, 31)
    return date(ano, mes, resto + 1)


def primeiro_domingo_advento(ano: int) -> date:
    """1º Domingo do Advento (domingo entre 27/11 e 03/12)."""
    natal = date(ano, 12, 25)
    # weekday(): seg=0 ... dom=6; dias desde o domingo anterior (ou 7 se o Natal cair no domingo)
    offset = (natal.weekday() + 1) % 7 or 7
    return natal - timedelta(days=offset + 21)


def batismo_do_senhor(ano: int) -> date:
    """No Brasil (onde a Epifania é transferida para o domingo entre 2 e 8 de janeiro):
    o Batismo do Senhor é no domingo seguinte à Epifania, ou na segunda-feira se a Epifania cair em 7 ou 8/jan."""
    d2 = date(ano, 1, 2)
    dias_ate_dom = (6 - d2.weekday()) % 7
    epifania = d2 + timedelta(days=dias_ate_dom)
    if epifania.day in (7, 8):
        return epifania + timedelta(days=1)
    return epifania + timedelta(days=7)


def ciclo_liturgico(d: date) -> tuple[str, str]:
    """Devolve (ciclo_domingo, ciclo_ferial), ex.: ('Ano A', 'Ano Par (II)')."""
    ano_liturgico = d.year + 1 if d >= primeiro_domingo_advento(d.year) else d.year
    letra = {1: "A", 2: "B", 0: "C"}[ano_liturgico % 3]
    par_impar = "Par (II)" if d.year % 2 == 0 else "Ímpar (I)"
    return f"Ano {letra}", f"Ano {par_impar}"


# Festas e solenidades fixas de destaque (incluindo a Padroeira da Basílica em 11/02)
_FIXAS: dict[tuple[int, int], tuple[str, str]] = {
    (1, 1): ("Solenidade de Santa Maria, Mãe de Deus", "Branco"),
    (2, 2): ("Festa da Apresentação do Senhor", "Branco"),
    (2, 11): ("Nossa Senhora de Lourdes · Padroeira da Basílica", "Branco"),
    (3, 19): ("Solenidade de São José, Esposo de Maria", "Branco"),
    (3, 25): ("Solenidade da Anunciação do Senhor", "Branco"),
    (6, 24): ("Solenidade da Natividade de São João Batista", "Branco"),
    (6, 29): ("Solenidade de São Pedro e São Paulo, Apóstolos", "Vermelho"),
    (8, 6): ("Festa da Transfiguração do Senhor", "Branco"),
    (8, 15): ("Solenidade da Assunção de Nossa Senhora", "Branco"),
    (9, 14): ("Festa da Exaltação da Santa Cruz", "Vermelho"),
    (10, 12): ("Solenidade de Nossa Senhora Aparecida, Padroeira do Brasil", "Branco"),
    (11, 1): ("Solenidade de Todos os Santos", "Branco"),
    (11, 2): ("Comemoração de Todos os Fiéis Defuntos", "Roxo"),
    (11, 9): ("Festa da Dedicação da Basílica de Latrão", "Branco"),
    (12, 8): ("Solenidade da Imaculada Conceição de Nossa Senhora", "Branco"),
    (12, 25): ("Solenidade do Natal do Senhor", "Branco"),
}


def calcular_calendario(d: date) -> dict:
    """Calcula título litúrgico, tempo, ciclo e cor para qualquer data."""
    ano_dom, ano_ferial = ciclo_liturgico(d)
    eh_dom = d.weekday() == 6
    sufixo = ano_dom if eh_dom else ano_ferial

    p = pascoa(d.year)
    cinzas = p - timedelta(days=46)
    ramos = p - timedelta(days=7)
    pentecostes = p + timedelta(days=49)
    trindade = p + timedelta(days=56)
    corpus = p + timedelta(days=60)
    sagrado_coracao = p + timedelta(days=68)
    advento1 = primeiro_domingo_advento(d.year)
    cristo_rei = advento1 - timedelta(days=7)
    batismo = batismo_do_senhor(d.year)

    # Datas móveis principais
    if d == cinzas:
        return {"titulo": f"Quarta-feira de Cinzas, {ano_dom}", "cor": "Roxo", "ciclo": sufixo}
    if d == ramos:
        return {"titulo": f"Domingo de Ramos e da Paixão do Senhor, {ano_dom}", "cor": "Vermelho", "ciclo": sufixo}
    if d == p - timedelta(days=3):
        return {"titulo": "Quinta-feira Santa · Ceia do Senhor", "cor": "Branco", "ciclo": sufixo}
    if d == p - timedelta(days=2):
        return {"titulo": "Sexta-feira Santa · Paixão do Senhor", "cor": "Vermelho", "ciclo": sufixo}
    if d == p - timedelta(days=1):
        return {"titulo": f"Sábado Santo · Vigília Pascal, {ano_dom}", "cor": "Branco", "ciclo": sufixo}
    if d == p:
        return {"titulo": f"Domingo da Páscoa na Ressurreição do Senhor, {ano_dom}", "cor": "Branco", "ciclo": sufixo}
    if d == p + timedelta(days=42):
        return {"titulo": f"Solenidade da Ascensão do Senhor, {ano_dom}", "cor": "Branco", "ciclo": sufixo}
    if d == pentecostes:
        return {"titulo": f"Domingo de Pentecostes, {ano_dom}", "cor": "Vermelho", "ciclo": sufixo}
    if d == trindade:
        return {"titulo": f"Solenidade da Santíssima Trindade, {ano_dom}", "cor": "Branco", "ciclo": sufixo}
    if d == corpus:
        return {"titulo": f"Solenidade do Santíssimo Corpo e Sangue de Cristo (Corpus Christi), {ano_dom}", "cor": "Branco", "ciclo": sufixo}
    if d == sagrado_coracao:
        return {"titulo": f"Solenidade do Sagrado Coração de Jesus, {ano_dom}", "cor": "Branco", "ciclo": sufixo}
    if d == cristo_rei:
        return {"titulo": f"Solenidade de Nosso Senhor Jesus Cristo, Rei do Universo, {ano_dom}", "cor": "Branco", "ciclo": sufixo}
    if d == batismo:
        return {"titulo": f"Festa do Batismo do Senhor, {ano_dom}", "cor": "Branco", "ciclo": sufixo}

    # Solenidades fixas (quando não conflitam com Quaresma/Semana Santa/Páscoa)
    if (d.month, d.day) in _FIXAS and not (cinzas <= d <= pentecostes):
        nome, cor = _FIXAS[(d.month, d.day)]
        return {"titulo": f"{nome}, {sufixo}", "cor": cor, "ciclo": sufixo}

    # Semana Santa
    if ramos < d < p - timedelta(days=3):
        return {"titulo": f"{regras.DIAS[regras.dia_semana(d)]}-feira da Semana Santa", "cor": "Roxo", "ciclo": sufixo}

    # Quaresma
    if cinzas < d < ramos:
        dom1_quaresma = cinzas + timedelta(days=4)
        if d < dom1_quaresma:
            return {"titulo": f"Depois das Cinzas, {ano_ferial}", "cor": "Roxo", "ciclo": sufixo}
        sem = (d - dom1_quaresma).days // 7 + 1
        cor = "Rosa" if eh_dom and sem == 4 else "Roxo"
        prefixo = f"{sem}º Domingo da Quaresma" if eh_dom else f"{sem}ª Semana da Quaresma"
        return {"titulo": f"{prefixo}, {sufixo}", "cor": cor, "ciclo": sufixo}

    # Tempo Pascal
    if p < d < pentecostes:
        sem = (d - p).days // 7 + 1
        prefixo = f"{sem}º Domingo da Páscoa" if eh_dom else f"{sem}ª Semana da Páscoa"
        return {"titulo": f"{prefixo}, {sufixo}", "cor": "Branco", "ciclo": sufixo}

    # Advento
    if advento1 <= d < date(d.year, 12, 25):
        sem = (d - advento1).days // 7 + 1
        cor = "Rosa" if eh_dom and sem == 3 else "Roxo"
        prefixo = f"{sem}º Domingo do Advento" if eh_dom else f"{sem}ª Semana do Advento"
        return {"titulo": f"{prefixo}, {sufixo}", "cor": cor, "ciclo": sufixo}

    # Tempo do Natal
    if d >= date(d.year, 12, 25) or d <= batismo:
        return {"titulo": f"Tempo do Natal, {sufixo}", "cor": "Branco", "ciclo": sufixo}

    # Tempo Comum (1ª parte: após o Batismo até terça de Carnaval)
    if batismo < d < cinzas:
        seg1 = batismo - timedelta(days=batismo.weekday())
        sem = (d - seg1).days // 7 + 1
    else:
        # Tempo Comum (2ª parte: após Pentecostes até Cristo Rei, contando de trás para frente a partir da 34ª semana)
        seg_cristo_rei = cristo_rei + timedelta(days=1)
        semanas_ate_fim = (seg_cristo_rei - (d - timedelta(days=d.weekday()))).days // 7
        sem = 34 - semanas_ate_fim + (1 if eh_dom else 0)
        sem = max(1, min(34, sem))

    prefixo = f"{sem}º Domingo do Tempo Comum" if eh_dom else f"{sem}ª Semana do Tempo Comum"
    return {"titulo": f"{prefixo}, {sufixo}", "cor": "Verde", "ciclo": sufixo}


def _normalizar_cor(cor: str | None, padrao: str = "Verde") -> str:
    if not cor:
        return padrao
    c = cor.strip().capitalize()
    for k in CORES_LITURGICAS:
        if c.startswith(k):
            return k
    if "roxo" in c.lower() or "violeta" in c.lower():
        return "Roxo"
    if "vermelh" in c.lower():
        return "Vermelho"
    if "branc" in c.lower() or "dourad" in c.lower():
        return "Branco"
    if "ros" in c.lower():
        return "Rosa"
    return padrao


def _extrair_item(bloco) -> dict | None:
    """Extrai {referencia, titulo, texto, refrao} tanto da v1 (dict) quanto da v2 (list[dict])."""
    if isinstance(bloco, list):
        bloco = bloco[0] if bloco else None
    if not isinstance(bloco, dict):
        return None
    ref = (bloco.get("referencia") or "").strip()
    if not ref or "não há" in ref.lower() or "nao ha" in ref.lower():
        return None
    return {
        "referencia": ref,
        "titulo": (bloco.get("titulo") or "").strip(),
        "refrao": (bloco.get("refrao") or "").strip(),
        "texto": (bloco.get("texto") or "").strip(),
    }


def _consultar_api_cnbb(d: date) -> dict | None:
    """Consulta a API pública da Liturgia Diária (v2 com fallback v1)."""
    if os.environ.get("COROINHAS_OFFLINE") == "1":
        return None
    urls = [
        f"https://liturgia.up.railway.app/v2/?dia={d.day:02d}&mes={d.month:02d}&ano={d.year}",
        f"https://liturgia.up.railway.app/?dia={d.day:02d}&mes={d.month:02d}&ano={d.year}",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CoroinhasLourdes/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                if resp.status != 200:
                    continue
                bruto = json.loads(resp.read().decode("utf-8"))
                if not isinstance(bruto, dict) or bruto.get("erro"):
                    continue
                return _converter_resposta_api(d, bruto)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            continue
    return None


def _converter_resposta_api(d: date, bruto: dict) -> dict:
    cal = calcular_calendario(d)
    titulo_api = (bruto.get("liturgia") or "").strip()
    ciclo = cal["ciclo"]
    if titulo_api:
        titulo = titulo_api if "Ano " in titulo_api else f"{titulo_api}, {ciclo}"
    else:
        titulo = cal["titulo"]

    cor = _normalizar_cor(bruto.get("cor"), cal["cor"])
    fonte = bruto.get("leituras") if isinstance(bruto.get("leituras"), dict) else bruto

    leituras = []
    for chave, rotulo in (
        ("primeiraLeitura", "1ª Leitura"),
        ("salmo", "Salmo"),
        ("segundaLeitura", "2ª Leitura"),
        ("evangelho", "Evangelho"),
    ):
        item = _extrair_item(fonte.get(chave))
        if item:
            leituras.append({"tipo": rotulo, **item})

    return {
        "data": d.isoformat(),
        "titulo": titulo,
        "cor": cor,
        "ciclo": ciclo,
        "leituras": leituras,
        "fonte": "cnbb",
    }


def enriquecer(registro: dict) -> dict:
    """Adiciona metadados visuais (dia da semana, data curta, cores hex) para os templates e JSON."""
    d = date.fromisoformat(registro["data"])
    cor = _normalizar_cor(registro.get("cor"))
    paleta = CORES_LITURGICAS[cor]
    return {
        **registro,
        "cor": cor,
        "cor_hex": paleta["hex"],
        "cor_escura": paleta["escuro"],
        "cor_borda": paleta["borda"],
        "cor_simbolo": paleta["simbolo"],
        "dia_nome": regras.DIAS[regras.dia_semana(d)],
        "data_curta": regras.data_curta(registro["data"]),
        "data_extenso": f"{d.day} de {regras.MESES[d.month - 1]}",
        "resumo_leituras": [l["referencia"] for l in registro.get("leituras", []) if l.get("referencia")],
    }


def liturgia_padrao(d: date) -> dict:
    """Liturgia calculada localmente quando a API externa ainda não tem a data ou está sem internet."""
    cal = calcular_calendario(d)
    return {
        "data": d.isoformat(),
        "titulo": cal["titulo"],
        "cor": cal["cor"],
        "ciclo": cal["ciclo"],
        "leituras": [],
        "fonte": "calculado",
    }
