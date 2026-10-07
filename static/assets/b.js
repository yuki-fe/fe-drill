/* FE用語ドリル: 科目Bの画面（アルゴリズム図鑑・トレース練習・穴埋め・セキュリティ・記法クイズ・シミュレータ・学習状況）
 * 問題データは b-data.js（build.py が生成）の window.FE_B、実行は pseudo.js の window.Pseudo */
(function () {
  "use strict";
  const B = window.FE_B, P = window.Pseudo;
  const ROOT = document.body.dataset.root || "";
  const KANA = ["ア", "イ", "ウ", "エ"];
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const norm = (s) => String(s).normalize("NFKC").replace(/\s+/g, "").replace(/^"(.*)"$/, "$1");

  /* ---------- 学習の記録（このブラウザに保存） ---------- */
  const PKEY = "fe-b-progress";
  function loadProgress() { try { return JSON.parse(localStorage.getItem(PKEY)) || {}; } catch (e) { return {}; } }
  function record(id, ok) {
    const p = loadProgress();
    const r = p[id] || { tries: 0 };
    r.ok = ok; r.tries++; r.t = Date.now();
    p[id] = r;
    try { localStorage.setItem(PKEY, JSON.stringify(p)); } catch (e) {}
  }
  const status = (id) => { const r = loadProgress()[id]; return r ? (r.ok ? "ok" : "ng") : ""; };

  /* ---------- 共通の部品 ---------- */
  function codeList(lines, start, opts) {
    opts = opts || {};
    return `<ol class="code" start="${start}">${lines.map((l, i) => {
      const n = start + i;
      let html = esc(l);
      if (opts.blank) html = html.replace("{{a}}", `<span class="blank">${opts.blank}</span>`);
      return `<li data-ln="${n}" class="${opts.mark === n ? "mark" : ""}"><span class="ln">${n}</span><span class="tx">${html || " "}</span></li>`;
    }).join("")}</ol>`;
  }
  function termLinks(names) {
    const items = (names || []).filter((n) => B.terms[n]).map((n) => `<a class="term-chip" href="${ROOT}terms/${B.terms[n]}.html">${esc(n)}</a>`);
    return items.length ? `<p class="b-related"><span>関連する用語</span>${items.join("")}</p>` : "";
  }
  function algoLink(slug) {
    const a = slug && B.algorithms.find((x) => x.slug === slug);
    return a ? `<p class="b-related"><span>図鑑</span><a href="${ROOT}b/algorithms/${a.slug}.html">${esc(a.title)}の動きを見る</a></p>` : "";
  }
  function valueHtml(v, prev) {
    if (Array.isArray(v)) {
      return `<span class="cells">${v.map((x, i) => {
        const changed = Array.isArray(prev) && (prev.length <= i || P.format(prev[i]) !== P.format(x));
        return `<span class="cell${changed ? " changed" : ""}"><b>${esc(P.format(x))}</b><i>${i + 1}</i></span>`;
      }).join("")}</span>`;
    }
    const s = typeof v === "string" ? `"${v}"` : P.format(v);
    return `<span class="${prev !== undefined && P.format(prev) !== P.format(v) ? "changed" : ""}">${esc(s)}</span>`;
  }

  /* ---------- 動きを1行ずつ見る部品 ---------- */
  /* main（呼び出し側の処理）は画面に出さず、プログラム本体の行だけを1行ずつ見せる。
   * opts.given: 渡す値の欄を出す / opts.example: 渡す値の代わりに出す説明文 */
  function viewer(el, code, main, opts) {
    opts = opts || {};
    const res = P.run(code.join("\n") + (main.length ? "\n" + main.join("\n") : ""));
    const last = res.events[res.events.length - 1] || { vars: {}, stack: ["メイン"], fn: "メイン", depth: 0, globals: null, out: 0 };
    const inCode = (e) => !main.length || e.line <= code.length;
    const frames = res.events.filter((e) => e.phase === "line" && inCode(e)).concat([Object.assign({}, last, { line: 0, end: true, out: res.output.length })]);
    let pos = 0, timer = null;
    let given = "";
    if (opts.example) given = `<div class="given"><p class="v-label">例</p><p>${esc(opts.example)}</p></div>`;
    else if (opts.given && main.length) {
      const info = entryInfo(code, main);
      given = givenHtml(`${esc(info.fn)} に渡す値`, info.args, `<tr class="given-out"><th>結果</th><td>${esc(info.output.join("、"))}</td></tr>`);
    }
    el.innerHTML = `
      ${given}
      <div class="viewer" tabindex="-1">
        <div class="v-code">
          <p class="v-label">プログラム</p>${codeList(code, 1, { mark: opts.mark })}
        </div>
        <div class="v-side">
          <div class="v-ctrl">
            <button type="button" data-act="first">最初</button>
            <button type="button" data-act="prev">戻る</button>
            <button type="button" data-act="play" class="pri">再生</button>
            <button type="button" data-act="next">進む</button>
            <button type="button" data-act="last">最後</button>
          </div>
          <input type="range" class="v-range" min="0" max="${frames.length - 1}" value="0" aria-label="手順">
          <p class="v-pos"></p>
          <div class="v-state"></div>
        </div>
      </div>`;
    const box = $(".viewer", el), range = $(".v-range", el);
    function stop() { if (timer) { clearInterval(timer); timer = null; $("[data-act=play]", el).textContent = "再生"; } }
    function go(n) { pos = Math.max(0, Math.min(frames.length - 1, n)); render(); }
    function varsTable(vars, prevVars, title) {
      const names = Object.keys(vars);
      if (!names.length) return title ? "" : `<p class="v-empty">まだ変数はありません</p>`;
      return `${title ? `<p class="v-label">${title}</p>` : ""}<table class="v-vars">${names.map((k) =>
        `<tr><th>${esc(k)}</th><td>${valueHtml(vars[k], prevVars ? prevVars[k] : undefined)}</td></tr>`).join("")}</table>`;
    }
    function render() {
      const f = frames[pos], prev = frames[pos - 1];
      const same = prev && prev.depth === f.depth && prev.fn === f.fn;
      $$("li[data-ln]", el).forEach((li) => li.classList.toggle("cur", +li.dataset.ln === f.line));
      range.value = pos;
      $(".v-pos", el).textContent = `手順 ${pos + 1} / ${frames.length}`;
      const where = f.end ? "実行が終わりました" : `次に実行する行: ${f.line}行目`;
      const names = f.stack.filter((n) => n !== "メイン");
      const stack = names.length > 1 ? `<p class="v-stack">呼び出しの流れ: ${names.map(esc).join(" → ")}</p>` : "";
      const out = res.output.slice(0, f.out);
      const outLabel = main.length ? "結果" : "表示（print）";
      const hideVars = main.length && f.end;  // 終了後は呼び出し側の変数しか残らないので、結果だけを見せる
      $(".v-state", el).innerHTML = `
        <p class="v-where">${where}${f.end || f.fn === "メイン" ? "" : `（${esc(f.fn)}）`}</p>${stack}
        ${hideVars ? "" : `<p class="v-label">変数</p>${varsTable(f.vars, same ? prev.vars : null)}`}
        ${f.globals && !hideVars ? varsTable(f.globals, prev && prev.globals, "大域変数") : ""}
        <p class="v-label">${outLabel}</p><pre class="v-out">${out.length ? esc(out.join("\n")) : "（まだありません）"}</pre>
        ${f.end && res.error ? `<p class="v-error">${esc(res.error.message)}</p>` : ""}`;
    }
    el.addEventListener("click", (e) => {
      const b = e.target.closest("[data-act]");
      if (!b) return;
      const act = b.dataset.act;
      if (act !== "play") stop();
      if (act === "first") go(0);
      else if (act === "prev") go(pos - 1);
      else if (act === "next") go(pos + 1);
      else if (act === "last") go(frames.length - 1);
      else if (timer) stop();
      else {
        if (pos >= frames.length - 1) go(0);
        b.textContent = "停止";
        timer = setInterval(() => { if (pos >= frames.length - 1) stop(); else go(pos + 1); }, 650);
      }
    });
    range.addEventListener("input", () => { stop(); go(+range.value); });
    box.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") { e.preventDefault(); stop(); go(pos + 1); }
      if (e.key === "ArrowLeft") { e.preventDefault(); stop(); go(pos - 1); }
    });
    render();
    return res;
  }

  /* ---------- 問題で使う値（関数に渡される引数）を表示する ---------- */
  function entryInfo(code, main) {
    const res = P.run(code.join("\n") + "\n" + main.join("\n"));
    const e = res.events.find((x) => x.depth === 1 && x.phase === "line");
    return { fn: e ? e.fn : "", args: e ? e.vars : {}, output: res.output };
  }
  function givenHtml(title, args, extra) {
    const rows = Object.keys(args).map((k) => `<tr><th>${esc(k)}</th><td>${valueHtml(args[k])}</td></tr>`).join("");
    return `<div class="given"><p class="v-label">${title}</p><table class="v-vars">${rows}${extra || ""}</table></div>`;
  }

  /* ---------- 問題を切り替える共通の枠 ---------- */
  function practice(el, kind, list, renderOne) {
    let onlyWrong = false;
    let cur = list.find((x) => x.id === location.hash.slice(1)) || list[0];
    function draw() {
      const shown = onlyWrong ? list.filter((x) => status(`${kind}:${x.id}`) === "ng") : list;
      const chips = shown.map((x, i) => {
        const st = status(`${kind}:${x.id}`);
        return `<button type="button" class="pchip ${st}" data-id="${x.id}" aria-pressed="${x === cur}" title="${esc(x.title)}">${list.indexOf(x) + 1}</button>`;
      }).join("");
      const idx = list.indexOf(cur);
      el.innerHTML = `
        <div class="pbar">
          <div class="pchips">${chips || `<span class="v-empty">間違えた問題はありません</span>`}</div>
          <label class="pfilter"><input type="checkbox" id="onlyWrong-${kind}" ${onlyWrong ? "checked" : ""}> 間違えた問題だけ</label>
        </div>
        <article class="b-problem" id="prob"></article>
        <div class="pnav">
          ${idx > 0 ? `<button type="button" class="btn" data-go="${idx - 1}">前の問題</button>` : "<span></span>"}
          ${idx < list.length - 1 ? `<button type="button" class="btn primary" data-go="${idx + 1}">次の問題</button>` : "<span></span>"}
        </div>`;
      renderOne($("#prob", el), cur, () => drawChipsOnly());
      $(`#onlyWrong-${kind}`, el).onchange = (e) => { onlyWrong = e.target.checked; draw(); };
    }
    function drawChipsOnly() {
      $$(".pchip", el).forEach((b) => { b.className = `pchip ${status(`${kind}:${b.dataset.id}`)}`; });
    }
    el.addEventListener("click", (e) => {
      const c = e.target.closest(".pchip"), g = e.target.closest("[data-go]");
      if (c) { cur = list.find((x) => x.id === c.dataset.id); select(); }
      else if (g) { cur = list[+g.dataset.go]; select(); el.scrollIntoView({ block: "start" }); }
    });
    function select() { try { history.replaceState(null, "", "#" + cur.id); } catch (e) {} draw(); }
    window.addEventListener("hashchange", () => { const x = list.find((y) => y.id === location.hash.slice(1)); if (x && x !== cur) { cur = x; draw(); } });
    draw();
  }

  /* ---------- C: トレース練習 ---------- */
  function traceRows(p) {
    const res = P.run(p.code.join("\n") + "\n" + p.main.join("\n"));
    const pick = (e, v) => (v in e.vars ? e.vars[v] : e.globals && v in e.globals ? e.globals[v] : P.UNDEF);
    return res.events.filter((e) => e.phase === "after" && e.line === p.line).map((e) => p.vars.map((v) => pick(e, v)));
  }
  function renderTrace(box, p, onRecord) {
    const rows = traceRows(p);
    const id = `trace:${p.id}`;
    const info = entryInfo(p.code, p.main);
    box.innerHTML = `
      <p class="b-tags">${p.tags.map(esc).join(" / ")}</p>
      <h2>${esc(p.title)}</h2>
      <p>${esc(info.fn)} を次の値で呼び出します。<b>${p.line}行目</b>（<code>${esc(p.code[p.line - 1].trim())}</code>）を実行した直後の変数の値を、実行するたびに表に書き込んでください。</p>
      ${givenHtml(`${esc(info.fn)} に渡される値（配列の下の小さい数字は番号）`, info.args)}
      <div class="code-wrap">${codeList(p.code, 1, { mark: p.line })}</div>
      <div class="table-scroll"><table class="trace-table">
        <tr><th>回目</th>${p.vars.map((v) => `<th>${esc(v)}</th>`).join("")}</tr>
        ${rows.map((r, i) => `<tr><td>${i + 1}</td>${r.map((_, j) => `<td><input type="text" inputmode="text" autocomplete="off" data-r="${i}" data-c="${j}" aria-label="${i + 1}回目の ${esc(p.vars[j])}"></td>`).join("")}</tr>`).join("")}
      </table></div>
      <div class="cta-row">
        <button type="button" class="btn primary" data-a="check">確かめる</button>
        <button type="button" class="btn" data-a="hint">ヒント</button>
        <button type="button" class="btn" data-a="answer">答えを見る</button>
        <button type="button" class="btn again" data-a="view">▶ 動きを見る</button>
      </div>
      <p class="b-result" aria-live="polite"></p>
      <div class="b-viewer" hidden></div>
      ${termLinks(p.terms)}${algoLink(p.algo)}`;
    const result = $(".b-result", box);
    box.onclick = (e) => {
      const a = e.target.closest("[data-a]");
      if (!a) return;
      if (a.dataset.a === "check") {
        let ok = 0, filled = 0;
        $$("input[data-r]", box).forEach((inp) => {
          const want = P.format(rows[+inp.dataset.r][+inp.dataset.c]);
          const right = norm(inp.value) === norm(want);
          if (inp.value.trim()) filled++;
          if (right) ok++;
          inp.classList.toggle("ok", right);
          inp.classList.toggle("ng", !right);
        });
        const all = rows.length * p.vars.length;
        if (!filled) { result.textContent = "表に値を書き込んでから確かめてください。"; return; }
        record(id, ok === all);
        result.className = "b-result " + (ok === all ? "ok" : "ng");
        result.textContent = ok === all ? "全部正解です。「動きを見る」で、実際の動きと見比べてみましょう。" : `${all} 個中 ${ok} 個が正解です。赤い欄を見直してください。「動きを見る」で1行ずつ再生すると、どこでずれたかがわかります。`;
        onRecord();
      } else if (a.dataset.a === "hint") {
        result.className = "b-result";
        result.textContent = "ヒント: " + p.hint;
      } else if (a.dataset.a === "answer") {
        $$("input[data-r]", box).forEach((inp) => { inp.value = P.format(rows[+inp.dataset.r][+inp.dataset.c]); inp.classList.remove("ng"); inp.classList.add("ok"); });
        if (status(id) !== "ok") { record(id, false); onRecord(); }
        result.className = "b-result";
        result.textContent = "答えを表示しました。「動きを見る」で、1行ずつ確かめられます。";
      } else if (a.dataset.a === "view") {
        const v = $(".b-viewer", box);
        v.hidden = !v.hidden;
        if (!v.hidden && !v.firstChild) viewer(v, p.code, p.main, { mark: p.line });
      }
    };
  }

  /* ---------- D: 穴埋め ---------- */
  function renderFill(box, p, onRecord) {
    const id = `fill:${p.id}`;
    const sub = (k) => p.code.map((l) => l.replace("{{a}}", p.choices[k]));
    let example;
    if (p.example) example = `<div class="given"><p class="v-label">例</p><p>${esc(p.example)}</p></div>`;
    else {
      const info = entryInfo(sub(p.answer), p.tests[0].main);
      example = givenHtml(`例: ${esc(info.fn)} に次の値を渡すと`, info.args,
        `<tr class="given-out"><th>結果</th><td>${esc(info.output.join("、"))}</td></tr>`);
    }
    box.innerHTML = `
      <p class="b-tags">${p.tags.map(esc).join(" / ")}</p>
      <h2>${esc(p.title)}</h2>
      <p>${esc(p.desc)}</p>
      ${example}
      <div class="code-wrap">${codeList(p.code, 1, { blank: "a" })}</div>
      <p class="b-q">［a］に入るもの</p>
      <div class="choices">${p.choices.map((c, k) => `<button type="button" class="choice" data-k="${k}"><span class="oval">${KANA[k]}</span><code>${esc(c)}</code></button>`).join("")}</div>
      <div class="b-after" hidden></div>
      ${termLinks(p.terms)}${algoLink(p.algo)}`;
    const after = $(".b-after", box);
    $$(".choice", box).forEach((b) => b.onclick = () => {
      const k = +b.dataset.k, ok = k === p.answer;
      $$(".choice", box).forEach((x) => { x.disabled = true; if (+x.dataset.k === p.answer) x.classList.add("correct"); });
      if (!ok) b.classList.add("wrong");
      record(id, ok); onRecord();
      after.hidden = false;
      after.innerHTML = `
        <p class="b-result ${ok ? "ok" : "ng"}">${ok ? "正解です。" : `不正解です。正解は ${KANA[p.answer]} です。`}</p>
        <p class="explain">${esc(p.explain)}</p>
        <div class="cta-row">
          <button type="button" class="btn primary" data-v="${p.answer}">正しい答えで動きを見る</button>
          ${ok ? "" : `<button type="button" class="btn" data-v="${k}">選んだ答えで動かしてみる</button>`}
        </div>
        <div class="b-viewer"></div>`;
      $$("[data-v]", after).forEach((vb) => vb.onclick = () => {
        const v = $(".b-viewer", after);
        viewer(v, sub(+vb.dataset.v), p.tests[0].main);
        v.scrollIntoView({ block: "nearest" });
      });
    });
  }

  /* ---------- E: セキュリティ事例 ---------- */
  function renderSecurity(box, p, onRecord) {
    const id = `sec:${p.id}`;
    box.innerHTML = `
      <p class="b-tags">${p.tags.map(esc).join(" / ")}</p>
      <h2>${esc(p.title)}</h2>
      <div class="scenario">${esc(p.scenario)}</div>
      <p class="b-q">${esc(p.question)}</p>
      <div class="choices">${p.choices.map((c, k) => `<button type="button" class="choice" data-k="${k}"><span class="oval">${KANA[k]}</span><span>${esc(c)}</span></button>`).join("")}</div>
      <div class="b-after" hidden></div>
      ${termLinks(p.terms)}`;
    const after = $(".b-after", box);
    $$(".choice", box).forEach((b) => b.onclick = () => {
      const k = +b.dataset.k, ok = k === p.answer;
      $$(".choice", box).forEach((x) => { x.disabled = true; if (+x.dataset.k === p.answer) x.classList.add("correct"); });
      if (!ok) b.classList.add("wrong");
      record(id, ok); onRecord();
      after.hidden = false;
      after.innerHTML = `<p class="b-result ${ok ? "ok" : "ng"}">${ok ? "正解です。" : `不正解です。正解は ${KANA[p.answer]} です。`}</p><p class="explain">${esc(p.explain)}</p>`;
    });
  }

  /* ---------- A: 記法クイズ ---------- */
  function notationQuiz(el) {
    el.innerHTML = B.notation.map((q, i) => `
      <div class="nq" id="${q.id}">
        <p class="nq-h"><span class="mono">Q${i + 1}</span> ${esc(q.title)}</p>
        <pre class="code-plain">${esc(q.code.join("\n"))}</pre>
        <div class="nq-row"><label for="in-${q.id}">表示される値</label><input id="in-${q.id}" type="text" autocomplete="off"><button type="button" class="btn primary" data-q="${i}">確かめる</button></div>
        <p class="nq-res" aria-live="polite"></p>
      </div>`).join("");
    el.addEventListener("click", (e) => {
      const b = e.target.closest("[data-q]");
      if (!b) return;
      const q = B.notation[+b.dataset.q], card = b.closest(".nq");
      const inp = $("input", card), res = $(".nq-res", card);
      if (!inp.value.trim()) { inp.focus(); return; }
      const out = P.run(q.code.join("\n")).output.join("\n");
      const ok = norm(inp.value) === norm(out);
      record(`notation:${q.id}`, ok);
      res.className = "nq-res " + (ok ? "ok" : "ng");
      res.innerHTML = `<b>${ok ? "正解" : `不正解（答えは ${esc(out)}）`}</b> ${esc(q.explain)}`;
    });
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target.matches(".nq input") && !e.isComposing) $("[data-q]", e.target.closest(".nq")).click();
    });
  }

  /* ---------- H: シミュレータ ---------- */
  function simulator(el) {
    const KEY = "fe-b-simulator";
    const sample = (a) => a.code.concat([""], a.main).join("\n");
    let saved = "";
    try { saved = localStorage.getItem(KEY) || ""; } catch (e) {}
    const keys = ["←", "×", "÷", "≠", "≦", "≧", "○", "mod", "and", "or", "not"];
    el.innerHTML = `
      <div class="sim-bar">
        <label for="simSample">見本を読み込む</label>
        <select id="simSample"><option value="">選んでください</option>${B.algorithms.map((a, i) => `<option value="${i}">${esc(a.title)}</option>`).join("")}</select>
      </div>
      <div class="sim-keys" aria-label="記号を入力">${keys.map((k) => `<button type="button" data-k="${esc(k)}">${esc(k)}</button>`).join("")}</div>
      <textarea id="simCode" spellcheck="false" autocapitalize="off" aria-label="擬似言語のプログラム"></textarea>
      <div class="cta-row">
        <button type="button" class="btn primary" id="simRun">実行する</button>
        <button type="button" class="btn" id="simReset">見本に戻す</button>
      </div>
      <p class="b-result" id="simMsg" aria-live="polite"></p>
      <div id="simOut"></div>`;
    const ta = $("#simCode", el);
    ta.value = saved || sample(B.algorithms[0]);
    const save = () => { try { localStorage.setItem(KEY, ta.value); } catch (e) {} };
    function insert(text) {
      const s = ta.selectionStart, e = ta.selectionEnd;
      ta.value = ta.value.slice(0, s) + text + ta.value.slice(e);
      ta.selectionStart = ta.selectionEnd = s + text.length;
      ta.focus(); save();
    }
    $(".sim-keys", el).onclick = (e) => { const b = e.target.closest("[data-k]"); if (b) insert(/^[a-z]+$/.test(b.dataset.k) ? ` ${b.dataset.k} ` : b.dataset.k); };
    ta.addEventListener("keydown", (e) => { if (e.key === "Tab" && !e.shiftKey) { e.preventDefault(); insert("  "); } });
    ta.addEventListener("input", save);
    $("#simSample", el).onchange = (e) => { if (e.target.value !== "") { ta.value = sample(B.algorithms[+e.target.value]); save(); run(); } };
    $("#simReset", el).onclick = () => { ta.value = sample(B.algorithms[0]); $("#simSample", el).value = ""; save(); run(); };
    function run() {
      const lines = ta.value.replace(/\r\n?/g, "\n").split("\n");
      const res = viewer($("#simOut", el), lines, []);
      const msg = $("#simMsg", el);
      msg.className = "b-result " + (res.error ? "ng" : "ok");
      msg.textContent = res.error ? `エラー: ${res.error.message}` : `実行できました（${res.events.filter((x) => x.phase === "line").length} 手順）。下の「再生」や「進む」で動きを確かめられます。`;
    }
    $("#simRun", el).onclick = run;
    run();
  }

  /* ---------- F: 学習状況 ---------- */
  function dashboard(el) {
    const items = [].concat(
      B.notation.map((x) => ({ id: `notation:${x.id}`, title: x.title, tags: x.tags, href: `notation.html#${x.id}`, kind: "記法クイズ" })),
      B.trace.map((x) => ({ id: `trace:${x.id}`, title: x.title, tags: x.tags, href: `trace.html#${x.id}`, kind: "トレース" })),
      B.fill.map((x) => ({ id: `fill:${x.id}`, title: x.title, tags: x.tags, href: `fill.html#${x.id}`, kind: "穴埋め" })),
      B.security.map((x) => ({ id: `sec:${x.id}`, title: x.title, tags: ["セキュリティ"], href: `security.html#${x.id}`, kind: "セキュリティ" })));
    const p = loadProgress();
    const tags = {};
    items.forEach((it) => it.tags.forEach((t) => {
      const g = tags[t] || (tags[t] = { total: 0, done: 0, ok: 0 });
      g.total++;
      if (p[it.id]) { g.done++; if (p[it.id].ok) g.ok++; }
    }));
    const done = items.filter((it) => p[it.id]).length, ok = items.filter((it) => p[it.id] && p[it.id].ok).length;
    const wrong = items.filter((it) => p[it.id] && !p[it.id].ok);
    const rows = Object.entries(tags).sort((a, b) => b[1].total - a[1].total).map(([t, g]) => {
      const rate = g.done ? Math.round((g.ok / g.done) * 100) : null;
      return `<tr><th>${esc(t)}</th><td class="mono">${g.done}/${g.total}</td><td><span class="bar"><i style="width:${rate || 0}%"></i></span></td><td class="mono">${rate === null ? "—" : rate + "%"}</td></tr>`;
    }).join("");
    el.innerHTML = `
      <div class="dash-sum">
        <div><b class="mono">${done}<small>/${items.length}</small></b><span>解いた問題</span></div>
        <div><b class="mono">${done ? Math.round((ok / done) * 100) : 0}<small>%</small></b><span>正答率</span></div>
        <div><b class="mono">${wrong.length}</b><span>復習する問題</span></div>
      </div>
      <h3>テーマ別の正答率</h3>
      <div class="table-scroll"><table class="dash-table"><tr><th>テーマ</th><th>解いた数</th><th>正答率</th><th></th></tr>${rows}</table></div>
      <h3>復習する問題</h3>
      ${wrong.length ? `<ul class="dash-wrong">${wrong.map((it) => `<li><span class="b-tags">${it.kind}</span> <a href="${it.href}">${esc(it.title)}</a></li>`).join("")}</ul>`
        : `<p class="v-empty">間違えた問題はまだありません。最後に間違えた問題がここに集まり、正解すると消えます。</p>`}
      <p class="save-note">記録はこのブラウザに保存されます。<button type="button" id="dashReset">科目Bの記録をリセット</button></p>`;
    let armed = false;
    $("#dashReset", el).onclick = (e) => {
      if (!armed) { armed = true; e.target.textContent = "もう一度押すとリセットします"; setTimeout(() => { armed = false; e.target.textContent = "科目Bの記録をリセット"; }, 3000); return; }
      try { localStorage.removeItem(PKEY); } catch (x) {}
      dashboard(el);
    };
  }

  /* ---------- 起動 ---------- */
  $$("[data-b]").forEach((el) => {
    const k = el.dataset.b;
    if (k === "viewer") {
      const a = B.algorithms.find((x) => x.slug === el.dataset.algo);
      if (a) viewer(el, a.code, a.main, { given: true, example: a.example });
    } else if (k === "trace-demo") {
      const p = B.trace.find((x) => x.id === el.dataset.id);
      if (p) viewer(el, p.code, p.main, { given: true, mark: p.line });
    } else if (k === "trace") practice(el, "trace", B.trace, renderTrace);
    else if (k === "fill") practice(el, "fill", B.fill, renderFill);
    else if (k === "security") practice(el, "sec", B.security, renderSecurity);
    else if (k === "notation") notationQuiz(el);
    else if (k === "simulator") simulator(el);
    else if (k === "dashboard") dashboard(el);
  });
})();
