// Gera docs/Documentacao-Coroinhas.docx
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType,
  ShadingType, BorderStyle, LevelFormat, Header, Footer, PageNumber, PageBreak, Bookmark, InternalHyperlink,
} = require("docx");

const SAIDA = process.argv[2];
const AZUL = "12215F", AZUL_CLARO = "E8EEFF", OURO = "B8861B", CINZA = "5B648A", CODIGO_FUNDO = "F3F6FF";
const LARGURA = 9638; // A4 com margens de 2 cm

// ---------------------------------------------------------------- helpers
function runs(texto, base = {}) {
  return texto.split(/(\*\*[^*]+\*\*|`[^`]+`)/).filter(Boolean).map((t) => {
    if (t.startsWith("**")) return new TextRun({ ...base, text: t.slice(2, -2), bold: true });
    if (t.startsWith("`")) return new TextRun({ ...base, text: t.slice(1, -1), font: "Consolas", size: 19, color: AZUL });
    return new TextRun({ ...base, text: t });
  });
}
const p = (texto, opts = {}) => new Paragraph({ children: runs(texto), spacing: { after: 120 }, ...opts });
const capitulos = [];   // [âncora, título] para o sumário
const h1 = (t) => {
  const ancora = "cap" + (capitulos.length + 1);
  capitulos.push([ancora, t]);
  return new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new Bookmark({ id: ancora, children: [new TextRun(t)] })] });
};
// Sumário fixo com links (não depende de o Word atualizar campos; funciona no Google Docs e no celular)
const sumario = () => capitulos.map(([ancora, t]) => new Paragraph({
  spacing: { after: 100 }, indent: { left: 200 },
  children: [new InternalHyperlink({ anchor: ancora, children: [new TextRun({ text: t, color: "2F4AC2", size: 24 })] })],
}));
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const h3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const item = (t, nivel = 0) => new Paragraph({ numbering: { reference: "marcadores", level: nivel }, children: runs(t), spacing: { after: 60 } });
let lista = 0;
const passos = (itens) => { lista++; return itens.map((t) => new Paragraph({ numbering: { reference: "passos", level: 0, instance: lista }, children: runs(t), spacing: { after: 60 } })); };
const codigo = (linhas) => linhas.map((l, i) => new Paragraph({
  children: [new TextRun({ text: l || " ", font: "Consolas", size: 19 })],
  shading: { type: ShadingType.CLEAR, fill: CODIGO_FUNDO, color: "auto" },
  indent: { left: 200, right: 200 },
  spacing: { before: i === 0 ? 80 : 0, after: i === linhas.length - 1 ? 160 : 0 },
}));
const aviso = (t) => new Paragraph({
  children: runs(t),
  shading: { type: ShadingType.CLEAR, fill: "FFF1D6", color: "auto" },
  border: { left: { style: BorderStyle.SINGLE, size: 24, color: "F08C00", space: 8 } },
  indent: { left: 200, right: 200 }, spacing: { before: 120, after: 160 },
});

const borda = { style: BorderStyle.SINGLE, size: 4, color: "C5D3FF" };
const bordas = { top: borda, bottom: borda, left: borda, right: borda };
function tabela(cabecalho, linhas, larguras) {
  const total = larguras.reduce((a, b) => a + b, 0);
  const cel = (texto, largura, cab) => new TableCell({
    borders: bordas,
    width: { size: largura, type: WidthType.DXA },
    shading: cab ? { type: ShadingType.CLEAR, fill: AZUL, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: String(texto).split("\n").map((linha) => new Paragraph({
      children: runs(linha, cab ? { bold: true, color: "FFFFFF" } : {}), spacing: { after: 0 },
    })),
  });
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: larguras,
    rows: [
      new TableRow({ tableHeader: true, children: cabecalho.map((c, i) => cel(c, larguras[i], true)) }),
      ...linhas.map((l) => new TableRow({ children: l.map((c, i) => cel(c, larguras[i], false)) })),
    ],
  });
}
const espaco = () => new Paragraph({ children: [], spacing: { after: 60 } });

// ---------------------------------------------------------------- conteúdo
const capa = [
  new Paragraph({ children: [], spacing: { before: 2400 } }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "🕯️", size: 72 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200 }, children: [new TextRun({ text: "Coroinhas de Lourdes", bold: true, size: 56, color: AZUL, font: "Calibri" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Documentação do sistema web e do app Android", size: 30, color: CINZA })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600 }, children: [new TextRun({ text: "Pastoral dos Coroinhas e Cerimoniários", size: 24, color: OURO, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Basílica Nossa Senhora de Lourdes · Vila Isabel · Rio de Janeiro", size: 22, color: CINZA })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 1600 }, children: [new TextRun({ text: "Atualizada em 28/10/2026", size: 22, color: CINZA })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Pasta do projeto: C:\\Users\\mvim_\\OneDrive\\Desktop\\Codes\\Projetos\\Coroinhas", size: 18, color: CINZA, font: "Consolas" })] }),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ children: [new TextRun({ text: "Sumário", bold: true, size: 32, color: AZUL })], spacing: { after: 200 } }),
];

const visao = [
  h1("1. Visão geral"),
  p("O sistema organiza a **escala da Pastoral dos Coroinhas e Cerimoniários** da Basílica Nossa Senhora de Lourdes (Vila Isabel). Ele cuida do cadastro da equipe, das funções do altar, das missas fixas e da escala de cada fim de semana. Também mostra alertas de quem ficou sem escala e exporta a escala para o WhatsApp, em texto ou imagem."),
  p("Há duas formas de uso. As duas têm a mesma interface e o mesmo código:"),
  item("**Web (no PC):** um servidor Flask roda no computador. Abra no navegador do PC ou de qualquer aparelho na mesma rede Wi-Fi."),
  item("**App Android (APK):** o mesmo sistema roda **dentro do celular, sem internet**, com dados próprios. Os dados do celular são **separados** dos do PC. Para levar de um para o outro, use o backup."),
  h2("Em resumo"),
  tabela(["Item", "Detalhe"], [
    ["Linguagem / framework", "Python 3.11 + Flask 3.1 (Werkzeug 3.1, Jinja2)"],
    ["Banco de dados", "SQLite: `dados/usuarios.db` (contas) e `dados/coroinhas/coroinhas.db` (escala)"],
    ["Interface", "Templates Jinja + Bootstrap 5.3.3 + Bootstrap Icons 1.11.3 + JavaScript puro (um .js por tela)"],
    ["Arquivos estáticos", "Tudo local em `static/vendor/` (sem CDN): funciona offline"],
    ["Planilha da Pastoral", "Leitura de .xlsx com `python-calamine` (PC) ou `openpyxl` (Android)"],
    ["App Android", "Chaquopy 16 (Python no Android) + WebView, Android 11+ (minSdk 30, targetSdk 35), arm64"],
    ["Testes", "pytest: `python -m pytest tests` (25 testes)"],
    ["Controle de versão", "O projeto **ainda não é um repositório git**"],
  ], [2600, 7038]),
  h2("Identidade visual"),
  p("Azul mariano da abóbada da basílica (`#12215f` → `#3b5bdb`), dourado dos arcos (`#f5c451`) e o vermelho da batina (`#d6293a`). Fontes Fredoka (títulos) e Nunito (texto). Animações em CSS (entrada das telas, vela e rosácea da ilustração) respeitam a opção “reduzir movimento” do sistema operacional."),
];

const usoPC = [
  h1("2. Como usar no PC"),
  h2("Primeira vez"),
  ...codigo([
    "cd C:\\Users\\mvim_\\OneDrive\\Desktop\\Codes\\Projetos\\Coroinhas",
    "pip install -r requirements.txt         (ou use o .venv que já existe)",
    "python app.py criar-usuario marcus      # cria o 1º coordenador (pede nome e senha)",
    "python app.py                           # http://127.0.0.1:5000",
  ]),
  p("O servidor também responde no IP da rede (`0.0.0.0`). Outro aparelho no mesmo Wi-Fi abre pelo navegador em `http://<IP do PC>:5000`."),
  p("Já existe a conta **marcus** (coordenador). A senha foi gerada ao acaso e entregue no chat. Troque-a em **Minha conta → Trocar minha senha**."),
  p("O comando `python app.py criar-usuario <login>` **sempre cria ou atualiza um coordenador**. Ele também serve para recuperar o acesso se todos os coordenadores esquecerem a senha."),
  p("Na 1ª execução, o banco da escala é criado a partir de `dados/coroinhas/carga_inicial/backup-inicial.json`, que tem os cadastros da planilha da Pastoral e a escala de 24 e 25/10/2026. Sem esse arquivo, o banco começa vazio, só com as funções e as missas fixas padrão."),
  h2("Variáveis de ambiente"),
  tabela(["Variável", "Para que serve"], [
    ["`SECRET_KEY`", "Chave da sessão. Sem ela, uma chave é gerada e guardada em `dados/secret_key`."],
    ["`COOKIE_SEGURO=1`", "Cookie só por HTTPS. Ligue quando o site estiver na internet com HTTPS."],
    ["`COROINHAS_DADOS`", "Outra pasta de dados (usada pelos testes e pelo APK)."],
    ["`COROINHAS_APK=1`", "Modo app Android: a tela de entrar permite criar o 1º coordenador quando não há contas."],
    ["`PORT`", "Porta do servidor (padrão 5000)."],
  ], [2400, 7238]),
];

const telas = [
  h1("3. Telas e funcionalidades"),
  tabela(["Tela", "O que faz"], [
    ["Entrar", "Login. No APK, sem nenhuma conta, vira o cadastro do 1º coordenador."],
    ["Painel", "Escala da semana, vagas preenchidas, quem ainda está sem escala, quantas vezes cada um serviu no mês (quem serviu menos aparece primeiro), aniversariantes dos próximos 30 dias e ausentes."],
    ["Escala", "Semana a semana. Cria as missas a partir das missas fixas; ao tocar numa vaga, escolhe-se quem serve (quem ainda não foi escalado aparece primeiro). Também dá para tocar num nome em “Faltando na escala” e escolher a vaga. Avisa se alguém ausente foi escalado ou aparece 2× na mesma missa. Inclui missa extra, editar e remover missa, repetir a semana anterior, **Copiar p/ WhatsApp** (texto) e **Imagem da escala** (PNG)."],
    ["Coroinhas (Equipe)", "Cadastro com busca e filtros (coroinhas, cerimoniários, coordenação, ausentes). A chave **Ausente** tira a pessoa dos alertas, com motivo e data “até” opcionais (depois dela, a pessoa volta a ser alertada sozinha). Importa a planilha da Pastoral."],
    ["Funções & Missas", "Funções do altar (nome, emoji, cor) e missas fixas (dia, horário, vagas com as funções de cada uma, e reservas)."],
    ["Ajustes & Backup", "Importar planilha, baixar e restaurar backup (.json), escolher quem entra nos alertas (padrão: só coroinhas), recomeçar do zero e ver o **histórico** de alterações (quem, quando, o quê)."],
    ["Minha conta", "Abre ao clicar no nome, na barra lateral, ou no ícone de pessoa, no celular. Aqui cada um troca a própria senha. Coordenadores também gerenciam as contas (ver capítulo 4)."],
  ], [2200, 7438]),
  h2("Navegação"),
  item("**PC (tela larga):** barra lateral azul com o menu, o nome do usuário (link para Minha conta) e o botão Sair."),
  item("**Celular (até 860 px):** topo fixo com a marca, Minha conta e Sair; menu fixo embaixo com Painel, Escala, Equipe, Funções e Ajustes. **Só o meio da tela rola**, como num app. A aba Escala mostra um contador vermelho com vagas abertas + pessoas sem escala na semana atual."),
  item("No celular, os formulários (modais) abrem como uma “gaveta” que sobe de baixo."),
  h2("Planilha da Pastoral"),
  p("Arquivo .xlsx com as colunas **Função**, **Nome** e **Data de Nascimento**, em qualquer ordem. O cabeçalho pode estar depois de linhas de título. Quem já está cadastrado é atualizado, sem duplicar. Datas aceitas: data do Excel, número serial ou `dd/mm/aaaa`. Função começando com “cerimon” vira Cerimoniário, com “coord” vira Coordenação, e o resto vira Coroinha."),
];

const contas = [
  h1("4. Contas, perfis e permissões"),
  tabela(["Pode…", "Coordenador(a)", "Equipe"], [
    ["Usar todas as telas (escala, cadastros, funções, ajustes, backup)", "Sim", "Sim"],
    ["Trocar a própria senha", "Sim", "Sim"],
    ["Criar contas (Coordenador ou Equipe)", "Sim", "Não"],
    ["Mudar o nome de uma conta", "Sim", "Não"],
    ["Redefinir a senha de outra pessoa", "Sim", "Não"],
    ["Dar ou tirar o acesso de coordenador de outra pessoa", "Sim", "Não"],
    ["Remover contas de outras pessoas", "Sim", "Não"],
  ], [5638, 2000, 2000]),
  h2("Regras"),
  item("Ninguém remove a própria conta nem tira o próprio acesso de coordenador. Assim sempre sobra pelo menos um coordenador."),
  item("Senha com no mínimo **8 caracteres**. Usuário (login): de 2 a 40 caracteres entre letras minúsculas, números, ponto, hífen ou _, sem espaços. O login não muda depois de criado."),
  item("Trocar a própria senha exige a senha atual. Você continua logado no aparelho atual e **sai dos outros aparelhos**."),
  item("Quando um coordenador redefine a senha de alguém, a pessoa sai de todos os aparelhos. Uma conta removida não consegue mais entrar, e a sessão dela cai na hora."),
  item("Como funciona: a sessão guarda uma “marca”, os últimos 16 caracteres do hash da senha. A cada requisição, a marca é comparada com a do banco. Se a senha mudou, a sessão é encerrada."),
  item("Limite contra chute de senha: 10 erros por IP a cada 10 minutos."),
  item("A sessão dura 30 dias."),
  h2("Primeiro coordenador"),
  item("**PC:** pelo terminal, `python app.py criar-usuario <login>`."),
  item("**APK:** na primeira abertura, a tela de entrar mostra “Bem-vindo! Crie a conta de coordenador” (nome, usuário, senha e repetir a senha). Isso só aparece enquanto não houver nenhuma conta, e só no modo APK."),
  h2("Migração de bancos antigos"),
  p("Se `usuarios.db` não tiver a coluna `coordenador`, ela é criada sozinha e **todas as contas que já existiam viram coordenadoras**, porque antes só se criava conta pelo terminal."),
  aviso("**Atenção:** as alterações em contas (criar, editar, remover, trocar senha) **não** aparecem no “Histórico de alterações” da tela Ajustes. Esse histórico só registra mudanças nos dados da escala."),
];

const arquitetura = [
  h1("5. Arquitetura e código"),
  h2("Estrutura de pastas"),
  tabela(["Caminho", "Conteúdo"], [
    ["`app.py`", "Cria o Flask, registra os projetos e o login, define a página inicial e o comando `criar-usuario`."],
    ["`acesso.py`", "Login (sessão), contas (classe `Usuarios`), Minha conta e as APIs `/conta/api/...`, além de `proteger()`, que exige login em tudo."],
    ["`templates/`", "`base.html` (layout com menu, modais e avisos), `entrar.html`, `conta.html` e `_basilica.html` (ilustração)."],
    ["`static/css/style.css`", "Todo o visual (cores, componentes, celular, animações)."],
    ["`static/js/comum.js`", "Utilidades das telas (objeto `window.App`)."],
    ["`static/js/conta.js`", "Tela Minha conta."],
    ["`static/vendor/`", "Bootstrap, Bootstrap Icons, fontes Fredoka/Nunito (latin) e html-to-image, todos locais."],
    ["`projetos/coroinhas/`", "O projeto da escala (um blueprint em `/coroinhas`)."],
    ["`  __init__.py`", "Blueprint, metadados `PROJETO` e abas do menu `ABAS`."],
    ["`  rotas.py`", "Páginas e APIs JSON."],
    ["`  regras.py`", "Regras da escala: datas, ausências, pendências, participação e texto do WhatsApp."],
    ["`  repositorio.py`", "SQLite: membros, funções, missas fixas, missas, escalas, histórico e backup."],
    ["`  planilha.py`", "Leitura do .xlsx da Pastoral."],
    ["`  padrao.py`", "Funções e missas fixas iniciais, emojis e cores."],
    ["`  templates/ static/js/`", "Telas do projeto (painel, escala, equipe, funcoes, ajustes; `editor_vagas.js` é compartilhado)."],
    ["`tests/test_app.py`", "Testes automatizados."],
    ["`dados/`", "Dados reais (fora do git): contas, chave da sessão e banco da escala."],
    ["`apk/`", "Projeto do app Android (capítulo 9)."],
    ["`_versao_react_antiga/`", "Versão anterior (React + Vite), guardada só para consulta. O backup dela pode ser restaurado no sistema atual."],
  ], [2900, 6738]),
  h2("Como uma requisição é tratada"),
  ...passos([
    "`acesso.proteger()` roda antes de tudo. Ela bloqueia envios (POST/PUT/DELETE) vindos de outro site (cabeçalho Origin), libera só a tela de entrar e os arquivos estáticos, carrega o usuário da sessão (`g.usuario`) e confere a marca da senha.",
    "Sem login, as páginas redirecionam para `/entrar?proximo=...`, e as APIs (caminho com `/api/`) respondem 401 em JSON.",
    "A rota do blueprint devolve uma página Jinja ou JSON. Erros de validação (`ErroCoroinhas`, `ErroAcesso`) viram `400 {\"erro\": \"mensagem\"}`.",
    "O JavaScript de cada tela chama as APIs com `App.api`/`post`/`put`/`del` e mostra o resultado com avisos (toasts). Depois de salvar, muitas telas usam `App.recarregarCom(msg)`, que recarrega a página e mostra o aviso.",
  ]),
  h2("Utilidades do JavaScript (window.App, em comum.js)"),
  tabela(["Função", "Uso"], [
    ["`api(url, opts)`", "fetch com JSON. Por padrão, prefixa `window.API` (`/coroinhas`). Passe `{ base: \"\" }` para rotas do site, como `/conta/api/...`."],
    ["`post` / `put` / `del`", "Atalhos de `api`."],
    ["`toast(msg, tipo, desfazer)` / `erro(e)`", "Avisos; `desfazer` mostra o botão Desfazer."],
    ["`confirmar(titulo, html, rotulo, classe)`", "Modal de confirmação; devolve uma Promise<boolean>."],
    ["`recarregarCom(msg)`", "Recarrega a página e mostra o aviso depois."],
    ["`baixar(blob, nome)`", "Salva um arquivo (no APK: pasta Downloads/Coroinhas)."],
    ["`compartilhar(blob, nome, titulo)`", "Abre o compartilhar do celular (ex.: WhatsApp). Devolve false se não deu."],
    ["`copiar(texto)`", "Copia para a área de transferência."],
    ["`NATIVO`", "A ponte `window.Android`, que só existe dentro do APK."],
    ["Formatação", "`dataCurta`, `formatarHora`, `diaSemana`, `rotuloMissa`, `normalizar`, `estaAusente`, `avatar`, `chipFuncao`, `ligarSwitch`."],
  ], [3300, 6338]),
  p("Links de download do servidor marcados com `data-baixar=\"nome\"` (ex.: Baixar backup) são buscados e salvos pela ponte quando o sistema roda no APK.", { spacing: { before: 120 } }),
  h2("Adicionar um projeto novo"),
  p("Crie `projetos/<nome>/` com um `Blueprint` chamado `bp` e o dicionário `PROJETO` (id, nome, descricao, icone, endpoint) e inclua o módulo em `MODULOS` no `app.py`. O primeiro da lista abre ao entrar. Hoje o menu do `base.html` usa as `ABAS` do projeto coroinhas."),
];

const dados = [
  h1("6. Dados"),
  h2("Onde ficam"),
  tabela(["Arquivo", "Conteúdo"], [
    ["`dados/usuarios.db`", "Contas (login, nome, hash da senha, coordenador)."],
    ["`dados/secret_key`", "Chave da sessão (gerada sozinha se não houver `SECRET_KEY`)."],
    ["`dados/coroinhas/coroinhas.db`", "Membros, funções, missas fixas, missas, escalas, configuração e histórico."],
    ["`dados/coroinhas/carga_inicial/backup-inicial.json`", "Carga da 1ª execução (planilha da Pastoral + escala de 24 e 25/10/2026)."],
    ["`dados/coroinhas/uploads/`", "Temporário, só durante uma importação."],
  ], [3900, 5738]),
  aviso("São **dados pessoais de menores**. `dados/` e as planilhas `.xlsx` estão no `.gitignore`. Nunca publique esses arquivos nem os coloque dentro do APK, porque o build empacota só o código."),
  h2("Tabelas"),
  tabela(["Tabela", "Campos principais"], [
    ["usuarios", "id, login (único), nome, senha_hash, coordenador (0/1)"],
    ["membros", "id, nome, apelido (nome na escala), tipo (coroinha | cerimoniario | coordenacao), nascimento, telefone, responsavel, observacoes, ausente, motivo_ausencia, ausente_ate"],
    ["funcoes", "id, nome, emoji, cor, ordem"],
    ["horarios (missas fixas)", "id, dia_semana (0 = domingo … 6 = sábado), hora, titulo, reservas, vagas (JSON: lista de funções de cada vaga)"],
    ["missas", "id, data, hora, titulo"],
    ["escalas", "id, missa_id, tipo (vaga | reserva), posicao, funcoes (JSON), membro_id"],
    ["config", "chave/valor; hoje só `tipos_escalaveis` (quem entra nos alertas)"],
    ["historico", "id, quando, usuario, acao, descricao"],
  ], [2500, 7138]),
  h2("Valores padrão"),
  p("**Funções:** Cruz ✝️, Vela 🕯️, Patena 🪙, Lavabo 💧, Ofertório 🍞, Sino eletrônico 🔔, Carrilhão 🎶, Naveta ⛵ e Turíbulo 💨."),
  tabela(["Missa fixa", "Vagas", "Reservas"], [
    ["Sábado 16h", "6", "3"],
    ["Domingo 10h", "8", "4"],
    ["Domingo 18h", "6", "3"],
  ], [4638, 2500, 2500]),
  p("Alertas: por padrão, só **coroinhas** entram em “faltando na escala”. Quem está marcado como Ausente nunca é alertado.", { spacing: { before: 120 } }),
  h2("Backup"),
  item("**Baixar backup** (Ajustes) gera um `.json` com tudo: cadastros, funções, missas fixas e escalas. As contas não entram."),
  item("**Restaurar backup** substitui **tudo** o que está salvo, para todo mundo. Também aceita o backup da versão React antiga."),
  item("É o único jeito de levar dados do PC para o celular (e vice-versa)."),
];

const api = [
  h1("7. Rotas e APIs"),
  p("Todas exigem login, menos `/entrar` e os arquivos estáticos. As rotas `/coroinhas/api/...` e `/conta/api/...` recebem e devolvem JSON."),
  tabela(["Método", "Rota", "O que faz"], [
    ["GET", "`/`", "Redireciona para o primeiro projeto (Painel)"],
    ["GET, POST", "`/entrar`", "Login (e o 1º coordenador, no APK)"],
    ["POST", "`/sair`", "Encerra a sessão"],
    ["GET", "`/conta`", "Tela Minha conta"],
    ["POST", "`/conta/api/senha`", "Trocar a própria senha `{atual, nova}`"],
    ["POST", "`/conta/api/usuarios`", "Criar conta `{login, nome, senha, coordenador}` (coordenador)"],
    ["PUT", "`/conta/api/usuarios/<id>`", "Editar `{nome, coordenador, senha?}` (coordenador)"],
    ["DELETE", "`/conta/api/usuarios/<id>`", "Remover conta (coordenador)"],
    ["GET", "`/coroinhas/`", "Painel"],
    ["GET", "`/coroinhas/escala`", "Escala (`?semana=AAAA-MM-DD`)"],
    ["GET", "`/coroinhas/equipe`", "Coroinhas"],
    ["GET", "`/coroinhas/funcoes`", "Funções & Missas"],
    ["GET", "`/coroinhas/ajustes`", "Ajustes & Backup"],
    ["GET", "`/coroinhas/backup`", "Baixa o backup .json"],
    ["GET", "`/coroinhas/api/semana`", "Dados da semana (missas, vagas, pendências)"],
    ["POST", "`/coroinhas/api/semana/gerar`", "Cria as missas da semana a partir das missas fixas"],
    ["POST", "`/coroinhas/api/semana/copiar-anterior`", "Repete a escala da semana anterior"],
    ["GET", "`/coroinhas/api/semana/whatsapp`", "Texto da escala para o WhatsApp"],
    ["POST", "`/coroinhas/api/escalas/<id>`", "Escala (ou tira) alguém de uma vaga/reserva"],
    ["POST, PUT, DELETE", "`/coroinhas/api/missas[/<id>]`", "Missa extra / editar / remover"],
    ["POST, PUT, DELETE", "`/coroinhas/api/membros[/<id>]`", "Cadastro de membros"],
    ["POST", "`/coroinhas/api/membros/<id>/ausencia`", "Liga/desliga Ausente (motivo, até)"],
    ["POST, PUT, DELETE", "`/coroinhas/api/funcoes[/<id>]`", "Funções do altar"],
    ["POST, PUT, DELETE", "`/coroinhas/api/horarios[/<id>]`", "Missas fixas"],
    ["POST", "`/coroinhas/api/planilha`", "Importa a planilha .xlsx (multipart, campo `arquivo`)"],
    ["POST", "`/coroinhas/api/backup`", "Restaura um backup .json (multipart)"],
    ["POST", "`/coroinhas/api/config`", "Quem entra nos alertas `{tipos_escalaveis}`"],
    ["POST", "`/coroinhas/api/apagar-tudo`", "Recomeça do zero"],
  ], [1700, 3900, 4038]),
];

const seguranca = [
  h1("8. Segurança"),
  item("Tudo exige login. As senhas são guardadas com hash (Werkzeug, scrypt)."),
  item("Limite de 10 tentativas erradas por IP a cada 10 minutos."),
  item("Envios vindos de outros sites são bloqueados (verificação do cabeçalho Origin)."),
  item("Cookie de sessão HttpOnly e SameSite=Lax, válido por 30 dias. Trocar a senha derruba as outras sessões."),
  item("Redirecionamento após o login só para caminhos do próprio site."),
  item("Upload limitado a 10 MB."),
  item("Para colocar na internet: HTTPS, `SECRET_KEY` fixa no ambiente e `COOKIE_SEGURO=1`. Lembre que são dados de menores."),
  item("No APK, o servidor escuta só em `127.0.0.1` (dentro do próprio celular). Outro app no aparelho chegaria a ele, mas também precisaria de login."),
];

const apk = [
  h1("9. App Android (APK)"),
  h2("Como funciona"),
  p("O APK leva o **mesmo código do site**. O Chaquopy embute o Python 3.11, e um WebView mostra as telas:"),
  ...passos([
    "O build compacta `app.py`, `acesso.py`, `projetos/`, `templates/` e `static/` em `sistema.zip`, que vai dentro do APK. A pasta `dados/` **não** vai junto.",
    "Na 1ª abertura de cada versão instalada, a `MainActivity` descompacta o `sistema.zip` na pasta interna do app.",
    "O `servidor.py` sobe o Flask em `127.0.0.1:8765`, numa thread, com `COROINHAS_APK=1` e os dados na pasta interna do app.",
    "O WebView abre `http://127.0.0.1:8765/`. Links para fora abrem no navegador do celular.",
  ]),
  h2("Arquivos da pasta apk/"),
  tabela(["Arquivo", "O que faz"], [
    ["`construir.ps1`", "Gera o APK. Na 1ª vez, baixa o Android SDK e o Gradle e cria a chave de assinatura. Precisa ficar salvo em **UTF-8 com BOM** (o PowerShell 5.1 quebra com acentos sem BOM)."],
    ["`build.gradle`, `settings.gradle`, `gradle.properties`", "AGP 8.7.3, Chaquopy 16.0.0, Gradle 8.11.1. Os intermediários do build vão para `%LOCALAPPDATA%\\CoroinhasApk\\build` (fora do OneDrive)."],
    ["`app/build.gradle`", "Empacota o `sistema.zip`, define a versão automática pela data, instala Flask 3.1.3, Werkzeug 3.1.9 e openpyxl 3.1.5 para Android e faz a assinatura."],
    ["`app/src/main/python/servidor.py`", "Sobe o Flask dentro do app."],
    ["`app/src/main/java/.../MainActivity.java`", "WebView, escolher arquivo, salvar em Downloads/Coroinhas, compartilhar, copiar, botão voltar, margens das barras do sistema, sem zoom e sem o “esticar” da rolagem."],
    ["`app/src/main/res/`", "Ícone adaptável (a vela do favicon em fundo azul) e o nome “Coroinhas”."],
    ["`assinatura/`", "Chave de assinatura (`coroinhas.jks` + senha). **Não publique e não perca.**"],
    ["`Coroinhas.apk`", "O APK gerado (cerca de 21 MB)."],
  ], [3300, 6338]),
  h2("Gerar o APK"),
  ...codigo(["powershell -ExecutionPolicy Bypass -File \"C:\\Users\\mvim_\\OneDrive\\Desktop\\Codes\\Projetos\\Coroinhas\\apk\\construir.ps1\""]),
  p("Requisitos no PC: JDK 17+ (já instalado em `C:\\Program Files\\Java\\jdk-17`) e Python 3.11 (`py -3.11`). O Android SDK fica em `%LOCALAPPDATA%\\Android\\Sdk`. A 1ª vez levou alguns minutos; as próximas levam de 1 a 2 minutos."),
  h2("Instalar no celular (Galaxy S25 Ultra)"),
  ...passos([
    "Mande o `apk\\Coroinhas.apk` para o celular: pelo WhatsApp Web para você mesmo (como documento), pelo Google Drive ou por cabo USB (pasta Download).",
    "Toque no arquivo. Quando o Android bloquear, toque em **Configurações → Permitir desta fonte** e volte.",
    "Toque em **Instalar**. Se o Play Protect avisar, toque em **Mais detalhes → Instalar mesmo assim**.",
    "Abra o app **Coroinhas** e crie a conta de coordenador.",
    "Para trazer os dados do PC: no PC, **Ajustes → Baixar backup**; mande o .json para o celular; no app, **Ajustes → Restaurar backup**.",
  ]),
  h2("Atualizar o app"),
  ...passos([
    "Faça a mudança no código do sistema. Ela vale para o site e para o APK.",
    "Rode o `construir.ps1` de novo. A versão (`versionCode`) é numerada sozinha pela data e hora do build.",
    "Instale o APK novo **por cima** do antigo, sem desinstalar. Os dados do celular são mantidos.",
  ]),
  aviso("**Guarde a pasta `apk\\assinatura\\`.** O Android só aceita a atualização se o APK tiver a mesma assinatura. Sem ela, a única saída é desinstalar, o que **apaga os dados do celular**. Antes de atualizações grandes, baixe um backup pelo app."),
  h2("Diferenças entre o APK e o PC"),
  tabela(["Assunto", "PC (web)", "APK"], [
    ["Dados", "`dados/` na pasta do projeto", "Pasta interna do app (some ao desinstalar)"],
    ["1º coordenador", "Terminal (`criar-usuario`)", "Tela de entrar, na 1ª abertura"],
    ["Planilha .xlsx", "python-calamine", "openpyxl"],
    ["Baixar arquivo / backup", "Download do navegador", "Salvo em Downloads/Coroinhas"],
    ["Imagem da escala", "Baixa o PNG (no celular pelo navegador: compartilhar)", "Abre o compartilhar do Android (WhatsApp) e salva em Downloads/Coroinhas"],
    ["Copiar p/ WhatsApp", "Área de transferência do navegador", "Área de transferência do Android (ponte nativa)"],
    ["Internet", "Não precisa (arquivos locais)", "Não precisa"],
  ], [2400, 3600, 3638]),
  h2("Ponte JavaScript ↔ Android"),
  p("Dentro do app existe `window.Android`, com `salvar(nome, tipo, base64)`, `compartilhar(nome, tipo, base64, titulo)` e `copiar(texto)`. O `comum.js` usa a ponte quando ela existe e as APIs do navegador quando não existe. Assim o mesmo JavaScript funciona nos dois lugares."),
];

const testes = [
  h1("10. Testes"),
  ...codigo(["python -m pytest tests          # 25 testes, usam uma pasta de dados temporária"]),
  item("Login obrigatório, senha errada, bloqueio de outra origem e todas as páginas abrindo (inclusive Minha conta)."),
  item("Contas: trocar a própria senha (derruba o outro aparelho), coordenador gerenciando contas, Equipe sem permissão (403), regras de não remover a si mesmo, 1º coordenador no modo APK e migração de banco antigo."),
  item("Escala: gerar a semana, escalar, ausência que expira, editar missa mantendo quem estava escalado, remover função ou membro liberando a vaga e validações."),
  item("Backup (ida e volta, versão React antiga, arquivo inválido) e regras."),
  p("Também foi feita uma simulação do APK no PC: o mesmo pacote do APK, o servidor do app, sem o python-calamine, e o fluxo completo por HTTP (1ª conta, telas sem CDN, backup, WhatsApp e planilha via openpyxl).", { spacing: { before: 120 } }),
];

const historico = [
  h1("11. Histórico de mudanças"),
  tabela(["Data", "Mudança"], [
    ["27/10/2026", "Sistema Flask atual (substituiu a versão React + Vite, guardada em `_versao_react_antiga/`). Escala, cadastros, funções, missas fixas, backup, histórico e login da coordenação."],
    ["28/10/2026", "Criada a conta de coordenador **marcus** (senha aleatória, entregue no chat)."],
    ["28/10/2026", "Perfis **Coordenador** e **Equipe**; tela **Minha conta** (trocar a própria senha); coordenadores criam, editam e removem contas, redefinem senhas e dão ou tiram o acesso de coordenador. A sessão cai quando a senha muda."],
    ["28/10/2026", "Bootstrap, ícones, fontes e html-to-image passaram a ser locais (`static/vendor/`): o sistema funciona sem internet."],
    ["28/10/2026", "**App Android offline** (pasta `apk/`): Chaquopy + WebView, ponte para salvar/compartilhar/copiar, 1º coordenador pelo app, planilha via openpyxl. APK gerado com sucesso (21 MB)."],
    ["28/10/2026", "`construir.ps1` salvo em UTF-8 com BOM (o PowerShell 5.1 quebrava com acentos). Versão do APK automática pela data do build."],
    ["28/10/2026", "Layout de **app** no celular: topo e menu de baixo fixos, só o meio rola, sem o efeito de esticar, sem zoom e sem fundo branco nas bordas; fontes sem “pulo” ao carregar."],
  ], [1500, 8138]),
];

const pendencias = [
  h1("12. Pendências e próximos passos"),
  item("**Gerar o APK de novo** (`construir.ps1`) para o celular receber o ajuste de layout (menu fixo) e instalar por cima."),
  item("**Testar no S25 Ultra** a parte nativa: compartilhar a imagem da escala, salvar o backup, escolher arquivo (planilha/backup), botão voltar e criação da 1ª conta."),
  item("Registrar as alterações de contas no Histórico (hoje não registra)."),
  item("Não há sincronização entre PC e celular: só o backup manual. Para ter os mesmos dados nos dois, o caminho seria hospedar o sistema na internet (com HTTPS) e apontar o app para lá."),
  item("Versionar o projeto com git, sem incluir `dados/` (já no .gitignore) nem `apk/assinatura/` (já no `apk/.gitignore`)."),
  item("Guardar uma cópia extra de `apk\\assinatura\\` fora do PC."),
];

const contexto = [
  h1("13. Contexto rápido (para retomar o projeto)"),
  p("Cole o texto abaixo ao pedir ajuda a outra pessoa ou a uma IA, junto com este documento:"),
  ...codigo([
    "Projeto: sistema da escala dos Coroinhas da Basílica N. Sra. de Lourdes (Vila Isabel).",
    "Pasta: C:\\Users\\mvim_\\OneDrive\\Desktop\\Codes\\Projetos\\Coroinhas (Windows, sem git).",
    "Stack: Python 3.11 + Flask 3.1 + SQLite + Jinja + Bootstrap 5.3 local + JS puro.",
    "Rodar: .venv\\Scripts\\python.exe app.py  |  testes: python -m pytest tests (25).",
    "Projeto em blueprint: projetos/coroinhas (rotas, regras, repositorio, planilha, padrao).",
    "Contas: acesso.py; perfis Coordenador/Equipe; Minha conta em /conta; coordenador",
    "  gerencia contas; ninguém remove a si mesmo; trocar senha derruba outras sessões.",
    "App Android: pasta apk/ (Chaquopy + WebView), roda o MESMO código offline no celular,",
    "  dados separados do PC (troca via backup .json). Gerar: apk\\construir.ps1",
    "  (UTF-8 com BOM). Guardar apk\\assinatura\\. JS usa window.Android via comum.js.",
    "Celular: topo e menu fixos, só .conteudo rola (style.css, body.com-menu).",
    "Dados reais em dados/ (menores de idade): nunca publicar nem empacotar.",
  ]),
];

// ---------------------------------------------------------------- documento
const doc = new Document({
  creator: "Pastoral dos Coroinhas",
  title: "Documentação · Coroinhas de Lourdes",
  description: "Documentação do sistema web e do app Android da escala dos coroinhas",
  styles: {
    default: { document: { run: { font: "Calibri", size: 22, color: "18203F" } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, color: AZUL, font: "Calibri" },
        paragraph: { spacing: { before: 0, after: 240 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: "F5C451", space: 6 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: "1B2F7A", font: "Calibri" },
        paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: "2F4AC2", font: "Calibri" },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "marcadores", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1080, hanging: 270 } } } },
      ] },
      { reference: "passos", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } },
      ] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "Coroinhas de Lourdes · Documentação", size: 16, color: CINZA })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: ["Página ", PageNumber.CURRENT, " de ", PageNumber.TOTAL_PAGES], size: 16, color: CINZA })] })] }) },
    children: [...capa, ...sumario(), ...visao, ...usoPC, ...telas, ...contas, ...arquitetura, ...dados, ...api, ...seguranca, ...apk, ...testes, ...historico, ...pendencias, ...contexto],
  }],
});

// O docx-js numera todos os marcadores com o mesmo id: renumera cada par início/fim em sequência
async function renumerarMarcadores(buf) {
  const JSZip = require("jszip");
  const zip = await JSZip.loadAsync(buf);
  let xml = await zip.file("word/document.xml").async("string");
  let n = 0, fim = 0;
  xml = xml.replace(/(<w:bookmarkStart [^>]*?)w:id="[0-9]+"/g, (_, ini) => `${ini}w:id="${++n}"`)
           .replace(/(<w:bookmarkEnd [^>]*?)w:id="[0-9]+"/g, (_, ini) => `${ini}w:id="${++fim}"`);
  zip.file("word/document.xml", xml);
  return zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
}

Packer.toBuffer(doc).then(renumerarMarcadores).then((buf) => {
  fs.mkdirSync(path.dirname(SAIDA), { recursive: true });
  fs.writeFileSync(SAIDA, buf);
  console.log("ok", SAIDA, Math.round(buf.length / 1024), "KB");
});
