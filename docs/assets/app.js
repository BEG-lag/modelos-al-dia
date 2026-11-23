// Filtros y orden para las tablas. La página funciona completa sin este archivo.
(() => {
  "use strict";

  const normaliza = (s) =>
    (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

  // Catálogo: búsqueda, proveedor, tipo y obsoletos.
  const formCat = document.querySelector('form[data-table="catalogo"]');
  const tabla = document.getElementById("catalogo");
  if (formCat && tabla) {
    const filas = [...tabla.tBodies[0].rows];
    const aplicar = () => {
      const q = normaliza(formCat.q.value);
      const prov = formCat.prov.value;
      const tipo = formCat.tipo.value;
      const obs = formCat.obsoletos.checked;
      let n = 0;
      for (const fila of filas) {
        const ok =
          (!prov || fila.dataset.prov === prov) &&
          (!tipo || fila.dataset.tipo === tipo) &&
          (obs || fila.dataset.estado === "vigente") &&
          (!q || normaliza(fila.textContent).includes(q));
        fila.hidden = !ok;
        if (ok) n++;
      }
      formCat.cuenta.value = `${n} modelos`;
    };
    formCat.addEventListener("input", aplicar);
    aplicar();

    // Orden por columna (las que tienen data-sort).
    tabla.tHead.querySelectorAll("th[data-sort]").forEach((th) => {
      th.tabIndex = 0;
      const ordena = () => {
        const i = th.cellIndex;
        const asc = th.getAttribute("aria-sort") !== "ascending";
        tabla.tHead.querySelectorAll("th").forEach((x) => x.removeAttribute("aria-sort"));
        th.setAttribute("aria-sort", asc ? "ascending" : "descending");
        const valor = (fila) => {
          const v = fila.cells[i].dataset.v || "";
          const num = Number(v);
          return v !== "" && !Number.isNaN(num) ? num : v;
        };
        filas.sort((a, b) => {
          const x = valor(a);
          const y = valor(b);
          const r = x < y ? -1 : x > y ? 1 : 0;
          return asc ? r : -r;
        });
        tabla.tBodies[0].append(...filas);
      };
      th.addEventListener("click", ordena);
      th.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          ordena();
        }
      });
    });
  }

  // Novedades: proveedor y origen.
  const formNov = document.querySelector('form[data-list="novedades"]');
  const lista = document.getElementById("novedades");
  if (formNov && lista) {
    const items = [...lista.children];
    const aplicar = () => {
      const prov = formNov.prov.value;
      const origen = formNov.origen.value;
      let n = 0;
      for (const li of items) {
        const ok = (!prov || li.dataset.prov === prov) && (!origen || li.dataset.origen === origen);
        li.hidden = !ok;
        if (ok) n++;
      }
      formNov.cuenta.value = `${n} notas`;
    };
    formNov.addEventListener("input", aplicar);
    aplicar();
  }
})();
