/* FE用語ドリル 運用LINE: お問い合わせ（ほかのファイルと合わせて1つのプログラム。分け方は config.gs の先頭） */

/* ---------- お問い合わせ（フォームの回答シート） ---------- */
function responseSheet() {
  const sheets = SpreadsheetApp.getActive().getSheets();
  return sheets.find((s) => s.getRange(1, 1).getValue() === "タイムスタンプ") || sheets[0];
}

/* 「対応済み」の列がなければ、いちばん右に作る */
function doneColumn(sheet) {
  const head = sheet.getRange(1, 1, 1, Math.max(1, sheet.getLastColumn())).getValues()[0];
  let col = head.indexOf("対応済み") + 1;
  if (!col) {
    col = head.length + 1;
    sheet.getRange(1, col).setValue("対応済み");
  }
  return col;
}

/* 見出しの一部の文字から列を探す（例: 「種類」→「お問い合わせの種類」） */
function fieldOf(head, row, word) {
  const i = head.findIndex((h) => String(h).indexOf(word) >= 0);
  return i >= 0 ? String(row[i] || "").trim() : "";
}

function inquiryText(head, row) {
  const body = fieldOf(head, row, "内容");
  return [
    "種類: " + (fieldOf(head, row, "種類") || "（なし）"),
    "対象: " + (fieldOf(head, row, "対象") || "（なし）"),
    "内容: " + (body.length > 300 ? body.slice(0, 300) + "…" : body),
    "返信先: " + (fieldOf(head, row, "メール") ? "メールアドレスあり（スプレッドシートで確認）" : "なし"),
  ].join("\n");
}

/* 未対応のお問い合わせ: [{ no: 番号, head, row }] 番号はシートの行番号 − 1 */
function openInquiries() {
  const sheet = responseSheet();
  const last = sheet.getLastRow();
  if (last < 2) return [];
  const col = doneColumn(sheet);
  const values = sheet.getRange(1, 1, last, Math.max(col, sheet.getLastColumn())).getValues();
  const head = values[0];
  const out = [];
  for (let r = 1; r < values.length; r++) {
    if (values[r][0] && !values[r][col - 1]) out.push({ no: r, head, row: values[r] });
  }
  return out;
}

/* フォームに投稿があったとき（トリガーから呼ばれる） */
function onFormSubmit(e) {
  if (!prop("OWNER_USER_ID")) return;
  const sheet = responseSheet();
  const head = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const rowNo = e && e.range ? e.range.getRow() : sheet.getLastRow();
  const row = sheet.getRange(rowNo, 1, 1, head.length).getValues()[0];
  const no = rowNo - 1;
  push([TALK.newInquiry(no), "", inquiryText(head, row), "", TALK.newInquiryFoot(no)].join("\n"));
}

function listText() {
  const items = openInquiries();
  if (!items.length) return TALK.inquiryNone;
  const shown = items.slice(-10);
  return [TALK.listHead(items.length), ""]
    .concat(shown.map((it) => `■ ${it.no}番（${fmt(new Date(it.row[0]), "M/d")}）\n${inquiryText(it.head, it.row)}`).join("\n\n"))
    .concat(["", TALK.listFoot]).join("\n");
}

function markDone(no) {
  const sheet = responseSheet();
  const rowNo = no + 1;
  if (no < 1 || rowNo > sheet.getLastRow() || !sheet.getRange(rowNo, 1).getValue()) return TALK.doneMissing(no);
  const cell = sheet.getRange(rowNo, doneColumn(sheet));
  if (cell.getValue()) return TALK.doneAlready(no);
  cell.setValue(fmt(new Date(), "yyyy/MM/dd HH:mm"));
  return TALK.done(no);
}
