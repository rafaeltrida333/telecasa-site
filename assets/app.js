(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const norm = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

  // Menu no celular
  const mb = $(".menu"), nav = $("#nav");
  if (mb) mb.addEventListener("click", () => { const o = nav.classList.toggle("open"); mb.setAttribute("aria-expanded", o) });

  // Filtros da lista de imóveis (os cartões já vêm no HTML; aqui só escondemos os que não batem)
  const f = $("#filtros");
  if (f) {
    const cards = [...document.querySelectorAll("#lista .card")];
    const qs = new URLSearchParams(location.search);
    // Páginas como /imoveis/a-venda/casa/ já vêm com filtros definidos
    let pre = {}; try { pre = JSON.parse(f.dataset.preset || "{}") } catch (e) {}
    for (const k in pre) if (!qs.has(k)) qs.set(k, pre[k]);
    for (const k of ["tipo", "q", "quartos", "max"]) if (qs.get(k) && f.elements[k]) f.elements[k].value = qs.get(k);
    const p = qs.get("p") || "";
    for (const r of f.querySelectorAll("[name=p]")) r.checked = r.value === p;
    const apply = () => {
      const fp = (f.querySelector("[name=p]:checked") || {}).value || "";
      const tipo = f.elements.tipo.value, q = norm(f.elements.q.value), qt = +f.elements.quartos.value || 0;
      const max = +String(f.elements.max.value).replace(/\D/g, "") || 0;
      let n = 0;
      for (const c of cards) {
        const d = c.dataset, valor = fp === "aluguel" ? +d.aluguel : +d.valor || +d.aluguel;
        const ok = (!fp || d.p.split(" ").includes(fp)) && (!tipo || d.tipo === tipo) && (!q || d.q.includes(q)) && (+d.quartos >= qt) && (!max || !valor || valor <= max);
        c.hidden = !ok; if (ok) n++;
      }
      $("#count").textContent = n + (n === 1 ? " imóvel" : " imóveis");
      $("#vazio").hidden = n > 0;
      const u = new URLSearchParams();
      if (fp) u.set("p", fp); if (tipo) u.set("tipo", tipo); if (f.elements.q.value) u.set("q", f.elements.q.value); if (qt) u.set("quartos", qt); if (max) u.set("max", max);
      history.replaceState(null, "", location.pathname + (u.toString() ? "?" + u : ""));
    };
    f.addEventListener("input", apply); f.addEventListener("change", apply); apply();
  }

  // Busca por código
  for (const b of document.querySelectorAll("[data-cod]")) b.addEventListener("click", () => {
    const c = prompt("Digite o código do imóvel");
    if (c && c.trim()) location.href = b.closest("form").action + "?q=" + encodeURIComponent(c.trim());
  });

  // Bairros mais populares: 16 por página, com Anterior e Próximo
  const bl = [...document.querySelectorAll("#bairros [data-pg]")];
  if (bl.length) {
    const last = Math.max(...bl.map(a => +a.dataset.pg)); let pg = 0;
    const btn = [...document.querySelectorAll("[data-car]")];
    const show = () => { bl.forEach(a => a.hidden = +a.dataset.pg !== pg); btn.forEach(b => b.disabled = (+b.dataset.car < 0 ? pg === 0 : pg === last)) };
    btn.forEach(b => b.addEventListener("click", () => { pg = Math.min(last, Math.max(0, pg + +b.dataset.car)); show() }));
    show();
  }

  // Fecha os menus suspensos ao clicar fora
  document.addEventListener("click", e => { for (const d of document.querySelectorAll("details.dd[open]")) if (!d.contains(e.target)) d.open = false });

  // Galeria da página do imóvel
  const g = $(".gal");
  if (g) {
    const fotos = JSON.parse($("#gdata").textContent), img = $("#gmain"), gc = $("#gc"), th = [...g.querySelectorAll(".th")];
    let i = 0;
    const show = k => {
      i = (k + fotos.length) % fotos.length; img.src = fotos[i]; img.parentNode.classList.toggle("wm", /^https:/.test(fotos[i]));
      img.alt = img.alt.replace(/foto \d+ de/, "foto " + (i + 1) + " de"); gc.textContent = (i + 1) + " / " + fotos.length;
      th.forEach((t, j) => t.setAttribute("aria-current", j === i));
    };
    g.addEventListener("click", e => {
      if (e.target.closest(".prev")) show(i - 1); else if (e.target.closest(".next")) show(i + 1);
      else { const t = e.target.closest(".th"); if (t) show(+t.dataset.i) }
    });
    document.addEventListener("keydown", e => { if (e.key === "ArrowLeft") show(i - 1); if (e.key === "ArrowRight") show(i + 1) });
    let x0 = null; img.addEventListener("touchstart", e => x0 = e.touches[0].clientX, { passive: true });
    img.addEventListener("touchend", e => { if (x0 === null) return; const dx = e.changedTouches[0].clientX - x0; if (Math.abs(dx) > 40) show(i + (dx < 0 ? 1 : -1)); x0 = null });
    if (th.length) th[0].setAttribute("aria-current", "true");
  }

  // Formulários que abrem o WhatsApp com a mensagem pronta
  for (const w of document.querySelectorAll(".wform")) {
    w.addEventListener("submit", e => {
      e.preventDefault();
      const lines = [w.dataset.assunto + " (site)"];
      for (const el of w.elements) if (el.name && el.value.trim()) lines.push(el.name + ": " + el.value.trim());
      window.open("https://wa.me/" + w.dataset.wa + "?text=" + encodeURIComponent(lines.join("\n")), "_blank", "noopener");
    });
  }
})();
