"""
SacroByte — Assistente de IA do Portal Coroinhas (Google Gemini `gemini-2.5-flash` via `google-genai`).
"""
from __future__ import annotations

import os
import re
from datetime import date, timedelta
from pathlib import Path

from flask import Blueprint, jsonify, request, session

from projetos.coroinhas import regras
from projetos.coroinhas.rotas import _liturgias_da_escala, repo

ENV_PATH = Path(__file__).resolve().parent / ".env"

try:
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH, override=True)
except ImportError:
    pass

bp = Blueprint("sacrobyte", __name__)

MODELOS_GEMINI = (
    os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-flash-lite",
)
MAX_HISTORICO = 6          # últimas 6 mensagens na sessão (mantém o cookie leve)
MAX_CHARS_HISTORICO = 360  # truncamento por item salvo no cookie de sessão

SYSTEM_INSTRUCTION_BASE = """Você é o **SacroByte**, o assistente virtual oficial do **Portal Coroinhas** da Basílica Nossa Senhora de Lourdes (Vila Isabel, Rio de Janeiro).

Sua personalidade e missão:
- Você é um "servidor do altar digital": acolhedor, dedicado, prestativo e bem-humorado, inspirado em São Tarcísio (padroeiro dos coroinhas).
- Misture de forma leve, respeitosa e divertida expressões do universo litúrgico/coroinhas (altar, túnica, batina, sobrepeliz, turíbulo, naveta, círio, missal, sineta, amém, paz e bem) com termos de tecnologia e dados (requisição, pacote, servidor, banco de dados, byte, cache, deploy, ping).
  Exemplos naturais para usar ocasionalmente: "Pronto para servir cada requisição do Portal!", "Abençoando os dados por aqui...", "Pacote entregue com sucesso, amém!", "Turíbulo aquecido e servidor online!".
- Suas respostas devem ser sempre claras, objetivas, curtas (1 a 3 parágrafos curtos ou lista direta) e muito úteis para a coordenação, cerimoniários e coroinhas.
- Você conhece todas as funções do altar (Turíbulo, Naveta, Cruz Processional, Ceroferários/Velas, Missal, Microfone, Galhetas, Lavabo, Sineta), objetos litúrgicos, tempos e cores litúrgicas (Verde, Branco, Vermelho, Roxo e Rosa), além de ajudar a usar o Portal Coroinhas (abas Painel, Escala, Liturgia, Coroinhas/Membros, Funções & Missas e Ajustes & Backup).
"""


def _contexto_atual() -> str:
    """Resumo rápido da semana atual no banco para o SacroByte responder perguntas sobre a escala e a liturgia."""
    try:
        hoje = date.today()
        seg = regras.inicio_semana(hoje)
        membros = repo.membros()
        missas = repo.missas_entre(seg, seg + timedelta(days=6))
        cfg = repo.config()
        pend = regras.pendencias(membros, missas, cfg["tipos_escalaveis"], seg)
        lits = _liturgias_da_escala(seg, missas)
        resumo_lit = "; ".join(
            f"{l['dia_nome']} {l['data_curta']}: {l['titulo']} (Cor {l['cor']}, leituras: {', '.join(l['resumo_leituras']) or 'a consultar'})"
            for l in lits
        )
        sem_escala = ", ".join(m["apelido"] for m in pend["sem_escala"][:15]) or "ninguém (todos escalados)"
        ausentes = ", ".join(m["apelido"] for m in pend["ausentes"][:15]) or "ninguém"
        return (
            f"\n\nContexto em tempo real do Portal hoje ({hoje.isoformat()}):\n"
            f"- Total de membros cadastrados: {len(membros)}\n"
            f"- Missas na semana atual ({regras.titulo_semana(seg, [m['data'] for m in missas])}): {len(missas)} missa(s), "
            f"{pend['vagas_abertas']} de {pend['total_vagas']} vaga(s) em aberto.\n"
            f"- Disponíveis ainda sem escala nesta semana: {sem_escala}.\n"
            f"- Marcados como ausentes: {ausentes}.\n"
            f"- Liturgia do fim de semana: {resumo_lit}."
        )
    except Exception:
        return ""


def _ler_chave() -> str:
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_PATH, override=True)
    except ImportError:
        if ENV_PATH.exists():
            for linha in ENV_PATH.read_text(encoding="utf-8").splitlines():
                linha = linha.strip()
                if linha.startswith("GEMINI_API_KEY="):
                    return linha.split("=", 1)[1].strip().strip("\"'")
    return (os.environ.get("GEMINI_API_KEY") or "").strip()


_CONFIG_FUNCIONANDO: tuple[bool, str] | None = None


def _chamar_gemini(mensagem: str, historico: list[dict]) -> str:
    global _CONFIG_FUNCIONANDO
    chave = _ler_chave()
    if not chave:
        raise RuntimeError(
            "A chave `GEMINI_API_KEY` ainda não foi configurada! "
            "Adicione no arquivo `.env` (no PC) ou na aba **Variables** do Railway para ativar o SacroByte."
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise RuntimeError(
            "A biblioteca `google-genai` ainda não está instalada neste Python local. "
            "Rode no terminal: `.\\.venv\\Scripts\\pip install -r requirements.txt`"
        ) from None

    conteudos = []
    for item in historico:
        papel = "model" if item.get("role") == "model" else "user"
        texto = str(item.get("text") or "").strip()
        if texto:
            conteudos.append(types.Content(role=papel, parts=[types.Part.from_text(text=texto)]))
    conteudos.append(types.Content(role="user", parts=[types.Part.from_text(text=mensagem)]))

    cfg = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION_BASE + _contexto_atual(),
        temperature=0.7,
        max_output_tokens=700,
    )

    # Chaves "AQ...." são do Vertex AI Express Mode; chaves "AIza..." são do Google AI Studio
    modos = [True, False] if chave.startswith("AQ.") else [False, True]
    tentativas: list[tuple[bool, str]] = []
    if _CONFIG_FUNCIONANDO:
        tentativas.append(_CONFIG_FUNCIONANDO)
    for m in modos:
        for mod in MODELOS_GEMINI:
            if (m, mod) not in tentativas:
                tentativas.append((m, mod))

    ultimo_erro = None
    idx = 0
    while idx < len(tentativas):
        usar_vertex, modelo = tentativas[idx]
        idx += 1
        try:
            client = genai.Client(vertexai=True, api_key=chave) if usar_vertex else genai.Client(api_key=chave)
            resposta = client.models.generate_content(model=modelo, contents=conteudos, config=cfg)
            _CONFIG_FUNCIONANDO = (usar_vertex, modelo)
            return (resposta.text or "Perdão, deu um pequeno soluço nos meus circuitos litúrgicos. Pode repetir?").strip()
        except Exception as e:
            ultimo_erro = e
            # Se a API indicar que o modelo mudou (ex: "Please update your code to use models/gemini-..."), adiciona na fila
            for sugerido in re.findall(r"use models/([a-zA-Z0-9._-]+)", str(e)):
                if (usar_vertex, sugerido) not in tentativas:
                    tentativas.insert(idx, (usar_vertex, sugerido))
            continue
    raise RuntimeError(f"Erro na API do Gemini: {ultimo_erro}") from None


@bp.post("/chat")
def chat():
    dados = request.get_json(silent=True) or {}
    mensagem = str(dados.get("mensagem") or dados.get("message") or "").strip()
    if not mensagem:
        return jsonify({"erro": "Envie uma mensagem para o SacroByte."}), 400
    if len(mensagem) > 1500:
        return jsonify({"erro": "Mensagem muito longa (máximo de 1500 caracteres)."}), 400

    historico = list(session.get("sacrobyte_historico") or [])
    try:
        resposta = _chamar_gemini(mensagem, historico)
    except RuntimeError as e:
        return jsonify({"erro": str(e)}), 503
    except Exception:
        return jsonify({"erro": "Não consegui conectar ao servidor do Gemini agora. Confira sua GEMINI_API_KEY e tente novamente!"}), 502

    historico.append({"role": "user", "text": mensagem[:MAX_CHARS_HISTORICO]})
    historico.append({"role": "model", "text": resposta[:MAX_CHARS_HISTORICO]})
    session["sacrobyte_historico"] = historico[-MAX_HISTORICO:]

    return jsonify({"resposta": resposta})


@bp.post("/chat/limpar")
def limpar_chat():
    session.pop("sacrobyte_historico", None)
    return jsonify({"ok": True})
