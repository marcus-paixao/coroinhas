"""Rotas do projeto Escala dos Coroinhas: páginas (Jinja) e APIs (JSON) usadas pelo JS de cada tela."""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Response, abort, g, jsonify, render_template, request

from . import ABAS, bp, regras
from .padrao import CORES, EMOJIS
from .planilha import ler_planilha
from .repositorio import ErroCoroinhas, RepositorioCoroinhas

# COROINHAS_DADOS permite apontar outra pasta (ex.: testes) sem tocar nos dados reais
DADOS = Path(os.environ.get("COROINHAS_DADOS") or Path(__file__).resolve().parents[2] / "dados") / "coroinhas"
UPLOAD_DIR = DADOS / "uploads"          # temporário: só durante a importação
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

repo = RepositorioCoroinhas(DADOS / "coroinhas.db", carga_inicial=DADOS / "carga_inicial" / "backup-inicial.json")


def _quem() -> str:
    return (g.get("usuario") or {}).get("nome", "")


def _semana(valor: str | None) -> date:
    try:
        d = date.fromisoformat(valor) if valor else date.today()
    except ValueError:
        abort(404)
    return regras.inicio_semana(d)


def _corpo() -> dict:
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        raise ErroCoroinhas("Requisição inválida.")
    return d


def _mes_de(ref: date) -> tuple[date, date]:
    ini = ref.replace(day=1)
    return ini, (ini + timedelta(days=32)).replace(day=1) - timedelta(days=1)


def _arquivo_enviado(extensao: str) -> tuple[Path, str]:
    f = request.files.get("arquivo")
    if f is None or not f.filename:
        raise ErroCoroinhas("Nenhum arquivo recebido.")
    nome = Path(f.filename).name
    if not nome.lower().endswith(extensao):
        raise ErroCoroinhas(f"'{nome}': envie um arquivo {extensao}.")
    tmp = UPLOAD_DIR / f"{uuid.uuid4().hex}{extensao}"
    f.save(tmp)
    return tmp, nome


@bp.app_context_processor
def _ctx():
    """Menu e o contador de pendências da semana atual (badge da aba Escala). Vale também fora do projeto (ex.: Minha conta)."""
    if not g.get("usuario"):
        return {}
    seg = regras.inicio_semana(date.today())
    missas = repo.missas_entre(seg, seg + timedelta(days=6))
    badge = 0
    if missas:
        p = regras.pendencias(repo.membros(), missas, repo.config()["tipos_escalaveis"], seg)
        badge = p["vagas_abertas"] + len(p["sem_escala"])
    return {"abas": ABAS, "badge_escala": badge, "TIPOS": regras.TIPOS, "regras": regras}


@bp.errorhandler(ErroCoroinhas)
def _erro(e):
    return jsonify({"erro": str(e)}), 400


# ======================================================================================
# Páginas
# ======================================================================================
@bp.get("/")
def painel():
    hoje = date.today()
    seg = regras.inicio_semana(hoje)
    membros = repo.membros()
    cfg = repo.config()
    missas = repo.missas_entre(seg, seg + timedelta(days=6))
    pend = regras.pendencias(membros, missas, cfg["tipos_escalaveis"], seg)
    no_mes = regras.participacao(repo.missas_entre(*_mes_de(hoje)))
    ativos = [m for m in membros if m["tipo"] in cfg["tipos_escalaveis"] and not regras.esta_ausente(m, hoje.isoformat())]
    ranking = sorted(({"m": m, "vezes": no_mes.get(m["id"], 0)} for m in ativos), key=lambda r: (r["vezes"], r["m"]["apelido"]))
    hora = datetime.now().hour
    return render_template(
        "coroinhas/painel.html", aba="painel", hoje=hoje, semana=seg, missas=missas, pend=pend,
        titulo=regras.titulo_semana(seg, [m["data"] for m in missas]), ativos=ativos, ranking=ranking,
        max_vezes=max([r["vezes"] for r in ranking] + [1]), mes=regras.MESES[hoje.month - 1],
        aniversariantes=regras.aniversariantes(membros, hoje), tem_membros=bool(membros),
        saudacao="Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite")


@bp.get("/escala")
def escala():
    return render_template("coroinhas/escala.html", aba="escala", dados=_payload_semana(_semana(request.args.get("semana"))))


@bp.get("/equipe")
def equipe():
    hoje = date.today()
    no_mes = regras.participacao(repo.missas_entre(*_mes_de(hoje)))
    passadas = repo.missas_entre(hoje - timedelta(days=365), hoje)
    ultima = {}
    for missa in passadas:                       # em ordem de data: a última sobrescreve
        for i in regras.membros_da_missa(missa):
            ultima[i] = missa["data"]
    membros = []
    for m in repo.membros():
        membros.append({
            **m,
            "ausente_hoje": regras.esta_ausente(m, hoje.isoformat()),
            "idade": regras.idade(m["nascimento"], hoje) if m["nascimento"] else None,
            "faltam_aniversario": regras.dias_para_aniversario(m["nascimento"], hoje) if m["nascimento"] else None,
            "vezes_mes": no_mes.get(m["id"], 0),
            "ultima": ultima.get(m["id"]),
        })
    return render_template("coroinhas/equipe.html", aba="equipe", membros=membros)


@bp.get("/funcoes")
def funcoes():
    lista = repo.funcoes()
    return render_template("coroinhas/funcoes.html", aba="funcoes", funcoes=lista, funcoes_por_id={f["id"]: f for f in lista},
                           horarios=repo.horarios(), emojis=EMOJIS, cores=CORES)


@bp.get("/ajustes")
def ajustes():
    return render_template("coroinhas/ajustes.html", aba="ajustes", config=repo.config(), historico=repo.historico(), hoje=date.today(),
                           n_membros=len(repo.membros()))


# ======================================================================================
# APIs — escala
# ======================================================================================
def _payload_semana(seg: date) -> dict:
    hoje = date.today()
    membros = repo.membros()
    cfg = repo.config()
    missas = repo.missas_entre(seg, seg + timedelta(days=6))
    pend = regras.pendencias(membros, missas, cfg["tipos_escalaveis"], seg)
    ref = date.fromisoformat(missas[0]["data"]) if missas else seg + timedelta(days=5)
    no_mes = regras.participacao(repo.missas_entre(*_mes_de(ref)))
    ids = lambda lista: [m["id"] for m in lista]  # noqa: E731
    return {
        "semana": seg.isoformat(),
        "anterior": (seg - timedelta(days=7)).isoformat(),
        "proxima": (seg + timedelta(days=7)).isoformat(),
        "atual": regras.inicio_semana(hoje).isoformat(),
        "titulo": regras.titulo_semana(seg, [m["data"] for m in missas]),
        "distancia": regras.distancia_semana(seg, hoje),
        "missas": missas,
        "funcoes": repo.funcoes(),
        "horarios": repo.horarios(),
        "membros": [{k: m[k] for k in ("id", "nome", "apelido", "tipo", "ausente", "motivo_ausencia", "ausente_ate",
                                       "cor", "iniciais")} | {"vezes_mes": no_mes.get(m["id"], 0)} for m in membros],
        "tipos_escalaveis": cfg["tipos_escalaveis"],
        "pendencias": {
            "total_vagas": pend["total_vagas"], "vagas_abertas": pend["vagas_abertas"],
            "sem_escala": ids(pend["sem_escala"]), "ausentes": ids(pend["ausentes"]),
            "escalados_ausentes": ids(pend["escalados_ausentes"]), "duplicados": pend["duplicados"],
        },
        "horarios_faltando": repo.horarios_faltando(seg),
        "tem_semana_anterior": bool(repo.missas_entre(seg - timedelta(days=7), seg - timedelta(days=1))),
    }


@bp.get("/api/semana")
def api_semana():
    return jsonify(_payload_semana(_semana(request.args.get("semana"))))


@bp.post("/api/semana/gerar")
def api_gerar_semana():
    return jsonify({"criadas": repo.gerar_semana(_semana(_corpo().get("semana")), _quem())})


@bp.post("/api/semana/copiar-anterior")
def api_copiar_anterior():
    return jsonify({"copiadas": repo.copiar_semana_anterior(_semana(_corpo().get("semana")), _quem())})


@bp.get("/api/semana/whatsapp")
def api_whatsapp():
    seg = _semana(request.args.get("semana"))
    missas = repo.missas_entre(seg, seg + timedelta(days=6))
    texto = regras.texto_whatsapp(missas, {m["id"]: m for m in repo.membros()}, {f["id"]: f for f in repo.funcoes()},
                                  regras.titulo_semana(seg, [m["data"] for m in missas]))
    return jsonify({"texto": texto})


@bp.post("/api/escalas/<escala_id>")
def api_escalar(escala_id: str):
    membro = _corpo().get("membro_id") or None
    return jsonify({"anterior": repo.escalar(escala_id, membro, _quem())})


@bp.post("/api/missas")
def api_missa_nova():
    return jsonify({"id": repo.salvar_missa(_corpo(), usuario=_quem())}), 201


@bp.put("/api/missas/<missa_id>")
def api_missa_editar(missa_id: str):
    return jsonify({"id": repo.salvar_missa(_corpo(), missa_id, _quem())})


@bp.delete("/api/missas/<missa_id>")
def api_missa_remover(missa_id: str):
    repo.remover_missa(missa_id, _quem())
    return jsonify({"ok": True})


# ======================================================================================
# APIs — equipe, funções e horários
# ======================================================================================
@bp.post("/api/membros")
def api_membro_novo():
    return jsonify({"membro": repo.salvar_membro(_corpo(), usuario=_quem())}), 201


@bp.put("/api/membros/<membro_id>")
def api_membro_editar(membro_id: str):
    return jsonify({"membro": repo.salvar_membro(_corpo(), membro_id, _quem())})


@bp.delete("/api/membros/<membro_id>")
def api_membro_remover(membro_id: str):
    repo.remover_membro(membro_id, _quem())
    return jsonify({"ok": True})


@bp.post("/api/membros/<membro_id>/ausencia")
def api_ausencia(membro_id: str):
    d = _corpo()
    repo.definir_ausencia(membro_id, bool(d.get("ausente")), d.get("motivo"), d.get("ate"), _quem())
    return jsonify({"ok": True})


@bp.post("/api/funcoes")
def api_funcao_nova():
    return jsonify({"funcao": repo.salvar_funcao(_corpo(), usuario=_quem())}), 201


@bp.put("/api/funcoes/<funcao_id>")
def api_funcao_editar(funcao_id: str):
    return jsonify({"funcao": repo.salvar_funcao(_corpo(), funcao_id, _quem())})


@bp.delete("/api/funcoes/<funcao_id>")
def api_funcao_remover(funcao_id: str):
    repo.remover_funcao(funcao_id, _quem())
    return jsonify({"ok": True})


@bp.post("/api/horarios")
def api_horario_novo():
    repo.salvar_horario(_corpo(), usuario=_quem())
    return jsonify({"ok": True}), 201


@bp.put("/api/horarios/<horario_id>")
def api_horario_editar(horario_id: str):
    repo.salvar_horario(_corpo(), horario_id, _quem())
    return jsonify({"ok": True})


@bp.delete("/api/horarios/<horario_id>")
def api_horario_remover(horario_id: str):
    repo.remover_horario(horario_id, _quem())
    return jsonify({"ok": True})


# ======================================================================================
# APIs — planilha, backup e ajustes
# ======================================================================================
@bp.post("/api/planilha")
def api_planilha():
    tmp, nome = _arquivo_enviado(".xlsx")
    try:
        novos, atualizados = repo.importar_membros(ler_planilha(tmp), nome, _quem())
    finally:
        tmp.unlink(missing_ok=True)
    return jsonify({"novos": novos, "atualizados": atualizados})


@bp.get("/backup")
def backup():
    nome = f"backup-coroinhas-{date.today().isoformat()}.json"
    return Response(json.dumps(repo.exportar(), ensure_ascii=False, indent=2), mimetype="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@bp.post("/api/backup")
def api_restaurar():
    tmp, nome = _arquivo_enviado(".json")
    try:
        try:
            conteudo = json.loads(tmp.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ErroCoroinhas("O arquivo não é um JSON válido.") from None
        return jsonify(repo.restaurar(conteudo, _quem(), origem=nome))
    finally:
        tmp.unlink(missing_ok=True)


@bp.post("/api/config")
def api_config():
    return jsonify(repo.salvar_config(_corpo(), _quem()))


@bp.post("/api/apagar-tudo")
def api_apagar_tudo():
    repo.apagar_tudo(_quem())
    return jsonify({"ok": True})
