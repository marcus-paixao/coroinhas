// SacroByte — Widget de chat flutuante integrado ao Google Gemini (`POST /chat`).
(function () {
  "use strict";

  const A = window.App;
  const { el, esc } = A;
  const btnFab = el("btnSacrobyte");
  const janela = el("janelaSacrobyte");
  const lista = el("sacrobyteMensagens");
  const form = el("formSacrobyte");
  const input = el("inputSacrobyte");
  const btnEnviar = el("btnEnviarSacrobyte");
  const sugestoes = el("sacrobyteSugestoes");
  if (!btnFab || !janela) return;

  const AVATAR_BOT = lista.querySelector(".sb-avatar")?.innerHTML || "";
  const BOAS_VINDAS = lista.innerHTML;

  function formatarTexto(s) {
    return esc(s)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\n/g, "<br>");
  }

  function rolarParaBaixo() {
    lista.scrollTop = lista.scrollHeight;
  }

  function alternarJanela(abrir) {
    const aberta = abrir !== undefined ? abrir : janela.hidden;
    janela.hidden = !aberta;
    btnFab.setAttribute("aria-expanded", String(aberta));
    if (aberta) {
      rolarParaBaixo();
      setTimeout(() => input.focus(), 80);
    }
  }

  function adicionarMensagem(texto, autor = "bot", erro = false) {
    const div = document.createElement("div");
    div.className = `sb-msg ${autor === "user" ? "sb-user" : "sb-bot"}${erro ? " sb-erro" : ""}`;
    div.innerHTML = autor === "user"
      ? `<div class="sb-balao">${esc(texto)}</div>`
      : `<div class="sb-avatar">${AVATAR_BOT}</div><div class="sb-balao">${formatarTexto(texto)}</div>`;
    lista.append(div);
    rolarParaBaixo();
    return div;
  }

  function mostrarDigitando() {
    const div = document.createElement("div");
    div.className = "sb-msg sb-bot sb-digitando";
    div.innerHTML = `<div class="sb-avatar">${AVATAR_BOT}</div>
      <div class="sb-balao"><span class="sb-pontos"><i></i><i></i><i></i></span> Digitando…</div>`;
    lista.append(div);
    rolarParaBaixo();
    return div;
  }

  async function enviarMensagem(texto) {
    const msg = (texto || "").trim();
    if (!msg) return;
    input.value = "";
    input.disabled = true;
    btnEnviar.disabled = true;
    if (sugestoes) sugestoes.hidden = true;

    adicionarMensagem(msg, "user");
    const digitando = mostrarDigitando();

    try {
      const r = await A.api("/chat", { base: "", method: "POST", json: { mensagem: msg } });
      digitando.remove();
      adicionarMensagem(r.resposta, "bot");
    } catch (err) {
      digitando.remove();
      adicionarMensagem(err.message || "Falha ao falar com o SacroByte.", "bot", true);
    } finally {
      input.disabled = false;
      btnEnviar.disabled = false;
      input.focus();
    }
  }

  btnFab.addEventListener("click", () => alternarJanela());
  el("btnFecharChat")?.addEventListener("click", () => alternarJanela(false));

  el("btnLimparChat")?.addEventListener("click", async () => {
    try {
      await A.api("/chat/limpar", { base: "", method: "POST", json: {} });
      lista.innerHTML = BOAS_VINDAS;
      if (sugestoes) sugestoes.hidden = false;
      A.toast("Conversa reiniciada com o SacroByte ✨");
    } catch (err) {
      A.erro(err);
    }
  });

  sugestoes?.addEventListener("click", (e) => {
    const b = e.target.closest("[data-pergunta]");
    if (b) enviarMensagem(b.dataset.pergunta);
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    enviarMensagem(input.value);
  });
})();
