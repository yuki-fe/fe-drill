/* FE用語ドリル: IPA 擬似言語のインタプリタ（科目B用）
 * Pseudo.run(ソース) で実行し、1行ごとの変数の状態（events）と出力を返す。
 * このサイト独自の約束: 整数どうしの ÷ は商（小数点以下切り捨て）、print(...) で値を表示する。 */
(function (root) {
  "use strict";
  const TYPE_RE = "(?:整数型|実数型|文字型|文字列型|論理型)(?:の配列|の二次元配列|配列の配列)?";
  const UNDEF = Object.freeze({ undef: true });
  const MAX_DEPTH = 200;

  class PseudoError extends Error {
    constructor(msg, line) { super(line ? `${line}行目: ${msg}` : msg); this.line = line || 0; this.plain = msg; }
  }
  class Return { constructor(value) { this.value = value; } }

  /* ---------- 式の字句解析 ---------- */
  const OPS = [["←", "←"], ["≠", "≠"], ["≦", "≦"], ["≧", "≧"], ["<=", "≦"], [">=", "≧"], ["!=", "≠"], ["<>", "≠"],
    ["×", "×"], ["÷", "÷"], ["*", "×"], ["/", "÷"], ["+", "+"], ["-", "-"], ["=", "="], ["<", "<"], [">", ">"],
    ["(", "("], [")", ")"], ["[", "["], ["]", "]"], ["{", "{"], ["}", "}"], [",", ","]];
  const KW = ["未定義の値", "未定義", "の要素数", "個の"];

  function tokenize(src, line) {
    const out = [];
    let i = 0;
    while (i < src.length) {
      const c = src[i];
      if (c === " " || c === "\t") { i++; continue; }
      const rest = src.slice(i);
      let m = /^\d+(?:\.\d+)?/.exec(rest);
      if (m) { out.push({ t: "num", v: Number(m[0]) }); i += m[0].length; continue; }
      if (c === '"' || c === "'") {
        const j = src.indexOf(c, i + 1);
        if (j < 0) throw new PseudoError(`文字列の ${c} が閉じていません`, line);
        out.push({ t: "str", v: src.slice(i + 1, j) });
        i = j + 1;
        continue;
      }
      const kw = KW.find((k) => rest.startsWith(k));
      if (kw) { out.push({ t: "kw", v: kw }); i += kw.length; continue; }
      const op = OPS.find(([s]) => rest.startsWith(s));
      if (op) { out.push({ t: "op", v: op[1] }); i += op[0].length; continue; }
      m = /^[A-Za-z_][A-Za-z0-9_]*/.exec(rest);
      if (m) {
        const w = m[0];
        if (w === "and" || w === "or" || w === "not" || w === "mod") out.push({ t: "op", v: w });
        else if (w === "true" || w === "false") out.push({ t: "bool", v: w === "true" });
        else out.push({ t: "id", v: w });
        i += w.length;
        continue;
      }
      throw new PseudoError(`「${c}」を読み取れません`, line);
    }
    return out;
  }

  /* ---------- 式の構文解析（優先順位: 単項 > 乗除 > 加減 > 比較 > and > or） ---------- */
  const BIN = { or: 1, and: 2, "=": 3, "≠": 3, "<": 3, ">": 3, "≦": 3, "≧": 3, "+": 4, "-": 4, "×": 5, "÷": 5, mod: 5 };

  function parseExpr(src, line) {
    const toks = tokenize(src, line);
    let p = 0;
    const isOp = (v) => toks[p] && toks[p].t === "op" && toks[p].v === v;
    const isKw = (v) => toks[p] && toks[p].t === "kw" && toks[p].v === v;
    const expect = (v) => { if (!isOp(v)) throw new PseudoError(`「${v}」が足りません`, line); p++; };

    function binary(minPrec) {
      let left = unary();
      for (;;) {
        const t = toks[p];
        if (!t || t.t !== "op" || !(t.v in BIN) || BIN[t.v] < minPrec) return left;
        p++;
        left = { k: "bin", op: t.v, l: left, r: binary(BIN[t.v] + 1) };
      }
    }
    function unary() {
      if (isOp("not") || isOp("-") || isOp("+")) { const op = toks[p++].v; return { k: "un", op, e: unary() }; }
      return postfix(primary());
    }
    function list(close) {
      const items = [];
      if (!isOp(close)) { items.push(binary(1)); while (isOp(",")) { p++; items.push(binary(1)); } }
      expect(close);
      return items;
    }
    function primary() {
      const t = toks[p];
      if (!t) throw new PseudoError("式が途中で終わっています", line);
      p++;
      if (t.t === "num" || t.t === "str" || t.t === "bool") return { k: "lit", v: t.v };
      if (t.t === "kw" && (t.v === "未定義" || t.v === "未定義の値")) return { k: "lit", v: UNDEF };
      if (t.t === "op" && t.v === "(") { const e = binary(1); expect(")"); return e; }
      if (t.t === "op" && t.v === "{") {
        if (isOp("}")) { p++; return { k: "arr", items: [] }; }
        const first = binary(1);
        if (isKw("個の")) { p++; const v = binary(1); expect("}"); return { k: "fill", n: first, v }; }
        const items = [first];
        while (isOp(",")) { p++; items.push(binary(1)); }
        expect("}");
        return { k: "arr", items };
      }
      if (t.t === "id") {
        if (isOp("(")) { p++; return { k: "call", name: t.v, args: list(")") }; }
        return { k: "var", name: t.v };
      }
      throw new PseudoError(`「${t.v}」の位置がおかしいです`, line);
    }
    function postfix(e) {
      for (;;) {
        if (isOp("[")) { p++; e = { k: "idx", obj: e, idx: list("]") }; }
        else if (isKw("の要素数")) { p++; e = { k: "len", obj: e }; }
        else return e;
      }
    }
    const e = binary(1);
    if (p < toks.length) throw new PseudoError(`「${toks[p].v}」の位置がおかしいです`, line);
    return e;
  }

  /* カンマで区切る（括弧と文字列の中は区切らない） */
  function splitTop(s) {
    const out = [];
    let depth = 0, cur = "", q = "";
    for (const ch of s) {
      if (q) { cur += ch; if (ch === q) q = ""; continue; }
      if (ch === '"' || ch === "'") { q = ch; cur += ch; continue; }
      if ("([{".includes(ch)) depth++;
      if (")]}".includes(ch)) depth--;
      if (ch === "," && depth === 0) { out.push(cur.trim()); cur = ""; continue; }
      cur += ch;
    }
    if (cur.trim()) out.push(cur.trim());
    return out;
  }
  function indexOfTop(s, target) {
    let q = "";
    for (let i = 0; i < s.length; i++) {
      const ch = s[i];
      if (q) { if (ch === q) q = ""; continue; }
      if (ch === '"' || ch === "'") { q = ch; continue; }
      if (ch === target) return i;
    }
    return -1;
  }

  /* ---------- 文の構文解析 ---------- */
  const RE = {
    head: new RegExp(`^○\\s*(?:(${TYPE_RE})\\s*:\\s*)?([A-Za-z_]\\w*)\\s*\\((.*)\\)$`),
    param: new RegExp(`^(${TYPE_RE})\\s*:\\s*([A-Za-z_]\\w*)$`),
    decl: new RegExp(`^(大域\\s*:\\s*)?(${TYPE_RE})\\s*:\\s*(.+)$`),
    forCtl: /^([A-Za-z_]\w*)\s*を\s*(.+?)\s*から\s*(.+?)\s*まで\s*(.+?)\s*ずつ\s*(増やす|減らす)$/,
    append: /^(.+?)\s*の末尾に\s*(.+?)\s*(?:の値)?\s*を追加する$/,
  };

  function parseBlock(ls, start, terms, doIndent) {
    const stmts = [];
    let i = start;
    while (i < ls.length) {
      const L = ls[i], t = L.text;
      const head = t.split(/[\s(]/)[0];
      if (terms.includes(head) && !(head === "while" && L.indent > doIndent)) return { stmts, next: i, end: L };
      let m;
      if ((m = /^if\s*\((.*)\)$/.exec(t))) {
        const branches = [];
        let cond = parseExpr(m[1], L.no), condLine = L.no, elseBody = null, elseLine = 0, endLine = 0;
        i++;
        for (;;) {
          const r = parseBlock(ls, i, ["elseif", "else", "endif"], doIndent);
          if (!r.end) throw new PseudoError("if に対応する endif がありません", L.no);
          if (cond) branches.push({ cond, line: condLine, body: r.stmts }); else elseBody = r.stmts;
          const et = r.end.text;
          i = r.next + 1;
          if (et === "endif") { endLine = r.end.no; break; }
          if ((m = /^elseif\s*\((.*)\)$/.exec(et))) {
            if (!cond) throw new PseudoError("else の後に elseif は書けません", r.end.no);
            cond = parseExpr(m[1], r.end.no); condLine = r.end.no;
            continue;
          }
          if (et === "else") {
            if (!cond) throw new PseudoError("else が2回あります", r.end.no);
            cond = null; elseLine = r.end.no;
            continue;
          }
          throw new PseudoError(`「${et}」の書き方がわかりません`, r.end.no);
        }
        stmts.push({ k: "if", line: L.no, branches, elseBody, elseLine, endLine });
        continue;
      }
      if ((m = /^while\s*\((.*)\)$/.exec(t))) {
        const r = parseBlock(ls, i + 1, ["endwhile"], doIndent);
        if (!r.end) throw new PseudoError("while に対応する endwhile がありません", L.no);
        stmts.push({ k: "while", line: L.no, cond: parseExpr(m[1], L.no), body: r.stmts });
        i = r.next + 1;
        continue;
      }
      if (t === "do") {
        const r = parseBlock(ls, i + 1, ["while"], L.indent);
        const mm = r.end && /^while\s*\((.*)\)$/.exec(r.end.text);
        if (!mm) throw new PseudoError("do に対応する while (条件) がありません", L.no);
        stmts.push({ k: "dowhile", line: L.no, body: r.stmts, cond: parseExpr(mm[1], r.end.no), condLine: r.end.no });
        i = r.next + 1;
        continue;
      }
      if ((m = /^for\s*\((.*)\)$/.exec(t))) {
        const c = RE.forCtl.exec(m[1].trim());
        if (!c) throw new PseudoError("for の書き方がわかりません（例: i を 1 から n まで 1 ずつ増やす）", L.no);
        const r = parseBlock(ls, i + 1, ["endfor"], doIndent);
        if (!r.end) throw new PseudoError("for に対応する endfor がありません", L.no);
        stmts.push({ k: "for", line: L.no, v: c[1], from: parseExpr(c[2], L.no), to: parseExpr(c[3], L.no),
          step: parseExpr(c[4], L.no), up: c[5] === "増やす", body: r.stmts });
        i = r.next + 1;
        continue;
      }
      if (["endif", "endwhile", "endfor", "elseif", "else"].includes(head)) throw new PseudoError(`対応する文がない「${head}」です`, L.no);
      if ((m = /^return(?:\s+(.+))?$/.exec(t))) {
        stmts.push({ k: "ret", line: L.no, e: m[1] ? parseExpr(m[1], L.no) : null });
        i++;
        continue;
      }
      if ((m = RE.append.exec(t))) {
        stmts.push({ k: "append", line: L.no, target: parseExpr(m[1], L.no), e: parseExpr(m[2], L.no) });
        i++;
        continue;
      }
      if ((m = RE.decl.exec(t))) {
        const items = splitTop(m[3]).map((part) => {
          const a = indexOfTop(part, "←");
          const name = (a < 0 ? part : part.slice(0, a)).trim();
          if (!/^[A-Za-z_]\w*$/.test(name)) throw new PseudoError(`変数名「${name}」が正しくありません`, L.no);
          return { name, init: a < 0 ? null : parseExpr(part.slice(a + 1), L.no) };
        });
        stmts.push({ k: "decl", line: L.no, global: !!m[1], type: m[2], items });
        i++;
        continue;
      }
      const a = indexOfTop(t, "←");
      if (a >= 0) {
        const target = parseExpr(t.slice(0, a), L.no);
        if (target.k !== "var" && target.k !== "idx") throw new PseudoError("← の左側には変数か配列の要素を書きます", L.no);
        stmts.push({ k: "set", line: L.no, target, e: parseExpr(t.slice(a + 1), L.no) });
        i++;
        continue;
      }
      const e = parseExpr(t, L.no);
      if (e.k !== "call") throw new PseudoError(`この行の書き方がわかりません:「${t}」`, L.no);
      stmts.push({ k: "callstmt", line: L.no, e });
      i++;
    }
    return { stmts, next: i, end: null };
  }

  function preprocess(source) {
    const raw = String(source).replace(/\r\n?/g, "\n").split("\n");
    const lines = [];
    let inBlock = false;
    raw.forEach((text, n) => {
      let out = "", k = 0;
      while (k < text.length) {
        if (inBlock) {
          const e = text.indexOf("*/", k);
          if (e < 0) k = text.length; else { inBlock = false; k = e + 2; }
        } else {
          const b = text.indexOf("/*", k), l = text.indexOf("//", k);
          if (l >= 0 && (b < 0 || l < b)) { out += text.slice(k, l); k = text.length; }
          else if (b >= 0) { out += text.slice(k, b); inBlock = true; k = b + 2; }
          else { out += text.slice(k); k = text.length; }
        }
      }
      const norm = out.normalize("NFKC").replace(/\s+$/, "");
      if (norm.trim()) lines.push({ no: n + 1, text: norm.trim(), indent: /^\s*/.exec(norm)[0].replace(/\t/g, "    ").length });
    });
    return lines;
  }

  function compile(source) {
    const lines = preprocess(source);
    const funcs = Object.create(null);
    const topLines = [];
    let i = 0;
    while (i < lines.length) {
      const L = lines[i];
      if (!L.text.startsWith("○")) { topLines.push(L); i++; continue; }
      const m = RE.head.exec(L.text);
      if (!m) throw new PseudoError("関数・手続の宣言の書き方がわかりません（例: ○整数型: f(整数型: x)）", L.no);
      const params = splitTop(m[3]).map((s) => {
        const pm = RE.param.exec(s);
        if (!pm) throw new PseudoError(`引数「${s}」の書き方がわかりません（例: 整数型: x）`, L.no);
        return { type: pm[1], name: pm[2] };
      });
      let j = i + 1;
      const body = [];
      while (j < lines.length && lines[j].indent > L.indent && !lines[j].text.startsWith("○")) body.push(lines[j++]);
      const r = parseBlock(body, 0, [], Infinity);
      if (funcs[m[2]]) throw new PseudoError(`関数「${m[2]}」が2回宣言されています`, L.no);
      funcs[m[2]] = { name: m[2], type: m[1] || null, params, body: r.stmts, line: L.no };
      i = j;
    }
    return { funcs, top: parseBlock(topLines, 0, [], Infinity).stmts };
  }

  /* ---------- 実行 ---------- */
  function clone(v) { return Array.isArray(v) ? v.map(clone) : v; }
  function format(v) {
    if (v === UNDEF || v === undefined) return "未定義";
    if (Array.isArray(v)) return "{" + v.map(formatInner).join(", ") + "}";
    if (typeof v === "boolean") return v ? "true" : "false";
    if (typeof v === "number") return Number.isInteger(v) ? String(v) : String(Math.round(v * 1e6) / 1e6);
    return String(v);
  }
  function formatInner(v) { return typeof v === "string" ? `"${v}"` : format(v); }
  function toBool(v, line) {
    if (typeof v !== "boolean") throw new PseudoError(`条件の結果が true / false になっていません（${format(v)}）`, line);
    return v;
  }
  function num(v, line, op) {
    if (typeof v !== "number") throw new PseudoError(`「${op}」は数値どうしで計算します（${format(v)}）`, line);
    return v;
  }

  class Machine {
    constructor(prog) { this.prog = prog; this.globals = new Map(); this.frames = [{ name: "メイン", vars: this.globals, global: true }]; this.out = []; }
    get frame() { return this.frames[this.frames.length - 1]; }
    scopeOf(name) { return this.frame.vars.has(name) ? this.frame.vars : this.globals.has(name) ? this.globals : null; }
    get(name, line) {
      const s = this.scopeOf(name);
      if (!s) throw new PseudoError(`変数「${name}」が宣言されていません`, line);
      return s.get(name);
    }
    set(name, v) { (this.scopeOf(name) || this.frame.vars).set(name, v); }
  }

  function* execBlock(m, stmts) { for (const s of stmts) yield* execStmt(m, s); }

  function* execStmt(m, s) {
    switch (s.k) {
      case "decl":
        yield { phase: "line", line: s.line };
        for (const it of s.items) {
          const v = it.init ? yield* evaluate(m, it.init, s.line) : UNDEF;
          (s.global ? m.globals : m.frame.vars).set(it.name, v);
        }
        yield { phase: "after", line: s.line };
        return;
      case "set": {
        yield { phase: "line", line: s.line };
        const v = yield* evaluate(m, s.e, s.line);
        if (s.target.k === "var") m.set(s.target.name, v);
        else {
          let obj = yield* evaluate(m, s.target.obj, s.line);
          const idx = [];
          for (const e of s.target.idx) idx.push(yield* evaluate(m, e, s.line));
          for (let n = 0; n < idx.length; n++) {
            checkIndex(obj, idx[n], s.line);
            if (n === idx.length - 1) obj[idx[n] - 1] = v; else obj = obj[idx[n] - 1];
          }
        }
        yield { phase: "after", line: s.line };
        return;
      }
      case "append": {
        yield { phase: "line", line: s.line };
        const arr = yield* evaluate(m, s.target, s.line);
        if (!Array.isArray(arr)) throw new PseudoError("末尾に追加できるのは配列だけです", s.line);
        arr.push(yield* evaluate(m, s.e, s.line));
        yield { phase: "after", line: s.line };
        return;
      }
      case "if":
        for (const b of s.branches) {
          yield { phase: "line", line: b.line };
          if (toBool(yield* evaluate(m, b.cond, b.line), b.line)) { yield* execBlock(m, b.body); return; }
        }
        if (s.elseBody) { yield { phase: "line", line: s.elseLine }; yield* execBlock(m, s.elseBody); }
        return;
      case "while":
        for (;;) {
          yield { phase: "line", line: s.line };
          if (!toBool(yield* evaluate(m, s.cond, s.line), s.line)) return;
          yield* execBlock(m, s.body);
        }
      case "dowhile":
        yield { phase: "line", line: s.line };
        for (;;) {
          yield* execBlock(m, s.body);
          yield { phase: "line", line: s.condLine };
          if (!toBool(yield* evaluate(m, s.cond, s.condLine), s.condLine)) return;
        }
      case "for": {
        yield { phase: "line", line: s.line };
        m.set(s.v, num(yield* evaluate(m, s.from, s.line), s.line, "for"));
        for (;;) {
          const to = num(yield* evaluate(m, s.to, s.line), s.line, "for");
          const cur = m.get(s.v, s.line);
          if (s.up ? cur > to : cur < to) return;
          yield* execBlock(m, s.body);
          yield { phase: "line", line: s.line };
          const step = num(yield* evaluate(m, s.step, s.line), s.line, "for");
          m.set(s.v, m.get(s.v, s.line) + (s.up ? step : -step));
        }
      }
      case "ret":
        yield { phase: "line", line: s.line };
        throw new Return(s.e ? yield* evaluate(m, s.e, s.line) : UNDEF);
      case "callstmt":
        yield { phase: "line", line: s.line };
        yield* evaluate(m, s.e, s.line);
        yield { phase: "after", line: s.line };
        return;
    }
  }

  function checkIndex(arr, i, line) {
    if (!Array.isArray(arr)) throw new PseudoError(`配列ではない値（${format(arr)}）に [ ] を付けています`, line);
    if (!Number.isInteger(i)) throw new PseudoError(`配列の番号が整数ではありません（${format(i)}）`, line);
    if (i < 1 || i > arr.length) throw new PseudoError(`配列の範囲外です（番号 ${i}、要素数 ${arr.length}）。配列の番号は 1 から始まります`, line);
  }

  function* evaluate(m, e, line) {
    switch (e.k) {
      case "lit": return e.v;
      case "var": return m.get(e.name, line);
      case "arr": {
        const a = [];
        for (const it of e.items) a.push(clone(yield* evaluate(m, it, line)));
        return a;
      }
      case "fill": {
        const n = yield* evaluate(m, e.n, line);
        if (!Number.isInteger(n) || n < 0) throw new PseudoError("{ n個の 値 } の n は 0 以上の整数にします", line);
        const v = yield* evaluate(m, e.v, line);
        return Array.from({ length: n }, () => clone(v));
      }
      case "idx": {
        let obj = yield* evaluate(m, e.obj, line);
        for (const ie of e.idx) {
          const i = yield* evaluate(m, ie, line);
          checkIndex(obj, i, line);
          obj = obj[i - 1];
        }
        return obj;
      }
      case "len": {
        const a = yield* evaluate(m, e.obj, line);
        if (!Array.isArray(a) && typeof a !== "string") throw new PseudoError(`要素数を数えられない値です（${format(a)}）`, line);
        return a.length;
      }
      case "un": {
        const v = yield* evaluate(m, e.e, line);
        if (e.op === "not") return !toBool(v, line);
        return e.op === "-" ? -num(v, line, "-") : num(v, line, "+");
      }
      case "bin": {
        if (e.op === "and") return toBool(yield* evaluate(m, e.l, line), line) ? toBool(yield* evaluate(m, e.r, line), line) : false;
        if (e.op === "or") return toBool(yield* evaluate(m, e.l, line), line) ? true : toBool(yield* evaluate(m, e.r, line), line);
        const l = yield* evaluate(m, e.l, line), r = yield* evaluate(m, e.r, line);
        switch (e.op) {
          case "+":
            if (typeof l === "string" || typeof r === "string") return format(l) + format(r);
            return num(l, line, "+") + num(r, line, "+");
          case "-": return num(l, line, "-") - num(r, line, "-");
          case "×": return num(l, line, "×") * num(r, line, "×");
          case "÷":
            if (num(r, line, "÷") === 0) throw new PseudoError("0 で割ろうとしました", line);
            return Number.isInteger(num(l, line, "÷")) && Number.isInteger(r) ? Math.trunc(l / r) : l / r;
          case "mod":
            if (num(r, line, "mod") === 0) throw new PseudoError("0 で割った余りは求められません", line);
            return num(l, line, "mod") % r;
          case "=": return l === r;
          case "≠": return l !== r;
          case "<": return cmp(l, r, line) < 0;
          case ">": return cmp(l, r, line) > 0;
          case "≦": return cmp(l, r, line) <= 0;
          case "≧": return cmp(l, r, line) >= 0;
        }
        throw new PseudoError(`演算子「${e.op}」は使えません`, line);
      }
      case "call": return yield* call(m, e, line);
    }
    throw new PseudoError("式を計算できません", line);
  }

  function cmp(l, r, line) {
    if (typeof l === "number" && typeof r === "number") return l - r;
    if (typeof l === "string" && typeof r === "string") return l < r ? -1 : l > r ? 1 : 0;
    throw new PseudoError(`大小を比べられない値です（${format(l)} と ${format(r)}）`, line);
  }

  function* call(m, e, line) {
    const args = [];
    for (const a of e.args) args.push(yield* evaluate(m, a, line));
    if (e.name === "print") { m.out.push(args.map(format).join(" ")); return UNDEF; }
    const fn = m.prog.funcs[e.name];
    if (!fn) throw new PseudoError(`関数・手続「${e.name}」が見つかりません`, line);
    if (fn.params.length !== args.length) throw new PseudoError(`「${e.name}」の引数は ${fn.params.length} 個です（${args.length} 個渡しています）`, line);
    if (m.frames.length > MAX_DEPTH) throw new PseudoError("呼び出しが深すぎます。再帰が止まらなくなっていないか確認してください", line);
    const vars = new Map();
    fn.params.forEach((p, i) => vars.set(p.name, args[i]));
    m.frames.push({ name: fn.name, vars });
    let ret = UNDEF;
    try {
      yield { phase: "line", line: fn.line };
      yield* execBlock(m, fn.body);
    } catch (x) {
      if (x instanceof Return) ret = x.value; else throw x;
    } finally {
      m.frames.pop();
    }
    return ret;
  }

  function snapshotVars(map) {
    const o = {};
    map.forEach((v, k) => { o[k] = clone(v); });
    return o;
  }

  /* ソースを実行する。events は「その行を実行する直前（line）／直後（after）」の状態の一覧 */
  function run(source, opts) {
    opts = opts || {};
    const max = opts.maxSteps || 20000;
    const res = { events: [], output: [], error: null };
    let m;
    try {
      m = new Machine(compile(source));
      const gen = execBlock(m, m.prog.top);
      let steps = 0;
      for (let r = gen.next(); !r.done; r = gen.next()) {
        if (++steps > max) throw new PseudoError("処理の回数が多すぎます。無限ループになっていないか確認してください", r.value.line);
        if (opts.record === false) continue;
        const f = m.frame;
        res.events.push({
          phase: r.value.phase, line: r.value.line, fn: f.name, depth: m.frames.length - 1,
          stack: m.frames.map((x) => x.name), vars: snapshotVars(f.vars),
          globals: f.global ? null : snapshotVars(m.globals), out: m.out.length,
        });
      }
    } catch (x) {
      if (x instanceof PseudoError) res.error = x;
      else if (x instanceof Return) res.error = new PseudoError("return は関数の中でしか使えません");
      else if (x instanceof RangeError) res.error = new PseudoError("呼び出しが深すぎます。再帰が止まらなくなっていないか確認してください");
      else res.error = new PseudoError(String((x && x.message) || x));
    }
    if (m) res.output = m.out.slice();
    return res;
  }

  root.Pseudo = { run, compile, format, PseudoError, UNDEF };
})(typeof window !== "undefined" ? window : this);
