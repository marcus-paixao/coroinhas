// Ajustes: importar planilha, restaurar backup, quem entra nos alertas e recomeçar do zero.
(function () {
  "use strict";

  const A = window.App;
  const { el } = A;

  document.querySelectorAll("[data-arquivo]").forEach((b) => b.addEventListener("click", () => el(b.dataset.arquivo).click()));

  async function enviar(input, url) {
    const arq = input.files[0];
    input.value = "";
    if (!arq) return null;
    const dados = new FormData();
    dados.append("arquivo", arq);
    return A.api(url, { method: "POST", body: dados });
  }

  el("inputPlanilha").addEventListener("change", async (e) => {
    try {
      A.toast("Lendo a planilha…");
      const r = await enviar(e.target, "/api/planilha");
      if (r) A.recarregarCom(`Planilha importada: ${r.novos} novo(s), ${r.atualizados} atualizado(s) ✅`);
    } catch (err) { A.erro(err); }
  });

  el("inputBackup").addEventListener("change", async (e) => {
    const input = e.target;
    if (!input.files[0]) return;
    const ok = await A.confirmar("Restaurar este backup?",
      `O arquivo <strong>${A.esc(input.files[0].name)}</strong> vai substituir <strong>tudo</strong> o que está salvo agora (para todo mundo).`,
      "Restaurar", "btn-azul");
    if (!ok) { input.value = ""; return; }
    try {
      const r = await enviar(input, "/api/backup");
      A.recarregarCom(`Backup restaurado: ${r.membros} pessoas, ${r.missas} missas ✅`);
    } catch (err) { A.erro(err); }
  });

  document.querySelectorAll("[data-tipo]").forEach((c) => c.addEventListener("change", async () => {
    const tipos = [...document.querySelectorAll("[data-tipo]:checked")].map((x) => x.dataset.tipo);
    try {
      await A.post("/api/config", { tipos_escalaveis: tipos });
      A.toast("Alertas atualizados");
    } catch (err) { c.checked = !c.checked; A.erro(err); }
  }));

  el("btnApagar").addEventListener("click", async () => {
    const ok = await A.confirmar("Apagar tudo?",
      "Todos os cadastros e escalas serão apagados, para todo mundo. Funções e missas fixas voltam ao padrão.", "Apagar tudo");
    if (!ok) return;
    try {
      await A.post("/api/apagar-tudo", {});
      A.recarregarCom("Tudo zerado. Começando de novo! 🌱");
    } catch (err) { A.erro(err); }
  });
})();
