// Utilidades comuns às telas: chamadas à API, avisos (toasts), confirmação, formatação e pedaços de HTML.
(function () {
  "use strict";

  const DIAS = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"];
  const el = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------------------------------------------------------------- API
  // url relativa ao projeto (window.API); passe { base: "" } para usar um caminho do site, como /conta/api/...
  async function api(url, opts = {}) {
    const { base = window.API, ...resto } = opts;
    const o = { ...resto, headers: { ...(resto.headers || {}) } };
    if (o.json !== undefined) {
      o.body = JSON.stringify(o.json);
      o.headers["Content-Type"] = "application/json";
      delete o.json;
    }
    let r;
    try {
      r = await fetch(base + url, o);
    } catch {
      throw new Error("Sem conexão com o servidor.");
    }
    const j = await r.json().catch(() => ({}));
    if (r.status === 401) {
      location.href = "/entrar?proximo=" + encodeURIComponent(location.pathname + location.search);
      throw new Error(j.erro || "Sessão expirada.");
    }
    if (!r.ok) throw new Error(j.erro || `Erro ${r.status}`);
    return j;
  }
  const post = (url, json) => api(url, { method: "POST", json });
  const put = (url, json) => api(url, { method: "PUT", json });
  const del = (url) => api(url, { method: "DELETE" });

  // ---------------------------------------------------------------- avisos
  function toast(msg, tipo = "ok", desfazer = null) {
    const t = document.createElement("div");
    t.className = `toast aviso ${tipo === "erro" ? "erro" : ""}`;
    t.setAttribute("role", "status");
    t.innerHTML = `<div class="d-flex align-items-center gap-2">
        <i class="bi ${tipo === "erro" ? "bi-exclamation-octagon-fill" : "bi-check-circle-fill text-warning"}"></i>
        <span class="flex-grow-1">${msg}</span>
        ${desfazer ? '<button type="button" class="aviso-desfazer">Desfazer</button>' : ""}
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Fechar"></button></div>`;
    el("toasts").append(t);
    const bt = new bootstrap.Toast(t, { delay: desfazer || tipo === "erro" ? 6000 : 3200 });
    if (desfazer) t.querySelector(".aviso-desfazer").addEventListener("click", () => { bt.hide(); desfazer(); });
    t.addEventListener("hidden.bs.toast", () => t.remove());
    bt.show();
  }
  const erro = (e) => toast(esc(e.message || e), "erro");

  // Aviso que sobrevive a um reload (para telas que recarregam depois de salvar)
  function recarregarCom(msg) {
    try { sessionStorage.setItem("aviso", msg); } catch { /* sem storage: só recarrega */ }
    location.reload();
  }
  document.addEventListener("DOMContentLoaded", () => {
    let msg = null;
    try { msg = sessionStorage.getItem("aviso"); sessionStorage.removeItem("aviso"); } catch { /* ignore */ }
    if (msg) toast(msg);
  });

  // ---------------------------------------------------------------- confirmação
  let modalConfirmar;
  function confirmar(titulo, html, rotulo = "Remover", classe = "btn-perigo") {
    modalConfirmar ??= new bootstrap.Modal(el("modalConfirmar"));
    el("confirmarTitulo").textContent = titulo;
    el("confirmarTexto").innerHTML = html;
    const b = el("btnConfirmar");
    b.textContent = rotulo;
    b.className = `btn ${classe}`;
    return new Promise((ok) => {
      let sim = false;
      const clique = () => { sim = true; modalConfirmar.hide(); };
      b.addEventListener("click", clique, { once: true });
      el("modalConfirmar").addEventListener("hidden.bs.modal", () => { b.removeEventListener("click", clique); ok(sim); }, { once: true });
      modalConfirmar.show();
    });
  }

  // ---------------------------------------------------------------- arquivos e área de transferência
  // No APK (pasta apk/) o WebView não baixa blobs nem tem o compartilhar da Web: usa a ponte nativa window.Android.
  const NATIVO = window.Android;
  const emBase64 = (blob) => new Promise((ok, falha) => {
    const r = new FileReader();
    r.onload = () => ok(String(r.result).split(",")[1]);
    r.onerror = () => falha(new Error("Não consegui ler o arquivo."));
    r.readAsDataURL(blob);
  });

  /** Salva o arquivo (no celular, na pasta Downloads). */
  async function baixar(blob, nome) {
    if (NATIVO) return NATIVO.salvar(nome, blob.type || "application/octet-stream", await emBase64(blob));
    const url = URL.createObjectURL(blob);
    Object.assign(document.createElement("a"), { href: url, download: nome }).click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  /** Abre o compartilhar do celular (ex.: direto pro WhatsApp). Devolve false se não deu (aí quem chamou baixa). */
  async function compartilhar(blob, nome, titulo) {
    if (NATIVO) { NATIVO.compartilhar(nome, blob.type, await emBase64(blob), titulo); return true; }
    const arquivo = new File([blob], nome, { type: blob.type });
    if (!matchMedia("(pointer: coarse)").matches || !navigator.canShare?.({ files: [arquivo] })) return false;
    try { await navigator.share({ files: [arquivo], title: titulo }); return true; } catch { return false; }
  }

  async function copiar(texto) {
    if (NATIVO) return NATIVO.copiar(texto);
    return navigator.clipboard.writeText(texto);
  }

  // Links de download do servidor (ex.: backup): no APK, busca e salva pela ponte
  if (NATIVO) {
    document.addEventListener("click", async (e) => {
      const a = e.target.closest("a[data-baixar]");
      if (!a) return;
      e.preventDefault();
      try {
        const r = await fetch(a.href);
        if (!r.ok) throw new Error(`Erro ${r.status}`);
        await baixar(await r.blob(), a.dataset.baixar);
      } catch (err) { erro(err); }
    });
  }

  // ---------------------------------------------------------------- formatação
  const pad = (n) => String(n).padStart(2, "0");
  const deISO = (iso) => { const [a, m, d] = iso.split("-").map(Number); return new Date(a, m - 1, d); };
  const dataCurta = (iso) => { const d = deISO(iso); return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}`; };
  const formatarHora = (h) => { const [hh, mm] = h.split(":"); return mm === "00" ? `${Number(hh)}h` : `${Number(hh)}h${mm}`; };
  const diaSemana = (iso) => DIAS[deISO(iso).getDay()];
  const rotuloMissa = (m) => `${diaSemana(m.data)} ${dataCurta(m.data)} · ${formatarHora(m.hora)}`;
  const normalizar = (s) => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

  /** A ausência vale enquanto a flag estiver ligada e a data "até" (se houver) não tiver passado. */
  const estaAusente = (m, iso) => !!m.ausente && (!m.ausente_ate || iso <= m.ausente_ate);

  // ---------------------------------------------------------------- HTML
  const avatar = (m, tam = 32, apagado = false) =>
    `<span class="avatar${apagado ? " apagado" : ""}" style="--tam:${tam}px;background:${esc(m.cor)}" aria-hidden="true">${esc(m.iniciais)}</span>`;
  const chipFuncao = (f) => `<span class="chip-funcao" style="--cor:${esc(f.cor)}"><span aria-hidden="true">${f.emoji}</span>${esc(f.nome)}</span>`;

  /** Botão liga/desliga (role="switch"). */
  function ligarSwitch(botao, aoMudar) {
    botao.addEventListener("click", async (e) => {
      e.stopPropagation();
      const novo = botao.getAttribute("aria-checked") !== "true";
      botao.setAttribute("aria-checked", String(novo));
      try { await aoMudar(novo); } catch (err) { botao.setAttribute("aria-checked", String(!novo)); erro(err); }
    });
  }

  window.App = {
    el, esc, api, post, put, del, toast, erro, recarregarCom, confirmar, baixar, compartilhar, copiar, NATIVO,
    DIAS, dataCurta, formatarHora, diaSemana, rotuloMissa, normalizar, estaAusente, avatar, chipFuncao, ligarSwitch,
  };
})();
