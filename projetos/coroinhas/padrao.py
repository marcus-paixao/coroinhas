"""Valores iniciais: funções do altar e missas fixas, tirados da escala de outubro/2026."""

FUNCOES_PADRAO = [
    {"id": "cruz", "nome": "Cruz", "emoji": "✝️", "cor": "#c92a2a"},
    {"id": "vela", "nome": "Vela", "emoji": "🕯️", "cor": "#f08c00"},
    {"id": "patena", "nome": "Patena", "emoji": "🪙", "cor": "#d4a017"},
    {"id": "lavabo", "nome": "Lavabo", "emoji": "💧", "cor": "#1c7ed6"},
    {"id": "ofertorio", "nome": "Ofertório", "emoji": "🍞", "cor": "#a0522d"},
    {"id": "sino", "nome": "Sino eletrônico", "emoji": "🔔", "cor": "#7048e8"},
    {"id": "carrilhao", "nome": "Carrilhão", "emoji": "🎶", "cor": "#0ca678"},
    {"id": "naveta", "nome": "Naveta", "emoji": "⛵", "cor": "#1098ad"},
    {"id": "turibulo", "nome": "Turíbulo", "emoji": "💨", "cor": "#868e96"},
]

# dia_semana: 0 = domingo … 6 = sábado. Cada vaga é a lista de funções de um coroinha.
HORARIOS_PADRAO = [
    {"id": "sab-16", "dia_semana": 6, "hora": "16:00", "reservas": 3, "vagas": [
        ["cruz", "carrilhao"], ["ofertorio", "patena"], ["sino", "ofertorio", "patena"],
        ["patena", "lavabo"], ["vela", "lavabo"], ["vela", "lavabo"]]},
    {"id": "dom-10", "dia_semana": 0, "hora": "10:00", "reservas": 4, "vagas": [
        ["vela", "patena"], ["vela", "patena", "lavabo"], ["cruz", "lavabo"], ["sino", "patena"],
        ["ofertorio", "patena"], ["naveta", "carrilhao"], ["turibulo"], ["ofertorio", "lavabo"]]},
    {"id": "dom-18", "dia_semana": 0, "hora": "18:00", "reservas": 3, "vagas": [
        ["cruz", "carrilhao", "patena"], ["ofertorio", "lavabo"], ["sino", "ofertorio", "patena"],
        ["lavabo", "patena"], ["vela", "lavabo"], ["vela", "lavabo"]]},
]

CONFIG_PADRAO = {"tipos_escalaveis": ["coroinha"]}

EMOJIS = ["✝️", "🕯️", "🪙", "💧", "🍞", "🍷", "🔔", "🎶", "⛵", "💨", "📖", "🎙️", "🌿", "👑", "🙏", "⭐", "🧺", "🏳️"]
CORES = ["#c92a2a", "#f08c00", "#d4a017", "#1c7ed6", "#a0522d", "#7048e8",
         "#0ca678", "#1098ad", "#868e96", "#d6336c", "#2f4ac2", "#74b816"]
