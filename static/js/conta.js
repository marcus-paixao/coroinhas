// Minha conta: trocar a própria senha e, para coordenadores, criar/editar/remover contas.
(function () {
  "use strict";

  const A = window.App;
  const { el, esc } = A;
  const { eu, contas, senha_min: SENHA_MIN } = window.CONTA;
  const CONTAS = new Map(contas.map((c) => [c.id, c]));
  const site = { base: "" };          // estas APIs ficam em /conta/api, fora do projeto

  // ---------------------------------------------------------------- minha senha
  const formSenha = el("formSenha");
  formSenha.addEventListener("submit", async (e) => {
    e.preventDefault();
    const { atual, nova, repetir } = Object.fromEntries(new FormData(formSenha));
    const erro = el("senhaErro");
    if (nova.length < SENHA_MIN) { erro.textContent = `A nova senha precisa ter pelo menos ${SENHA_MIN} caracteres.`; return; }
    if (nova !== repetir) { erro.textContent = "As senhas novas não conferem."; return; }
    try {
      await A.api("/conta/api/senha", { ...site, method: "POST", json: { atual, nova } });
      formSenha.reset();
      erro.textContent = "";
      A.toast("Senha trocada ✅");
    } catch (err) {
      erro.textContent = err.message;
    }
  });

  // ---------------------------------------------------------------- contas (só coordenadores)
  const form = el("formConta");
  if (!form) return;
  const modal = new bootstrap.Modal(el("modalConta"));
  let editando = null;

  function gerarSenha() {
    const letras = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";   // sem 0/O, 1/l/I
    const n = new Uint32Array(10);
    crypto.getRandomValues(n);
    return [...n].map((x) => letras[x % letras.length]).join("");
  }
  el("btnGerar").addEventListener("click", () => { form.senha.value = gerarSenha(); });

  function abrir(c) {
    editando = c?.id ?? null;
    const proprio = editando === eu;
    form.reset();
    el("contaErro").textContent = "";
    el("contaTitulo").textContent = c ? `Editar ${c.nome}` : "Nova conta";
    form.nome.value = c?.nome ?? "";
    form.login.value = c?.login ?? "";
    form.login.disabled = !!c;
    form.coordenador.checked = !!c?.coordenador;
    form.coordenador.disabled = proprio;
    el("blocoSenha").hidden = proprio;      // a própria senha se troca no cartão ao lado
    el("rotuloSenha").textContent = c ? "Nova senha (deixe em branco para manter)" : "Senha";
    if (!c) form.senha.value = gerarSenha();
    modal.show();
  }
  el("modalConta").addEventListener("shown.bs.modal", () => form.nome.focus());

  document.querySelector("[data-nova]").addEventListener("click", () => abrir(null));
  document.querySelectorAll("[data-editar]").forEach((b) => b.addEventListener("click", () => abrir(CONTAS.get(Number(b.dataset.editar)))));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const corpo = {
      nome: form.nome.value, login: form.login.value, senha: form.senha.value, coordenador: form.coordenador.checked,
    };
    try {
      if (editando) {
        await A.api(`/conta/api/usuarios/${editando}`, { ...site, method: "PUT", json: corpo });
        A.recarregarCom(corpo.senha ? `Conta atualizada e senha redefinida. Passe a nova senha para ${esc(corpo.nome)}.` : "Conta atualizada");
      } else {
        const r = await A.api("/conta/api/usuarios", { ...site, method: "POST", json: corpo });
        A.recarregarCom(`Conta “${esc(r.conta.login)}” criada! 🎉`);
      }
    } catch (err) {
      el("contaErro").textContent = err.message;
    }
  });

  document.querySelectorAll("[data-remover]").forEach((b) => b.addEventListener("click", async () => {
    const c = CONTAS.get(Number(b.dataset.remover));
    const ok = await A.confirmar("Remover conta?",
      `<strong>${esc(c.nome)}</strong> (${esc(c.login)}) não vai mais conseguir entrar. Os cadastros e escalas não são afetados.`, "Remover");
    if (!ok) return;
    try {
      await A.api(`/conta/api/usuarios/${c.id}`, { ...site, method: "DELETE" });
      A.recarregarCom(`Conta de ${esc(c.nome)} removida`);
    } catch (err) { A.erro(err); }
  }));
})();
