// Liturgia: atualizar leituras da API da CNBB ou editar manualmente celebração, cor e referências.
(function () {
  "use strict";

  const A = window.App;
  const { el } = A;
  const DIAS = new Map((window.LITURGIAS || []).map((d) => [d.data, d]));
  const modal = new bootstrap.Modal(el("modalLiturgia"));
  const form = el("formLiturgia");
  let dataEditando = null;

  function acharLeitura(d, prefixo) {
    return (d.leituras || []).find((l) => l.tipo.toLowerCase().startsWith(prefixo)) || {};
  }

  function abrirEditor(dataIso) {
    const d = DIAS.get(dataIso);
    if (!d) return;
    dataEditando = dataIso;
    form.reset();
    el("liturgiaErro").textContent = "";
    el("liturgiaModalTitulo").textContent = `Liturgia · ${d.dia_nome} (${d.data_curta})`;
    form.titulo.value = d.titulo || "";
    form.cor.value = d.cor || "Verde";
    const l1 = acharLeitura(d, "1ª");
    const sl = acharLeitura(d, "salmo");
    const l2 = acharLeitura(d, "2ª");
    const ev = acharLeitura(d, "evangelho");
    form.ref_1.value = l1.referencia || "";
    form.ref_salmo.value = sl.referencia || "";
    form.refrao_salmo.value = sl.refrao || "";
    form.ref_2.value = l2.referencia || "";
    form.ref_evangelho.value = ev.referencia || "";
    modal.show();
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!dataEditando) return;
    const atual = DIAS.get(dataEditando) || {};
    const l1 = acharLeitura(atual, "1ª");
    const sl = acharLeitura(atual, "salmo");
    const l2 = acharLeitura(atual, "2ª");
    const ev = acharLeitura(atual, "evangelho");

    const leituras = [];
    if (form.ref_1.value.trim()) {
      leituras.push({ ...l1, tipo: "1ª Leitura", referencia: form.ref_1.value.trim() });
    }
    if (form.ref_salmo.value.trim()) {
      leituras.push({ ...sl, tipo: "Salmo", referencia: form.ref_salmo.value.trim(), refrao: form.refrao_salmo.value.trim() });
    }
    if (form.ref_2.value.trim()) {
      leituras.push({ ...l2, tipo: "2ª Leitura", referencia: form.ref_2.value.trim() });
    }
    if (form.ref_evangelho.value.trim()) {
      leituras.push({ ...ev, tipo: "Evangelho", referencia: form.ref_evangelho.value.trim() });
    }

    try {
      await A.put(`/api/liturgia/${dataEditando}`, {
        titulo: form.titulo.value.trim(),
        cor: form.cor.value,
        leituras,
      });
      modal.hide();
      A.recarregarCom("Liturgia atualizada ✨");
    } catch (err) {
      el("liturgiaErro").textContent = err.message;
    }
  });

  document.addEventListener("click", async (e) => {
    const btnEd = e.target.closest("[data-editar]");
    if (btnEd) return abrirEditor(btnEd.dataset.editar);

    const btnAt = e.target.closest("[data-atualizar]");
    if (btnAt) {
      const dt = btnAt.dataset.atualizar;
      btnAt.disabled = true;
      try {
        A.toast("Consultando liturgia da CNBB…");
        const r = await A.post(`/api/liturgia/${dt}/atualizar`, {});
        if (r.liturgia?.leituras?.length) {
          A.recarregarCom("Leituras atualizadas ✅");
        } else {
          A.toast("A CNBB ainda não publicou as leituras desta data (você pode preencher no lápis).", "erro");
          btnAt.disabled = false;
        }
      } catch (err) {
        btnAt.disabled = false;
        A.erro(err);
      }
    }
  });
})();
