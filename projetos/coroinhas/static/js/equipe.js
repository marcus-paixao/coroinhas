// Equipe: busca e filtros, flag de Ausente, cadastro (incluir/editar/remover) e importação da planilha.
(function () {
  "use strict";

  const A = window.App;
  const { el, esc, normalizar } = A;
  const MEMBROS = new Map(window.MEMBROS.map((m) => [m.id, m]));
  const modal = new bootstrap.Modal(el("modalMembro"));
  const form = el("formMembro");
  let editando = null;
  let apelidoManual = false;

  // ---------------------------------------------------------------- busca e filtros
  let filtro = "todos";
  function filtrar() {
    const busca = normalizar(el("busca")?.value);
    let visiveis = 0;
    document.querySelectorAll("#grade .membro").forEach((c) => {
      const ok = (!busca || c.dataset.busca.includes(busca)) &&
        (filtro === "todos" || (filtro === "ausentes" ? c.dataset.ausente === "1" : c.dataset.tipo === filtro));
      c.hidden = !ok;
      visiveis += ok;
    });
    if (el("nenhum")) el("nenhum").hidden = visiveis > 0;
  }
  el("busca")?.addEventListener("input", filtrar);
  el("filtroTipo")?.addEventListener("click", (e) => {
    const b = e.target.closest("[data-filtro]");
    if (!b) return;
    filtro = b.dataset.filtro;
    el("filtroTipo").querySelectorAll("button").forEach((x) => x.classList.toggle("ativo", x === b));
    filtrar();
  });

  // ---------------------------------------------------------------- flag de ausente no cartão
  document.querySelectorAll("[data-ausencia]").forEach((sw) => {
    const card = sw.closest(".membro");
    const m = MEMBROS.get(sw.dataset.ausencia);
    const aplicar = (ausente) => {
      card.classList.toggle("ausente", ausente);
      card.dataset.ausente = ausente ? "1" : "0";
      card.querySelector("[data-status]").textContent = ausente ? "🔕 Ausente — não entra nos alertas" : "✅ Disponível para a escala";
      sw.setAttribute("aria-checked", String(ausente));
    };
    A.ligarSwitch(sw, async (ausente) => {
      await A.post(`/api/membros/${m.id}/ausencia`, { ausente });
      aplicar(ausente);
      A.toast(ausente ? `${esc(m.apelido)} marcado(a) como ausente — sem alertas por enquanto 🔕` : `${esc(m.apelido)} está de volta! 🎉`, "ok",
        async () => {
          try { await A.post(`/api/membros/${m.id}/ausencia`, { ausente: !ausente }); aplicar(!ausente); } catch (e) { A.erro(e); }
        });
    });
  });

  // ---------------------------------------------------------------- cadastro
  function sugerirApelido(nome) {
    const conectores = new Set(["da", "de", "do", "das", "dos", "e"]);
    const compostos = new Set(["maria", "joao", "ana", "anna", "jose", "pedro", "luiz", "luis"]);
    const p = nome.trim().split(/\s+/).filter((x) => x && !conectores.has(x.toLowerCase()));
    if (!p.length) return "";
    const usados = new Set([...MEMBROS.values()].filter((m) => m.id !== editando).map((m) => normalizar(m.apelido)));
    let n = compostos.has(normalizar(p[0])) && p[1] ? 2 : 1;
    let ap = p.slice(0, n).join(" ");
    while (usados.has(normalizar(ap)) && n < p.length) ap = p.slice(0, ++n).join(" ");
    return ap.replace(/(^|\s)\S/g, (c) => c.toUpperCase());
  }

  const swAusente = el("switchAusente");
  const marcarAusente = (v) => {
    swAusente.setAttribute("aria-checked", String(v));
    el("blocoAusencia").classList.toggle("ligado", v);
  };
  swAusente.addEventListener("click", () => marcarAusente(swAusente.getAttribute("aria-checked") !== "true"));

  function abrir(m) {
    editando = m?.id || null;
    apelidoManual = !!m;
    form.reset();
    el("membroErro").textContent = "";
    el("membroTitulo").textContent = m ? `Editar ${m.apelido}` : "Novo cadastro";
    for (const campo of ["nome", "apelido", "tipo", "nascimento", "telefone", "responsavel", "observacoes", "motivo_ausencia", "ausente_ate"]) {
      form[campo].value = m?.[campo] ?? (campo === "tipo" ? "coroinha" : "");
    }
    marcarAusente(!!m?.ausente);
    modal.show();
  }
  el("modalMembro").addEventListener("shown.bs.modal", () => form.nome.focus());
  form.nome.addEventListener("input", () => { if (!apelidoManual) form.apelido.value = sugerirApelido(form.nome.value); });
  form.apelido.addEventListener("input", () => { apelidoManual = true; });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const corpo = Object.fromEntries(new FormData(form));
    corpo.ausente = swAusente.getAttribute("aria-checked") === "true";
    try {
      const r = editando ? await A.put(`/api/membros/${editando}`, corpo) : await A.post("/api/membros", corpo);
      A.recarregarCom(editando ? "Cadastro atualizado" : `${esc(r.membro.apelido)} cadastrado(a)! 🎉`);
    } catch (err) {
      el("membroErro").textContent = err.message;
    }
  });

  // ---------------------------------------------------------------- importação da planilha
  const input = el("inputPlanilha");
  input.addEventListener("change", async () => {
    const arq = input.files[0];
    if (!arq) return;
    const dados = new FormData();
    dados.append("arquivo", arq);
    try {
      A.toast("Lendo a planilha…");
      const r = await A.api("/api/planilha", { method: "POST", body: dados });
      A.recarregarCom(`Planilha importada: ${r.novos} novo(s), ${r.atualizados} atualizado(s) ✅`);
    } catch (err) {
      A.erro(err);
    } finally {
      input.value = "";
    }
  });

  // ---------------------------------------------------------------- cliques
  document.addEventListener("click", async (e) => {
    if (e.target.closest("[data-novo]")) return abrir(null);
    if (e.target.closest("[data-importar]")) return input.click();
    const ed = e.target.closest("[data-editar]");
    if (ed) return abrir(MEMBROS.get(ed.dataset.editar));
    const rm = e.target.closest("[data-remover]");
    if (rm) {
      const m = MEMBROS.get(rm.dataset.remover);
      const ok = await A.confirmar(`Remover ${m.apelido}?`,
        "O cadastro será apagado e a pessoa sai de todas as escalas. Se for só uma pausa, prefira marcar como <strong>Ausente</strong>.");
      if (!ok) return;
      try {
        await A.del(`/api/membros/${m.id}`);
        const card = rm.closest(".membro");
        card.style.transition = "opacity .25s, transform .25s";
        card.style.opacity = "0";
        card.style.transform = "scale(.9)";
        setTimeout(() => A.recarregarCom(`${esc(m.apelido)} removido(a)`), 250);
      } catch (err) { A.erro(err); }
    }
  });
})();
