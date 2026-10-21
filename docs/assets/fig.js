/* 用語の動く図（make_figs.py の SVG）を、利用者が「前へ」「次へ」で切り替える。
   .fig-player の中の svg.fig-svg に、ボタン・番号・いまのステップの文を付ける。
   図をタップすると次へ、左右になぞると前後に進む。矢印キーでも動かせる。 */
window.FigPlayer = (function () {
  function setup(box) {
    const svg = box.querySelector("svg.fig-svg");
    if (!svg || box.dataset.ready) return;
    box.dataset.ready = "1";
    let steps = [];
    try { steps = JSON.parse(svg.getAttribute("data-steps") || "[]"); } catch (e) {}
    const n = steps.length;
    if (!n) return;
    const list = box.parentElement && box.parentElement.querySelectorAll(".fig-steps li");
    const ctrl = document.createElement("div");
    ctrl.className = "fig-ctrl";
    let dots = "";
    for (let k = 0; k < n; k++) dots += '<button type="button" class="fig-dot" aria-label="ステップ' + (k + 1) + '"></button>';
    ctrl.innerHTML = '<button type="button" class="fig-btn fig-prev" aria-label="前のステップ">‹</button>'
      + '<span class="fig-dots">' + dots + '</span>'
      + '<span class="fig-count mono" aria-live="polite"></span>'
      + '<button type="button" class="fig-btn fig-next" aria-label="次のステップ">›</button>';
    const cap = document.createElement("p");
    cap.className = "fig-cap";
    box.appendChild(cap);
    box.appendChild(ctrl);
    const prev = ctrl.querySelector(".fig-prev"), next = ctrl.querySelector(".fig-next"), count = ctrl.querySelector(".fig-count");
    const dotEls = ctrl.querySelectorAll(".fig-dot");
    let i = 0;
    function go(k) {
      i = Math.max(0, Math.min(n - 1, k));
      svg.setAttribute("data-step", i);
      cap.textContent = steps[i];
      count.textContent = (i + 1) + " / " + n;
      prev.disabled = i === 0;
      next.textContent = i === n - 1 ? "↺" : "›";
      next.setAttribute("aria-label", i === n - 1 ? "最初から" : "次のステップ");
      dotEls.forEach((el, k) => el.classList.toggle("now", k === i));
      if (list) list.forEach((li, k) => li.classList.toggle("now", k === i));
    }
    const forward = () => go(i === n - 1 ? 0 : i + 1);
    prev.onclick = () => go(i - 1);
    next.onclick = forward;
    if (list) list.forEach((li, k) => { li.onclick = () => go(k); });
    dotEls.forEach((el, k) => { el.onclick = () => go(k); });
    // 図のタップで次へ・左右のスワイプで前後へ
    let sx = null, sy = 0;
    svg.addEventListener("pointerdown", (e) => { sx = e.clientX; sy = e.clientY; });
    svg.addEventListener("pointerup", (e) => {
      if (sx === null) return;
      const dx = e.clientX - sx, dy = e.clientY - sy;
      sx = null;
      if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) go(dx < 0 ? i + 1 : i - 1);
      else if (Math.abs(dx) < 10 && Math.abs(dy) < 10) forward();
    });
    svg.style.cursor = "pointer";
    svg.style.touchAction = "pan-y";
    box.tabIndex = 0;
    box.addEventListener("keydown", (e) => {
      // 図を操作しているときの ← → は、カードの「まだ」「覚えた」などに伝えない
      if (e.key === "ArrowRight") { go(i + 1); e.preventDefault(); e.stopPropagation(); }
      if (e.key === "ArrowLeft") { go(i - 1); e.preventDefault(); e.stopPropagation(); }
    });
    go(0);
  }
  /* figs/<id>.svg を読み込んで box の中に入れる（クイズの「図で見る」用） */
  function load(box, url) {
    if (box.dataset.loaded) return;
    box.dataset.loaded = "1";
    fetch(url).then((r) => { if (!r.ok) throw 0; return r.text(); })
      .then((t) => { box.innerHTML = t; setup(box); })
      .catch(() => { box.innerHTML = '<img src="' + url + '" alt="" width="640" height="350">'; });
  }
  document.querySelectorAll(".fig-player").forEach(setup);
  return { setup: setup, load: load };
})();
