// Editor das vagas de uma missa ou missa fixa: cada vaga é uma combinação de funções ("Vela / Patena / Lavabo").
// Usado na Escala (editar missa) e em Funções & Missas (missas fixas).
(function () {
  "use strict";
  const { esc } = window.App;

  window.EditorVagas = function (container, funcoes) {
    let vagas = [];        // [{ id?, funcoes: [] }]

    function render() {
      container.innerHTML = vagas.map((v, i) => `
        <div class="editor-vaga" data-i="${i}">
          <span class="num">${i + 1}</span>
          <div class="chips">${funcoes.map((f) => `
            <button type="button" class="chip-toggle" style="--cor:${esc(f.cor)}" data-funcao="${esc(f.id)}"
              aria-pressed="${v.funcoes.includes(f.id)}"><span aria-hidden="true">${f.emoji}</span> ${esc(f.nome)}</button>`).join("")}
          </div>
          <div class="acoes">
            <button type="button" class="btn-icone" data-mover="-1" ${i === 0 ? "disabled" : ""} aria-label="Subir"><i class="bi bi-arrow-up"></i></button>
            <button type="button" class="btn-icone" data-mover="1" ${i === vagas.length - 1 ? "disabled" : ""} aria-label="Descer"><i class="bi bi-arrow-down"></i></button>
            <button type="button" class="btn-icone perigo" data-remover aria-label="Remover vaga"><i class="bi bi-trash3"></i></button>
          </div>
        </div>`).join("") +
        `<button type="button" class="btn btn-suave btn-sm" data-adicionar><i class="bi bi-plus-lg"></i> Adicionar vaga</button>`;
    }

    container.addEventListener("click", (e) => {
      if (e.target.closest("[data-adicionar]")) {
        vagas.push({ funcoes: [] });
        return render();
      }
      const linha = e.target.closest(".editor-vaga");
      if (!linha) return;
      const i = Number(linha.dataset.i);
      const chip = e.target.closest("[data-funcao]");
      const mover = e.target.closest("[data-mover]");
      if (chip) {
        const f = chip.dataset.funcao;
        const fs = vagas[i].funcoes;
        vagas[i].funcoes = fs.includes(f) ? fs.filter((x) => x !== f) : [...fs, f];
        chip.setAttribute("aria-pressed", String(vagas[i].funcoes.includes(f)));
      } else if (mover) {
        const j = i + Number(mover.dataset.mover);
        [vagas[i], vagas[j]] = [vagas[j], vagas[i]];
        render();
      } else if (e.target.closest("[data-remover]")) {
        vagas.splice(i, 1);
        render();
      }
    });

    return {
      definir(lista) {
        vagas = lista.map((v) => ({ ...v, funcoes: [...v.funcoes] }));
        render();
      },
      obter: () => vagas.map((v) => ({ ...v })),
    };
  };
})();
