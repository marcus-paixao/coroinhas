"""Testes do sistema (rodar com: python -m pytest tests). Usa uma pasta de dados temporária."""
import os
import tempfile
from datetime import date, timedelta

os.environ["COROINHAS_DADOS"] = tempfile.mkdtemp(prefix="coroinhas-teste-")   # antes de importar o app
os.environ["COROINHAS_OFFLINE"] = "1"

import pytest  # noqa: E402

import acesso  # noqa: E402
from app import app  # noqa: E402
from projetos.coroinhas import regras  # noqa: E402
from projetos.coroinhas.rotas import repo  # noqa: E402

API = "/api"
SEGUNDA = date(2026, 10, 26)   # semana de 31/10 (sáb) e 01/11 (dom)


@pytest.fixture
def cliente():
    repo.apagar_tudo()
    acesso.usuarios.salvar("coord", "Coordenação Teste", "senha-boa-123")
    c = app.test_client()
    assert c.post("/entrar", data={"login": "coord", "senha": "senha-boa-123"}).status_code == 302
    return c


def novo_membro(c, nome, **extra):
    r = c.post(f"{API}/membros", json={"nome": nome, **extra})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["membro"]


# ------------------------------------------------------------------ acesso
def test_exige_login():
    c = app.test_client()
    assert c.get("/").status_code == 302
    assert c.get(f"{API}/semana").status_code == 401


def test_senha_errada():
    acesso.usuarios.salvar("coord", "Coordenação Teste", "senha-boa-123")
    r = app.test_client().post("/entrar", data={"login": "coord", "senha": "errada"})
    assert r.status_code == 401 and "incorretos" in r.get_data(as_text=True)


def test_bloqueia_outra_origem(cliente):
    r = cliente.post(f"{API}/membros", json={"nome": "X"}, headers={"Origin": "https://site-malicioso.com"})
    assert r.status_code == 403


# ------------------------------------------------------------------ contas
CONTAS = "/conta/api/usuarios"


def entrar(login, senha):
    c = app.test_client()
    assert c.post("/entrar", data={"login": login, "senha": senha}).status_code == 302
    return c


@pytest.fixture
def equipe(cliente):
    """Coordenador logado (cliente) + uma conta comum recém-criada pela tela."""
    for u in acesso.usuarios.listar():
        if u["login"] != "coord":
            acesso.usuarios.remover(u["id"])
    r = cliente.post(CONTAS, json={"login": "Joana", "nome": "Joana", "senha": "senha-da-joana", "coordenador": False})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["conta"]


def test_trocar_propria_senha(equipe):
    c = entrar("joana", "senha-da-joana")
    outro_aparelho = entrar("joana", "senha-da-joana")
    assert "A senha atual não confere" in c.post("/conta/api/senha", json={"atual": "errada", "nova": "nova-senha-1"}).get_json()["erro"]
    assert c.post("/conta/api/senha", json={"atual": "senha-da-joana", "nova": "curta"}).status_code == 400
    assert c.post("/conta/api/senha", json={"atual": "senha-da-joana", "nova": "nova-senha-1"}).status_code == 200
    assert c.get("/conta").status_code == 200                                   # continua logada aqui
    assert outro_aparelho.get(f"{API}/semana").status_code == 401             # o outro aparelho cai
    assert app.test_client().post("/entrar", data={"login": "joana", "senha": "senha-da-joana"}).status_code == 401
    entrar("joana", "nova-senha-1")


def test_coordenador_gerencia_contas(cliente, equipe):
    assert cliente.post(CONTAS, json={"login": "joana", "nome": "Outra", "senha": "12345678"}).status_code == 400   # repetido
    assert cliente.post(CONTAS, json={"login": "com espaço", "nome": "X", "senha": "12345678"}).status_code == 400
    assert cliente.post(CONTAS, json={"login": "pedro", "nome": "Pedro", "senha": "curta"}).status_code == 400
    pagina = cliente.get("/conta").get_data(as_text=True)
    assert "Contas de acesso" in pagina and "joana" in pagina

    joana = entrar("joana", "senha-da-joana")
    assert joana.post(CONTAS, json={"login": "pedro", "nome": "Pedro", "senha": "12345678"}).status_code == 403
    assert joana.delete(f"{CONTAS}/{equipe['id']}").status_code == 403
    assert "Nova conta" not in joana.get("/conta").get_data(as_text=True)
    assert joana.get("/").status_code == 200                                    # usa o sistema normalmente

    # coordenador redefine a senha e promove: a sessão antiga da Joana cai
    r = cliente.put(f"{CONTAS}/{equipe['id']}", json={"nome": "Joana Silva", "coordenador": True, "senha": "senha-nova-99"})
    assert r.status_code == 200
    assert joana.get("/conta").status_code == 302
    u = acesso.usuarios.obter(equipe["id"])
    assert u["nome"] == "Joana Silva" and u["coordenador"]

    # sem senha no corpo: mantém a senha
    assert cliente.put(f"{CONTAS}/{equipe['id']}", json={"nome": "Joana", "coordenador": False}).status_code == 200
    joana = entrar("joana", "senha-nova-99")

    # ninguém tira o próprio acesso de coordenador nem remove a si mesmo
    coord = acesso.usuarios.verificar("coord", "senha-boa-123")
    assert cliente.delete(f"{CONTAS}/{coord['id']}").status_code == 400
    assert cliente.put(f"{CONTAS}/{coord['id']}", json={"nome": "Coord", "coordenador": False}).status_code == 200
    assert acesso.usuarios.obter(coord["id"])["coordenador"]

    assert cliente.delete(f"{CONTAS}/{equipe['id']}").status_code == 200
    assert joana.get("/conta").status_code == 302
    assert acesso.usuarios.verificar("joana", "senha-nova-99") is None


def test_apk_cria_o_primeiro_coordenador(monkeypatch, tmp_path):
    monkeypatch.setattr(acesso, "usuarios", acesso.Usuarios(tmp_path / "u.db"))
    c = app.test_client()
    assert "Criar conta e entrar" not in c.get("/entrar").get_data(as_text=True)     # no PC: só pelo terminal
    assert c.post("/entrar", data={"nome": "X", "login": "x", "senha": "12345678", "repetir": "12345678"}).status_code == 401

    monkeypatch.setattr(acesso, "APK", True)
    assert "Criar conta e entrar" in c.get("/entrar").get_data(as_text=True)
    form = {"nome": "Marcus", "login": "marcus", "senha": "senha-forte-1", "repetir": "outra-senha"}
    assert "não conferem" in c.post("/entrar", data=form).get_data(as_text=True)
    assert c.post("/entrar", data={**form, "repetir": form["senha"]}).status_code == 302
    assert c.get("/conta").status_code == 200 and acesso.usuarios.listar()[0]["coordenador"]
    # já existe conta: volta a ser login normal
    assert "Criar conta e entrar" not in app.test_client().get("/entrar").get_data(as_text=True)


def test_banco_antigo_vira_coordenador(tmp_path):
    import sqlite3
    con = sqlite3.connect(tmp_path / "u.db")
    con.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT UNIQUE NOT NULL, nome TEXT NOT NULL, senha_hash TEXT NOT NULL)")
    con.execute("INSERT INTO usuarios (login, nome, senha_hash) VALUES ('velho', 'Velho', 'x')")
    con.commit()
    con.close()
    assert acesso.Usuarios(tmp_path / "u.db").listar()[0]["coordenador"] is True


@pytest.mark.parametrize("pagina", ["/", "/escala", "/liturgia", "/membros", "/funcoes", "/ajustes", "/conta"])
def test_paginas_abrem(cliente, pagina):
    novo_membro(cliente, "Lívia Exemplo Teste", nascimento="2014-04-15")
    cliente.post(f"{API}/semana/gerar", json={"semana": date.today().isoformat()})
    assert cliente.get(pagina).status_code == 200


# ------------------------------------------------------------------ escala
def test_fluxo_da_escala(cliente):
    beatriz = novo_membro(cliente, "beatriz exemplo ficticia de souza")
    assert beatriz["nome"] == "Beatriz Exemplo Ficticia de Souza" and beatriz["apelido"] == "Beatriz"
    davi = novo_membro(cliente, "Davi Exemplo")

    r = cliente.post(f"{API}/semana/gerar", json={"semana": SEGUNDA.isoformat()})
    assert r.get_json()["criadas"] == 3                         # sáb 16h, dom 10h, dom 18h
    assert cliente.post(f"{API}/semana/gerar", json={"semana": SEGUNDA.isoformat()}).get_json()["criadas"] == 0

    d = cliente.get(f"{API}/semana?semana=2026-10-31").get_json()   # qualquer dia cai na mesma semana
    assert d["semana"] == "2026-10-26" and d["titulo"] == "31/10 e 01/11"
    assert d["pendencias"]["total_vagas"] == 20 and d["pendencias"]["vagas_abertas"] == 20
    assert set(d["pendencias"]["sem_escala"]) == {beatriz["id"], davi["id"]}

    vaga = d["missas"][0]["vagas"][0]["id"]
    assert cliente.post(f"{API}/escalas/{vaga}", json={"membro_id": beatriz["id"]}).get_json()["anterior"] is None
    d = cliente.get(f"{API}/semana?semana=2026-10-26").get_json()
    assert d["pendencias"]["sem_escala"] == [davi["id"]] and d["pendencias"]["vagas_abertas"] == 19

    # Davi ausente: some do alerta
    cliente.post(f"{API}/membros/{davi['id']}/ausencia", json={"ausente": True, "motivo": "Viagem"})
    d = cliente.get(f"{API}/semana?semana=2026-10-26").get_json()
    assert d["pendencias"]["sem_escala"] == [] and d["pendencias"]["ausentes"] == [davi["id"]]

    texto = cliente.get(f"{API}/semana/whatsapp?semana=2026-10-26").get_json()["texto"]
    assert "*Beatriz*" in texto and "Sábado 31/10 · 16h" in texto and "_a definir_" in texto


def test_ausencia_expira(cliente):
    m = novo_membro(cliente, "Ana Clara", ausente=True, ausente_ate="2026-10-30")
    membro = next(x for x in repo.membros() if x["id"] == m["id"])
    assert regras.esta_ausente(membro, "2026-10-30") and not regras.esta_ausente(membro, "2026-10-31")


def test_editar_missa_mantem_quem_estava_escalado(cliente):
    m = novo_membro(cliente, "Felipe Exemplo")
    cliente.post(f"{API}/semana/gerar", json={"semana": SEGUNDA.isoformat()})
    missa = repo.missas_entre(SEGUNDA, SEGUNDA + timedelta(days=6))[0]
    v0, v1 = missa["vagas"][0], missa["vagas"][1]
    cliente.post(f"{API}/escalas/{v1['id']}", json={"membro_id": m["id"]})
    r = cliente.put(f"{API}/missas/{missa['id']}", json={
        "data": missa["data"], "hora": "17:00", "titulo": "Missa com Crisma", "reservas": 1,
        "vagas": [{"id": v1["id"], "funcoes": ["cruz"]}, {"id": v0["id"], "funcoes": v0["funcoes"]}, {"funcoes": ["vela"]}]})
    assert r.status_code == 200
    nova = next(x for x in repo.missas_entre(SEGUNDA, SEGUNDA + timedelta(days=6)) if x["id"] == missa["id"])
    assert nova["hora"] == "17:00" and len(nova["vagas"]) == 3 and len(nova["reservas"]) == 1
    assert nova["vagas"][0]["membro_id"] == m["id"] and nova["vagas"][0]["funcoes"] == ["cruz"]


def test_remover_funcao_limpa_as_vagas(cliente):
    cliente.post(f"{API}/semana/gerar", json={"semana": SEGUNDA.isoformat()})
    assert cliente.delete(f"{API}/funcoes/lavabo").status_code == 200
    assert all("lavabo" not in v for h in repo.horarios() for v in h["vagas"])
    assert all("lavabo" not in v["funcoes"] for m in repo.missas_entre(SEGUNDA, SEGUNDA + timedelta(days=6)) for v in m["vagas"])


def test_remover_membro_libera_a_vaga(cliente):
    m = novo_membro(cliente, "Enzo Exemplo")
    cliente.post(f"{API}/semana/gerar", json={"semana": SEGUNDA.isoformat()})
    vaga = repo.missas_entre(SEGUNDA, SEGUNDA + timedelta(days=6))[0]["vagas"][0]
    cliente.post(f"{API}/escalas/{vaga['id']}", json={"membro_id": m["id"]})
    cliente.delete(f"{API}/membros/{m['id']}")
    assert repo.missas_entre(SEGUNDA, SEGUNDA + timedelta(days=6))[0]["vagas"][0]["membro_id"] is None


@pytest.mark.parametrize("corpo, erro", [
    ({"nome": ""}, "Nome"),
    ({"nome": "Fulano", "tipo": "bispo"}, "inválida"),
    ({"nome": "Fulano", "nascimento": "31/12/2010"}, "data inválida"),
])
def test_validacao_membro(cliente, corpo, erro):
    r = cliente.post(f"{API}/membros", json=corpo)
    assert r.status_code == 400 and erro in r.get_json()["erro"]


# ------------------------------------------------------------------ backup
def test_backup_ida_e_volta(cliente):
    m = novo_membro(cliente, "Maria Clara Exemplo")
    cliente.post(f"{API}/semana/gerar", json={"semana": SEGUNDA.isoformat()})
    vaga = repo.missas_entre(SEGUNDA, SEGUNDA + timedelta(days=6))[0]["vagas"][0]
    cliente.post(f"{API}/escalas/{vaga['id']}", json={"membro_id": m["id"]})
    backup = repo.exportar()
    repo.apagar_tudo()
    assert repo.membros() == []
    repo.restaurar(backup)
    assert [x["apelido"] for x in repo.membros()] == ["Maria Clara"]
    assert repo.missas_entre(SEGUNDA, SEGUNDA + timedelta(days=6))[0]["vagas"][0]["membro_id"] == m["id"]


def test_restaura_backup_da_versao_react(cliente):
    v1 = {"versao": 1, "membros": [{"id": "m01", "nome": "Vitória", "apelido": "Vitória", "tipo": "coroinha", "ausente": True,
                                     "motivoAusencia": "Provas", "ausenteAte": "2026-11-15"}],
          "missas": [{"id": "d10", "data": "2026-10-25", "hora": "10:00",
                      "vagas": [{"id": "v1", "funcoes": ["vela", "patena"], "membroId": "m01"}], "reservas": [None, "m01"]}]}
    assert repo.restaurar(v1) == {"membros": 1, "missas": 1}
    m = repo.membros()[0]
    assert m["motivo_ausencia"] == "Provas" and m["ausente_ate"] == "2026-11-15"
    missa = repo.missas_entre(date(2026, 10, 25), date(2026, 10, 25))[0]
    assert missa["vagas"][0] == {"id": missa["vagas"][0]["id"], "funcoes": ["vela", "patena"], "membro_id": "m01"}
    assert [r["membro_id"] for r in missa["reservas"]] == [None, "m01"]
    assert len(repo.funcoes()) == 9 and len(repo.horarios()) == 3          # sem funções no backup: padrão


def test_backup_invalido_nao_muda_nada(cliente):
    novo_membro(cliente, "Tiago Exemplo")
    with pytest.raises(Exception):
        repo.restaurar({"membros": [{"nome": "Ok"}], "missas": [{"data": "ontem", "hora": "10:00", "vagas": [], "reservas": []}]})
    assert [m["apelido"] for m in repo.membros()] == ["Tiago"]


# ------------------------------------------------------------------ regras
def test_regras():
    assert regras.titulo_semana(date(2026, 10, 19), ["2026-10-24", "2026-10-25", "2026-10-25"]) == "24 e 25 de outubro"
    assert regras.sugerir_apelido("Maria Júlia Exemplo") == "Maria Júlia"
    assert regras.sugerir_apelido("Rafael Exemplo", ["Rafael"]) == "Rafael Exemplo"
    assert regras.dias_para_aniversario("2014-04-15", date(2026, 4, 15)) == 0
    assert regras.dias_para_aniversario("2012-02-29", date(2026, 3, 2)) == 364
    assert regras.formatar_hora("18:30") == "18h30" and regras.formatar_hora("10:00") == "10h"


def test_liturgia(cliente):
    from projetos.coroinhas import liturgia
    sab = liturgia.calcular_calendario(date(2026, 11, 14))
    assert sab["titulo"] == "32ª Semana do Tempo Comum, Ano Par (II)" and sab["cor"] == "Verde"
    dom = liturgia.calcular_calendario(date(2026, 11, 15))
    assert dom["titulo"] == "33º Domingo do Tempo Comum, Ano A" and dom["cor"] == "Verde"

    r = cliente.put(f"{API}/liturgia/2026-11-15", json={
        "titulo": "33º Domingo do Tempo Comum, Ano A",
        "cor": "Verde",
        "leituras": [
            {"tipo": "1ª Leitura", "referencia": "Pr 31,10-13.19-20.30-31"},
            {"tipo": "Salmo", "referencia": "Sl 127(128),1-2.3.4-5 (R. 1a)"},
            {"tipo": "2ª Leitura", "referencia": "1Ts 5,1-6"},
            {"tipo": "Evangelho", "referencia": "Mt 25,14-30"},
        ],
    })
    assert r.status_code == 200
    dados = r.get_json()["liturgia"]
    assert "Mt 25,14-30" in dados["resumo_leituras"]
    # Como a missa fixa de sábado é às 16h (>= 15h), o sábado e o domingo usam a mesma liturgia de domingo
    html = cliente.get("/liturgia?semana=2026-11-09").get_data(as_text=True)
    assert "Sábado (após 15h) e Domingo" in html and "Mt 25,14-30" in html

    # Se houver uma missa no sábado antes das 15h (ex.: 10:00) junto com as missas do fim de semana, aparece também a liturgia própria de sábado
    cliente.post(f"{API}/semana/gerar", json={"semana": "2026-11-09"})
    cliente.post(f"{API}/missas", json={"data": "2026-11-14", "hora": "10:00", "titulo": "Missa da manhã", "reservas": 0, "vagas": []})
    sem_payload = cliente.get(f"{API}/semana?semana=2026-11-09").get_json()
    datas_lit = [l["data"] for l in sem_payload["liturgias"]]
    assert "2026-11-14" in datas_lit and "2026-11-15" in datas_lit


def test_sacrobyte_chat(cliente, monkeypatch):
    import sacrobyte
    assert app.test_client().post("/chat", json={"mensagem": "Oi"}).status_code == 401
    assert cliente.post("/chat", json={"mensagem": ""}).status_code == 400

    historico_recebido = []
    monkeypatch.setattr(
        sacrobyte,
        "_chamar_gemini",
        lambda msg, hist: (historico_recebido.append(list(hist)) or f"Paz e bem! Recebi: {msg}"),
    )
    r1 = cliente.post("/chat", json={"mensagem": "Qual a cor litúrgica?"})
    assert r1.status_code == 200 and "Paz e bem!" in r1.get_json()["resposta"]
    assert historico_recebido[0] == []

    r2 = cliente.post("/chat", json={"mensagem": "E o evangelho?"})
    assert r2.status_code == 200
    assert len(historico_recebido[1]) == 2 and historico_recebido[1][0]["text"] == "Qual a cor litúrgica?"

    assert cliente.post("/chat/limpar", json={}).status_code == 200
    cliente.post("/chat", json={"mensagem": "Nova conversa"})
    assert historico_recebido[2] == []


def test_cadastro_na_pagina_e_permissoes_papeis(monkeypatch, tmp_path):
    monkeypatch.setattr(acesso, "usuarios", acesso.Usuarios(tmp_path / "papeis.db"))
    c1 = app.test_client()
    # 1ª conta criada pela aba "Criar conta" vira Coordenador(a) automaticamente
    assert "Criar conta e entrar" in c1.get("/entrar?modo=criar").get_data(as_text=True)
    r1 = c1.post("/entrar", data={"acao": "criar", "nome": "Marcus", "login": "marcus", "senha": "senha-forte-1", "repetir": "senha-forte-1"})
    assert r1.status_code == 302
    contas = acesso.usuarios.listar()
    assert len(contas) == 1 and contas[0]["coordenador"] is True and contas[0]["papel"] == "coordenacao"

    # 2ª conta criada pela aba "Criar conta" entra como Cerimoniário (sem poder editar escala)
    c2 = app.test_client()
    r2 = c2.post("/entrar", data={"acao": "criar", "nome": "Lucas", "login": "lucas", "papel": "cerimoniario", "senha": "senha-forte-2", "repetir": "senha-forte-2"})
    assert r2.status_code == 302
    lucas = next(u for u in acesso.usuarios.listar() if u["login"] == "lucas")
    assert lucas["coordenador"] is False and lucas["papel"] == "cerimoniario"

    # Lucas (Cerimoniário) pode visualizar Escala e Liturgia, mas NÃO pode criar/alterar escala ou membros
    assert c2.get("/escala").status_code == 200
    assert c2.get("/liturgia").status_code == 200
    assert c2.get(f"{API}/semana").status_code == 200
    assert c2.post(f"{API}/semana/gerar", json={"semana": SEGUNDA.isoformat()}).status_code == 403
    assert c2.post(f"{API}/membros", json={"nome": "Teste"}).status_code == 403
    assert c2.get("/ajustes").status_code == 403

    # Coordenador (Marcus) pode mudar o papel de Lucas para Coroinha ou Coordenador em "Minha conta"
    assert c1.put(f"{CONTAS}/{lucas['id']}", json={"nome": "Lucas", "papel": "coroinha"}).status_code == 200
    assert acesso.usuarios.obter(lucas["id"])["papel"] == "coroinha"
