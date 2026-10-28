// Painel: botão "Voltou" dos ausentes e "Ver todos" do ranking do mês.
(function () {
  "use strict";
  const { post, recarregarCom, erro } = window.App;

  document.querySelectorAll("[data-voltou]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      try {
        await post(`/api/membros/${b.dataset.voltou}/ausencia`, { ausente: false });
        recarregarCom(`${b.dataset.nome} voltou! 🎉`);
      } catch (e) {
        b.disabled = false;
        erro(e);
      }
    }));

  const btn = document.getElementById("btnRanking");
  btn?.addEventListener("click", () => {
    const aberto = document.getElementById("ranking").classList.toggle("ranking-aberto");
    btn.textContent = aberto ? "Mostrar menos" : `Ver todos (${btn.dataset.total})`;
  });
})();
