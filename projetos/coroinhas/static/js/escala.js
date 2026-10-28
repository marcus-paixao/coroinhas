// Escala da semana: missas e vagas, escolher quem serve, pendências, missas extras e exportação para o WhatsApp.
(function () {
  "use strict";

  const A = window.App;
  const { el, esc, avatar, chipFuncao, dataCurta, formatarHora, diaSemana, rotuloMissa, estaAusente, normalizar } = A;
  let D = window.ESCALA;                 // estado da semana vindo de /api/semana
  let porId = new Map();                 // membro por id
  let funcoes = new Map();               // função por id
  let alvo = null;                       // vaga sendo preenchida: { escala, missa, atual, titulo }
  let missaEditando = null;              // id da missa no modal (null = nova)

  const modalEscolher = new bootstrap.Modal(el("modalEscolher"));
  const modalVagas = new bootstrap.Modal(el("modalVagas"));
  const modalMissa = new bootstrap.Modal(el("modalMissa"));
  const editor = window.EditorVagas(el("editorVagasMissa"), D.funcoes);

  // ---------------------------------------------------------------- estado
  function indexar() {
    porId = new Map(D.membros.map((m) => [m.id, m]));
    funcoes = new Map(D.funcoes.map((f) => [f.id, f]));
  }

  async function recarregar(destacar = null) {
    D = await A.api(`/api/semana?semana=${D.semana}`);
    render(destacar);
  }

  const nomesFuncoes = (ids) => ids.map((f) => funcoes.get(f)?.nome).filter(Boolean).join(" / ");
  const membrosDaMissa = (m) => [...m.vagas, ...m.reservas].map((e) => e.membro_id).filter(Boolean);
  const escalavel = (m) => D.tipos_escalaveis.includes(m.tipo);

  // ---------------------------------------------------------------- desenho
  function render(destacar = null) {
    indexar();
    el("tituloSemana").textContent = D.titulo;
    renderAcoes();
    renderMissas(destacar);
    renderLateral();
    atualizarBadge();
  }

  function renderAcoes() {
    const p = [];
    if (D.horarios_faltando > 0) {
      p.push(`<button class="btn btn-azul" data-acao="gerar"><i class="bi bi-stars"></i>
        ${D.missas.length ? `Criar ${D.horarios_faltando} missa(s) que faltam` : "Criar missas da semana"}</button>`);
    }
    p.push(`<button class="btn btn-contorno" data-acao="nova"><i class="bi bi-calendar-plus"></i> Missa extra</button>`);
    if (D.missas.length) {
      p.push(`<button class="btn btn-ouro" data-acao="whatsapp"><i class="bi bi-whatsapp"></i> Copiar p/ WhatsApp</button>`);
      p.push(`<button class="btn btn-contorno" data-acao="imagem"><i class="bi bi-image"></i> Imagem da escala</button>`);
      if (D.tem_semana_anterior) {
        p.push(`<div class="dropdown">
          <button class="btn-icone" data-bs-toggle="dropdown" aria-expanded="false" aria-label="Mais opções"><i class="bi bi-three-dots"></i></button>
          <ul class="dropdown-menu dropdown-menu-end cartao p-1">
            <li><button class="opcao-membro" data-acao="copiar"><i class="bi bi-copy"></i> Repetir quem serviu na semana anterior</button></li>
          </ul></div>`);
      }
    }
    el("acoes").innerHTML = p.join("");
  }

  function problemaDe(id, missa, contagem) {
    if (!id) return null;
    const m = porId.get(id);
    if (m && estaAusente(m, missa.data)) return "Marcado(a) como ausente";
    if ((contagem.get(id) || 0) > 1) return "Escalado(a) duas vezes nesta missa";
    return null;
  }

  function botaoPessoa(item, missa, contagem, rotuloVazio, destacar) {
    const m = item.membro_id ? porId.get(item.membro_id) : null;
    const problema = problemaDe(item.membro_id, missa, contagem);
    const classes = ["vaga-pessoa", m ? "" : "vazia", problema ? "problema" : "", destacar === item.id ? "pop" : ""].join(" ");
    const dentro = m
      ? `${avatar(m, 28)}<span class="nome">${esc(m.apelido)}</span>${problema ? '<i class="bi bi-exclamation-octagon-fill text-danger"></i>' : ""}`
      : `<span class="mais"><i class="bi bi-plus-lg"></i></span><span class="nome">${esc(rotuloVazio)}</span>`;
    return `<button type="button" class="${classes}" data-escala="${item.id}" data-missa="${missa.id}" data-rotulo="${esc(rotuloVazio)}"
      ${problema ? `title="${esc(problema)}"` : ""}>${dentro}</button>`;
  }

  function renderMissas(destacar) {
    if (!D.missas.length) {
      const fixos = D.horarios.map((h) => `${A.DIAS[h.dia_semana].slice(0, 3)} ${formatarHora(h.hora)}`).join(", ");
      el("missas").innerHTML = `<div class="cartao"><div class="vazio entrar"><span class="emoji">⛪</span><h3>Nenhuma missa nesta semana</h3>
        <p class="mb-3">${D.horarios.length ? `Crie as missas a partir das missas fixas (${esc(fixos)}).` : "Cadastre as missas fixas em “Funções & Missas” ou adicione uma missa extra."}</p>
        ${D.horarios.length ? '<button class="btn btn-azul" data-acao="gerar"><i class="bi bi-stars"></i> Criar missas da semana</button>' : ""}</div></div>`;
      return;
    }
    el("missas").innerHTML = `<div class="missas">${D.missas.map((missa, i) => {
      const contagem = new Map();
      membrosDaMissa(missa).forEach((id) => contagem.set(id, (contagem.get(id) || 0) + 1));
      const preenchidas = missa.vagas.filter((v) => v.membro_id).length;
      const pct = missa.vagas.length ? (100 * preenchidas) / missa.vagas.length : 100;
      return `<article class="cartao missa ${destacar ? "" : "entrar"}" style="--i:${i + 2}">
        <header class="missa-topo">
          <span class="missa-hora">${formatarHora(missa.hora)}</span>
          <div class="missa-dia"><strong>${diaSemana(missa.data)}</strong><span>${dataCurta(missa.data)}${missa.titulo ? ` · ${esc(missa.titulo)}` : ""}</span></div>
          <div class="acoes">
            <button type="button" class="btn-icone" data-editar-missa="${missa.id}" aria-label="Editar missa"><i class="bi bi-pencil"></i></button>
            <button type="button" class="btn-icone" data-remover-missa="${missa.id}" aria-label="Remover missa"><i class="bi bi-trash3"></i></button>
          </div>
        </header>
        <div class="missa-progresso ${pct === 100 ? "completo" : ""}"><div style="width:${pct}%"></div></div>
        <ul class="vagas">
          ${missa.vagas.length ? "" : '<li class="vaga justify-content-center text-secondary">Sem vagas — toque no lápis para adicionar.</li>'}
          ${missa.vagas.map((v) => `<li class="vaga">
            <div class="vaga-funcoes"><div class="chips">${v.funcoes.map((f) => funcoes.get(f)).filter(Boolean).map(chipFuncao).join("")}</div></div>
            ${botaoPessoa(v, missa, contagem, "Escalar", destacar)}</li>`).join("")}
        </ul>
        ${missa.reservas.length ? `<div class="reservas"><h4>🙋 Reservas</h4><div class="reservas-grade">
          ${missa.reservas.map((r, j) => botaoPessoa(r, missa, contagem, `Reserva ${j + 1}`, destacar)).join("")}</div></div>` : ""}
      </article>`;
    }).join("")}</div>`;
  }

  function renderLateral() {
    if (!D.missas.length) { el("lateral").innerHTML = ""; return; }
    const p = D.pendencias;
    const pessoas = (ids) => ids.map((id) => porId.get(id)).filter(Boolean);
    const semEscala = pessoas(p.sem_escala);
    const ausentes = pessoas(p.ausentes);
    const tudoCerto = !p.vagas_abertas && !semEscala.length && !p.escalados_ausentes.length && !p.duplicados.length;
    const h = [];
    if (tudoCerto) {
      h.push(`<div class="alerta-box verde pop"><i class="bi bi-check-circle-fill"></i><div><strong>Escala completa! 🎉</strong>Todas as vagas preenchidas e todo mundo escalado.</div></div>`);
    } else if (p.vagas_abertas) {
      h.push(`<div class="alerta-box laranja"><i class="bi bi-exclamation-triangle-fill"></i><div><strong>${p.vagas_abertas} de ${p.total_vagas} vagas em aberto</strong>As vagas tracejadas ainda precisam de alguém.</div></div>`);
    }
    if (p.escalados_ausentes.length || p.duplicados.length) {
      const linhas = [
        ...pessoas(p.escalados_ausentes).map((m) => `• ${esc(m.apelido)} está marcado(a) como ausente`),
        ...p.duplicados.map((d) => {
          const missa = D.missas.find((x) => x.id === d.missa_id);
          return `• ${esc(porId.get(d.membro_id)?.apelido)} aparece 2× na missa de ${A.DIAS[new Date(missa.data + "T12:00").getDay()].slice(0, 3)} ${formatarHora(missa.hora)}`;
        }),
      ];
      h.push(`<div class="alerta-box vermelho"><i class="bi bi-exclamation-octagon-fill"></i><div><strong>Confira a escala</strong>${linhas.join("<br>")}</div></div>`);
    }
    h.push(`<section class="cartao cartao-pad">
      <div class="titulo-secao mb-2"><h2 style="font-size:17px">Faltando na escala</h2>
        <span class="tag ${semEscala.length ? "tag-laranja" : "tag-verde"}">${semEscala.length}</span></div>
      ${semEscala.length
        ? `<p class="small text-secondary mb-2">Toque num nome para escalar direto numa vaga livre.</p>
           <div class="lista-pessoas">${semEscala.map((m, i) => `<button type="button" class="pessoa-pill alerta entrar" style="--i:${i}"
             data-escalar-pessoa="${m.id}">${avatar(m, 26)} ${esc(m.apelido)}</button>`).join("")}</div>`
        : '<p class="small text-secondary mb-0">Todo mundo disponível já está escalado. 🙌</p>'}
      ${ausentes.length ? `<div class="rotulo-lista"><i class="bi bi-bell-slash"></i> Ausentes (sem alerta)</div>
        <div class="lista-pessoas">${ausentes.map((m) => `<span class="pessoa-pill apagado" title="${esc(m.motivo_ausencia || "")}">${avatar(m, 26, true)} ${esc(m.apelido)}</span>`).join("")}</div>` : ""}
    </section>`);
    el("lateral").innerHTML = h.join("");
  }

  function atualizarBadge() {
    if (D.semana !== D.atual) return;
    const n = D.missas.length ? D.pendencias.vagas_abertas + D.pendencias.sem_escala.length : 0;
    document.querySelectorAll('a[href$="/escala"]').forEach((a) => {
      let b = a.querySelector(".menu-badge");
      if (!n) return b?.remove();
      if (!b) { b = document.createElement("span"); b.className = "menu-badge"; a.append(b); }
      b.textContent = n;
    });
  }

  // ---------------------------------------------------------------- escolher quem serve
  function abrirSeletor(escalaId, missaId, rotulo) {
    const missa = D.missas.find((m) => m.id === missaId);
    const item = [...missa.vagas, ...missa.reservas].find((e) => e.id === escalaId);
    const ehVaga = missa.vagas.includes(item);
    alvo = { escala: escalaId, missa, atual: item.membro_id };
    el("escolherTitulo").innerHTML = `${esc(ehVaga ? nomesFuncoes(item.funcoes) || "Vaga" : rotulo)}<small class="modal-subtitulo">${esc(rotuloMissa(missa))}</small>`;
    el("rodapeEscolher").hidden = !item.membro_id;
    el("buscaMembro").value = "";
    renderListaMembros();
    modalEscolher.show();
  }

  function renderListaMembros() {
    const { missa, atual } = alvo;
    const filtro = normalizar(el("buscaMembro").value);
    const ondeServe = new Map();
    D.missas.forEach((mi) => membrosDaMissa(mi).forEach((id) =>
      ondeServe.set(id, [...(ondeServe.get(id) || []), `${A.DIAS[new Date(mi.data + "T12:00").getDay()].slice(0, 3)} ${formatarHora(mi.hora)}`])));
    const nestaMissa = new Set(membrosDaMissa(missa));
    const lista = D.membros
      .filter((m) => !filtro || normalizar(`${m.nome} ${m.apelido}`).includes(filtro))
      .sort((a, b) => a.vezes_mes - b.vezes_mes || a.apelido.localeCompare(b.apelido));
    const ausente = (m) => estaAusente(m, missa.data);
    const info = (m) => [`${m.vezes_mes}× no mês`, ondeServe.has(m.id) ? `nesta semana: ${ondeServe.get(m.id).join(", ")}` : ""].filter(Boolean).join(" · ");
    const grupos = [
      { titulo: "⭐ Ainda sem escala nesta semana", itens: lista.filter((m) => escalavel(m) && !ausente(m) && !ondeServe.has(m.id)), info },
      { titulo: "✔ Já escalados nesta semana", itens: lista.filter((m) => escalavel(m) && !ausente(m) && ondeServe.has(m.id)),
        info: (m) => (nestaMissa.has(m.id) && m.id !== atual ? "⚠️ já está nesta missa · " : "") + info(m) },
      { titulo: "Outros", itens: lista.filter((m) => !escalavel(m) && !ausente(m)), info: (m) => ({ coroinha: "Coroinha", cerimoniario: "Cerimoniário", coordenacao: "Coordenação" })[m.tipo] },
      { titulo: "🔕 Ausentes", itens: lista.filter(ausente), apagado: true,
        info: (m) => `${m.motivo_ausencia || "Ausente"}${m.ausente_ate ? ` até ${dataCurta(m.ausente_ate)}` : ""}` },
    ].filter((g) => g.itens.length);
    let n = 0;
    el("listaMembros").innerHTML = grupos.length
      ? grupos.map((g) => `<h5>${g.titulo} (${g.itens.length})</h5>${g.itens.map((m) => `
          <button type="button" class="opcao-membro ${m.id === atual ? "atual" : ""} ${g.apagado ? "apagado" : ""}" style="--i:${Math.min(n++, 25)}" data-membro="${m.id}">
            ${avatar(m, 38, g.apagado)}<span class="info"><strong>${esc(m.apelido)}</strong><small>${esc(g.info(m))}</small></span>
            ${g.apagado ? '<i class="bi bi-exclamation-triangle text-warning"></i>' : ""}${m.id === atual ? '<i class="bi bi-check-lg text-primary"></i>' : ""}
          </button>`).join("")}`).join("")
      : `<p class="text-center text-secondary my-3">${D.membros.length ? "Ninguém encontrado." : "Cadastre os coroinhas primeiro."}</p>`;
  }

  async function escalar(escalaId, membroId, comDesfazer = true) {
    try {
      const r = await A.post(`/api/escalas/${escalaId}`, { membro_id: membroId });
      await recarregar(escalaId);
      const nome = membroId ? porId.get(membroId)?.apelido : null;
      A.toast(nome ? `${esc(nome)} escalado(a) ✨` : "Vaga liberada", "ok",
        comDesfazer ? () => escalar(escalaId, r.anterior, false) : null);
    } catch (e) {
      A.erro(e);
    }
  }

  // ---------------------------------------------------------------- escalar a partir da pessoa
  function abrirVagasDe(membroId) {
    const m = porId.get(membroId);
    el("vagasTitulo").textContent = `Escalar ${m.apelido} em…`;
    const blocos = D.missas.map((missa) => {
      const vagas = missa.vagas.filter((v) => !v.membro_id);
      const reservas = missa.reservas.map((r, i) => ({ ...r, i })).filter((r) => !r.membro_id);
      if (!vagas.length && !reservas.length) return "";
      return `<h5>${esc(rotuloMissa(missa))}</h5>
        ${vagas.map((v) => `<button type="button" class="opcao-membro" data-vaga="${v.id}" data-membro="${m.id}">
          <span class="chips flex-grow-1">${v.funcoes.map((f) => funcoes.get(f)).filter(Boolean).map(chipFuncao).join("")}</span><i class="bi bi-plus-lg text-primary"></i></button>`).join("")}
        ${reservas.map((r) => `<button type="button" class="opcao-membro" data-vaga="${r.id}" data-membro="${m.id}">
          <span class="info"><strong>🙋 Reserva ${r.i + 1}</strong></span><i class="bi bi-plus-lg text-primary"></i></button>`).join("")}`;
    }).join("");
    el("listaVagas").innerHTML = blocos || `<div class="vazio"><span class="emoji">🧩</span><h3>Não há vagas livres</h3>
      <p class="mb-0">Adicione uma vaga ou reserva editando a missa (ícone de lápis).</p></div>`;
    modalVagas.show();
  }

  // ---------------------------------------------------------------- criar / editar missa
  function abrirMissa(missa) {
    const f = el("formMissa");
    missaEditando = missa?.id || null;
    el("missaTitulo").textContent = missa ? "Editar missa" : "Nova missa";
    el("missaErro").textContent = "";
    const base = D.horarios.find((h) => h.dia_semana === 0);
    const domingo = new Date(D.semana + "T12:00"); domingo.setDate(domingo.getDate() + 6);
    f.data.value = missa?.data || domingo.toISOString().slice(0, 10);
    f.hora.value = missa?.hora || base?.hora || "19:00";
    f.titulo.value = missa?.titulo || "";
    f.reservas.value = missa ? missa.reservas.length : base?.reservas ?? 2;
    editor.definir(missa ? missa.vagas : (base?.vagas || []).map((fs) => ({ funcoes: fs })));
    el("campoBase").hidden = !!missa || !D.horarios.length;
    el("selBase").innerHTML = `<option value="">Escolher…</option>` + D.horarios.map((h, i) =>
      `<option value="${i}">${A.DIAS[h.dia_semana]} ${formatarHora(h.hora)} (${h.vagas.length} vagas)</option>`).join("");
    modalMissa.show();
  }

  el("selBase").addEventListener("change", (e) => {
    const h = D.horarios[Number(e.target.value)];
    if (!h) return;
    editor.definir(h.vagas.map((fs) => ({ funcoes: fs })));
    el("formMissa").reservas.value = h.reservas;
  });

  el("formMissa").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    const corpo = { data: f.data.value, hora: f.hora.value, titulo: f.titulo.value, reservas: Number(f.reservas.value || 0),
                    vagas: editor.obter() };
    try {
      if (missaEditando) await A.put(`/api/missas/${missaEditando}`, corpo);
      else await A.post("/api/missas", corpo);
      modalMissa.hide();
      A.toast(missaEditando ? "Missa atualizada" : "Missa adicionada ⛪");
      if (!missaEditando && (corpo.data < D.semana || corpo.data >= D.proxima)) {
        location.href = `${window.API}/escala?semana=${corpo.data}`;       // missa de outra semana: vai até ela
      } else await recarregar();
    } catch (err) {
      el("missaErro").textContent = err.message;
    }
  });

  // ---------------------------------------------------------------- WhatsApp: texto e imagem
  async function copiarTexto() {
    try {
      const { texto } = await A.api(`/api/semana/whatsapp?semana=${D.semana}`);
      try {
        await A.copiar(texto);
        A.toast("Texto copiado! É só colar no WhatsApp 📲");
      } catch {
        await A.baixar(new Blob([texto], { type: "text/plain" }), `escala-${D.semana}.txt`);
      }
    } catch (e) { A.erro(e); }
  }

  function montarArte() {
    el("arteEscala").innerHTML = `
      <p class="exp-local">⛪ Basílica Nossa Senhora de Lourdes · Vila Isabel</p>
      <h1>Escala dos Coroinhas · <em>${esc(D.titulo)}</em></h1>
      <div class="exp-grade">${D.missas.map((missa) => {
        const reservas = missa.reservas.map((r) => porId.get(r.membro_id)?.apelido).filter(Boolean);
        return `<div class="exp-missa">
          <div class="missa-topo"><span class="missa-hora">${formatarHora(missa.hora)}</span>
            <div class="missa-dia"><strong>${diaSemana(missa.data)}</strong><span>${dataCurta(missa.data)}${missa.titulo ? ` · ${esc(missa.titulo)}` : ""}</span></div></div>
          ${missa.vagas.map((v) => {
            const m = porId.get(v.membro_id);
            return `<div class="exp-linha ${m ? "" : "vazia"}"><span>${funcoes.get(v.funcoes[0])?.emoji || ""} ${esc(nomesFuncoes(v.funcoes))}</span>
              <strong>${esc(m?.apelido || "a definir")}</strong></div>`;
          }).join("")}
          ${reservas.length ? `<div class="exp-reservas">🙋 Reservas: ${esc(reservas.join(", "))}</div>` : ""}
        </div>`;
      }).join("")}</div>
      <div class="exp-rodape">Pastoral dos Coroinhas e Cerimoniários ✝</div>`;
  }

  async function gerarImagem() {
    A.toast("Gerando imagem…");
    montarArte();
    const no = el("arteEscala");
    const opcoes = { pixelRatio: 2, cacheBust: true };
    let blob;
    try {
      blob = await htmlToImage.toBlob(no, opcoes);
    } catch {
      blob = await htmlToImage.toBlob(no, { ...opcoes, skipFonts: true }).catch(() => null);   // sem as fontes externas
    }
    if (!blob) return A.toast("Não consegui gerar a imagem 😕", "erro");
    const nome = `escala-coroinhas-${D.semana}.png`;
    // No celular abre o compartilhar nativo (direto pro WhatsApp); no computador, baixa o arquivo.
    if (!(await A.compartilhar(blob, nome, `Escala ${D.titulo}`))) await A.baixar(blob, nome);
  }

  // ---------------------------------------------------------------- eventos
  document.addEventListener("click", async (e) => {
    const acao = e.target.closest("[data-acao]")?.dataset.acao;
    const vaga = e.target.closest("[data-escala]");
    const editar = e.target.closest("[data-editar-missa]");
    const remover = e.target.closest("[data-remover-missa]");
    const pessoa = e.target.closest("[data-escalar-pessoa]");
    try {
      if (acao === "gerar") {
        const r = await A.post("/api/semana/gerar", { semana: D.semana });
        await recarregar();
        A.toast(`${r.criadas} missa(s) criada(s) ⛪`);
      } else if (acao === "nova") abrirMissa(null);
      else if (acao === "whatsapp") copiarTexto();
      else if (acao === "imagem") gerarImagem();
      else if (acao === "copiar") {
        if (!await A.confirmar("Repetir a semana anterior?", "As vagas e quem serviu em cada missa da semana anterior (mesmo dia e horário) vão substituir a escala desta semana.", "Repetir", "btn-azul")) return;
        await A.post("/api/semana/copiar-anterior", { semana: D.semana });
        await recarregar();
        A.toast("Escala copiada da semana anterior");
      } else if (vaga) abrirSeletor(vaga.dataset.escala, vaga.dataset.missa, vaga.dataset.rotulo);
      else if (editar) abrirMissa(D.missas.find((m) => m.id === editar.dataset.editarMissa));
      else if (remover) {
        const missa = D.missas.find((m) => m.id === remover.dataset.removerMissa);
        if (!await A.confirmar("Remover missa?", `A missa de <strong>${esc(rotuloMissa(missa))}</strong> e quem estava escalado nela serão removidos.`)) return;
        await A.del(`/api/missas/${missa.id}`);
        await recarregar();
        A.toast("Missa removida");
      } else if (pessoa) abrirVagasDe(pessoa.dataset.escalarPessoa);
    } catch (err) {
      A.erro(err);
    }
  });

  el("buscaMembro").addEventListener("input", renderListaMembros);
  el("modalEscolher").addEventListener("shown.bs.modal", () => { if (matchMedia("(pointer: fine)").matches) el("buscaMembro").focus(); });
  el("listaMembros").addEventListener("click", (e) => {
    const b = e.target.closest("[data-membro]");
    if (!b || !alvo) return;
    modalEscolher.hide();
    if (b.dataset.membro !== alvo.atual) escalar(alvo.escala, b.dataset.membro);
  });
  el("btnLiberar").addEventListener("click", () => { modalEscolher.hide(); escalar(alvo.escala, null); });
  el("listaVagas").addEventListener("click", (e) => {
    const b = e.target.closest("[data-vaga]");
    if (!b) return;
    modalVagas.hide();
    escalar(b.dataset.vaga, b.dataset.membro);
  });

  render();
})();
