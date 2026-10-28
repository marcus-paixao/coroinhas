"""Projeto: Escala dos Coroinhas e Cerimoniários da Basílica Nossa Senhora de Lourdes."""
from flask import Blueprint

PROJETO = {
    "id": "coroinhas",
    "nome": "Escala dos Coroinhas",
    "descricao": "Cadastro da equipe, funções do altar, missas fixas e a escala de cada fim de semana.",
    "icone": "bi-calendar-heart",
    "endpoint": "coroinhas.painel",
}

# Abas do menu: (endpoint, rótulo, rótulo curto no celular, ícone)
ABAS = [
    ("painel", "Painel", "Painel", "bi-grid-1x2-fill"),
    ("escala", "Escala", "Escala", "bi-calendar-week-fill"),
    ("equipe", "Coroinhas", "Equipe", "bi-people-fill"),
    ("funcoes", "Funções & Missas", "Funções", "bi-bell-fill"),
    ("ajustes", "Ajustes & Backup", "Ajustes", "bi-gear-fill"),
]

bp = Blueprint(
    "coroinhas", __name__,
    url_prefix="/coroinhas",
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)

from . import rotas  # noqa: E402,F401  (registra as rotas no blueprint)
