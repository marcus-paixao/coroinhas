// Funções & Missas: cadastro das funções do altar e das missas fixas (com o editor de vagas).
(function () {
  "use strict";

  const A = window.App;
  const { el, esc } = A;
  const FUNCOES = new Map(window.FUNCOES.map((f) => [f.id, f]));
  const HORARIOS = new Map(window.HORARIOS.map((h) => [h.id, h]));

  // ---------------------------------------------------------------- função
  const modalFuncao = new bootstrap.Modal(el("modalFuncao"));
  const formF = el("formFuncao");
  let funcaoEditando = null;
  let escolha = { emoji: "⭐", cor: "#2f4ac2" };

  function marcarEscolhas() {
    el("escolhaEmoji").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.valor === escolha.emoji)));
    el("escolhaCor").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.valor === escolha.cor)));
    el("previaFuncao").innerHTML = A.chipFuncao({ ...escolha, nome: formF.nome.value || "Nova função" });
  }
  el("escolhaEmoji").addEventListener("click", (e) => { const b = e.target.closest("[data-valor]"); if (b) { escolha.emoji = b.dataset.valor; marcarEscolhas(); } });
  el("escolhaCor").addEventListener("click", (e) => { const b = e.target.closest("[data-valor]"); if (b) { escolha.cor = b.dataset.valor; marcarEscolhas(); } });
  formF.nome.addEventListener("input", marcarEscolhas);

  function abrirFuncao(f) {
    funcaoEditando = f?.id || null;
    formF.nome.value = f?.nome || "";
    escolha = { emoji: f?.emoji || "⭐", cor: f?.cor || "#2f4ac2" };
    el("funcaoTitulo").textContent = f ? "Editar função" : "Nova função";
    el("funcaoErro").textContent = "";
    marcarEscolhas();
    modalFuncao.show();
  }
  el("modalFuncao").addEventListener("shown.bs.modal", () => formF.nome.focus());

  formF.addEventListener("submit", async (e) => {
    e.preventDefault();
    const corpo = { nome: formF.nome.value, ...escolha };
    try {
      if (funcaoEditando) await A.put(`/api/funcoes/${funcaoEditando}`, corpo);
      else await A.post("/api/funcoes", corpo);
      A.recarregarCom(funcaoEditando ? "Função atualizada" : "Função criada ✨");
    } catch (err) { el("funcaoErro").textContent = err.message; }
  });

  // ---------------------------------------------------------------- missa fixa
  const modalHorario = new bootstrap.Modal(el("modalHorario"));
  const formH = el("formHorario");
  const editor = window.EditorVagas(el("editorVagasHorario"), window.FUNCOES);
  let horarioEditando = null;

  function abrirHorario(h) {
    horarioEditando = h?.id || null;
    formH.dia_semana.value = h?.dia_semana ?? 0;
    formH.hora.value = h?.hora || "10:00";
    formH.titulo.value = h?.titulo || "";
    formH.reservas.value = h?.reservas ?? 2;
    editor.definir((h?.vagas || []).map((fs) => ({ funcoes: fs })));
    el("horarioTitulo").textContent = h ? "Editar missa fixa" : "Nova missa fixa";
    el("horarioErro").textContent = "";
    modalHorario.show();
  }

  formH.addEventListener("submit", async (e) => {
    e.preventDefault();
    const corpo = { dia_semana: Number(formH.dia_semana.value), hora: formH.hora.value, titulo: formH.titulo.value,
                    reservas: Number(formH.reservas.value || 0), vagas: editor.obter().map((v) => v.funcoes) };
    try {
      if (horarioEditando) await A.put(`/api/horarios/${horarioEditando}`, corpo);
      else await A.post("/api/horarios", corpo);
      A.recarregarCom(horarioEditando ? "Missa fixa atualizada" : "Missa fixa criada ⛪");
    } catch (err) { el("horarioErro").textContent = err.message; }
  });

  // ---------------------------------------------------------------- cliques
  document.addEventListener("click", async (e) => {
    const alvo = (attr) => e.target.closest(`[${attr}]`)?.getAttribute(attr);
    try {
      if (e.target.closest("[data-nova-funcao]")) abrirFuncao(null);
      else if (e.target.closest("[data-novo-horario]")) abrirHorario(null);
      else if (alvo("data-editar-funcao")) abrirFuncao(FUNCOES.get(alvo("data-editar-funcao")));
      else if (alvo("data-editar-horario")) abrirHorario(HORARIOS.get(alvo("data-editar-horario")));
      else if (alvo("data-remover-funcao")) {
        const f = FUNCOES.get(alvo("data-remover-funcao"));
        if (!await A.confirmar(`Remover “${f.nome}”?`, "A função sai de todas as vagas das missas fixas e das escalas onde aparece.")) return;
        await A.del(`/api/funcoes/${f.id}`);
        A.recarregarCom(`Função ${esc(f.nome)} removida`);
      } else if (alvo("data-remover-horario")) {
        const h = HORARIOS.get(alvo("data-remover-horario"));
        if (!await A.confirmar("Remover missa fixa?",
          `<strong>${A.DIAS[h.dia_semana]} ${A.formatarHora(h.hora)}</strong> deixa de ser criada nas próximas semanas. As escalas já criadas continuam.`)) return;
        await A.del(`/api/horarios/${h.id}`);
        A.recarregarCom("Missa fixa removida");
      }
    } catch (err) { A.erro(err); }
  });
})();
