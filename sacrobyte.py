"""
SacroByte — Assistente de IA do Portal Coroinhas (Google Gemini `gemini-2.5-flash` via `google-genai`).
"""
from __future__ import annotations

import os
from datetime import date, timedelta

from flask import Blueprint, jsonify, request, session

from projetos.coroinhas import regras
from projetos.coroinhas.rotas import repo

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

bp = Blueprint("sacrobyte", __name__)

MODELO_GEMINI = "gemini-2.5-flash"
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
        datas_lit = sorted({m["data"] for m in missas}) or [
            (seg + timedelta(days=5)).isoformat(),
            (seg + timedelta(days=6)).isoformat(),
        ]
        lits = repo.liturgias_datas(datas_lit)
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


def _chamar_gemini(mensagem: str, historico: list[dict]) -> str:
    chave = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not chave:
        raise RuntimeError(
            "A chave `GEMINI_API_KEY` ainda não foi configurada! "
            "Adicione no arquivo `.env` (no PC) ou na aba **Variables** do Railway para ativar o SacroByte."
        )

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=chave)
    conteudos = []
    for item in historico:
        papel = "model" if item.get("role") == "model" else "user"
        texto = str(item.get("text") or "").strip()
        if texto:
            conteudos.append(types.Content(role=papel, parts=[types.Part.from_text(text=texto)]))
    conteudos.append(types.Content(role="user", parts=[types.Part.from_text(text=mensagem)]))

    resposta = client.models.generate_content(
        model=MODELO_GEMINI,
        contents=conteudos,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION_BASE + _contexto_atual(),
            temperature=0.7,
            max_output_tokens=700,
        ),
    )
    return (resposta.text or "Perdão, deu um pequeno soluço nos meus circuitos litúrgicos. Pode repetir?").strip()


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
