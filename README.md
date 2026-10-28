# Coroinhas · Basílica Nossa Senhora de Lourdes (Vila Isabel)

Sistema Flask da Pastoral dos Coroinhas e Cerimoniários: cadastro da equipe, funções do altar,
missas fixas e a escala de cada fim de semana, com alertas de quem ficou sem escala e exportação para o WhatsApp.
Mesmo padrão de construção do portal de Planejamento (app.py + projetos em blueprints + SQLite).

## Executar

```bash
pip install -r requirements.txt
python app.py criar-usuario marcus     # uma vez: cria o 1º coordenador (pede nome e senha, mín. 8 caracteres)
python app.py                          # http://127.0.0.1:5000 (e no IP da rede, para abrir no celular)
```

Na 1ª execução o banco é criado a partir de `dados/coroinhas/carga_inicial/backup-inicial.json`
(cadastros da planilha da Pastoral + a escala de 24 e 25/10/2026). Sem esse arquivo, começa vazio,
só com as funções e missas fixas padrão.

## Telas

- **Painel** — escala da semana, vagas preenchidas, quem ainda está sem escala, quantas vezes cada um serviu no mês
  (quem serviu menos aparece primeiro), aniversariantes dos próximos 30 dias e ausentes.
- **Escala** — semana a semana: cria as missas a partir das missas fixas, toque numa vaga para escolher quem serve
  (quem ainda não foi escalado aparece primeiro) ou toque num nome em "Faltando na escala" para escolher a vaga.
  Avisa se alguém ausente foi escalado ou aparece 2× na mesma missa. Missa extra, editar/remover missa,
  repetir a semana anterior, **Copiar p/ WhatsApp** (texto formatado) e **Imagem da escala** (PNG).
- **Coroinhas** — cadastro com busca e filtros. A chave **Ausente** tira a pessoa dos alertas; no cadastro dá para
  informar o motivo e uma data "até" (depois dela, volta a ser alertada sozinha). Importa a planilha da Pastoral.
- **Funções & Missas** — funções do altar (nome, ícone, cor) e as missas fixas (dia, horário, vagas e reservas).
- **Ajustes & Backup** — importar planilha, baixar/restaurar backup (.json), quem entra nos alertas
  (padrão: só coroinhas), recomeçar do zero e o **histórico** de todas as alterações (quem, quando, o quê).
- **Minha conta** (clique no seu nome no menu) — cada um troca a própria senha (os outros aparelhos saem da conta).
  Coordenadores também criam, editam e removem contas, redefinem senhas esquecidas e dão ou tiram o acesso de coordenador
  (ninguém remove a própria conta nem tira o próprio acesso). Contas comuns usam o sistema normalmente.

## Estrutura

```
app.py                         registra os projetos, login e a página inicial; `python app.py criar-usuario`
acesso.py                      login (sessão), Minha conta e gestão de contas; usuários em dados/usuarios.db
templates/ static/             layout comum (menu, modais, avisos), tela Minha conta, CSS, comum.js e a ilustração da basílica
projetos/coroinhas/
  __init__.py                  blueprint + metadados do projeto e abas do menu
  rotas.py                     páginas e APIs (JSON)
  regras.py                    regras da escala: datas, ausências, pendências, participação, texto do WhatsApp
  repositorio.py               SQLite: membros, funções, missas fixas, missas, escalas, histórico, backup
  planilha.py                  leitura do .xlsx da Pastoral
  padrao.py                    funções e missas fixas iniciais
  templates/ static/js/        telas do projeto (um .js por tela; editor_vagas.js é compartilhado)
dados/                         (fora do git) usuarios.db, secret_key e coroinhas/{coroinhas.db, carga_inicial/}
tests/test_app.py              testes (python -m pytest tests)
static/vendor/                 Bootstrap, Bootstrap Icons, fontes e html-to-image locais (funciona sem internet)
apk/                           app Android com este mesmo sistema rodando no celular (ver apk/README.md)
```

**Novo projeto:** crie `projetos/<nome>/` com `bp` (Blueprint) e `PROJETO` e adicione o módulo em `MODULOS` no `app.py`.

## App Android (APK)

`apk/` gera um APK com o sistema completo rodando **offline no celular**, com dados próprios e separados dos do PC
(para trocar dados entre os dois, use o backup). Para gerar: `powershell -ExecutionPolicy Bypass -File apk\construir.ps1`.
Detalhes em [apk/README.md](apk/README.md).

## Dados e segurança

- São dados pessoais de menores: `dados/` e planilhas `.xlsx` estão no `.gitignore`. Não publique esses arquivos.
- Tudo exige login. Senhas com hash, limite de tentativas erradas e bloqueio de envios vindos de outros sites.
- Para colocar na internet: HTTPS, `SECRET_KEY` fixa no ambiente e `COOKIE_SEGURO=1`.
- `COROINHAS_DADOS` aponta outra pasta de dados (útil para testes sem afetar os dados reais).

## Identidade visual

Azul mariano da abóbada da basílica (`#12215f` → `#3b5bdb`), dourado dos arcos (`#f5c451`) e o vermelho da batina
(`#d6293a`); fontes Fredoka (títulos) e Nunito. Bootstrap 5.3 e Bootstrap Icons servidos de `static/vendor/` (sem CDN). Animações em CSS
(entrada das telas, vela e rosácea da ilustração, gavetas no celular) respeitando "reduzir movimento" do sistema.
