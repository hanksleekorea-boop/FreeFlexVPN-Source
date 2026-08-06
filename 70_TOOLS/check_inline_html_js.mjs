#!/usr/bin/env node
// 단일 HTML의 인라인 JavaScript를 실행하지 않고 구문만 검사한다.
import fs from "node:fs";
import path from "node:path";

const sourcePath = process.argv[2];
if (!sourcePath) {
  console.error("사용법: node check_inline_html_js.mjs <single-html>");
  process.exit(2);
}
const resolved = path.resolve(sourcePath);
const stat = fs.statSync(resolved);
if (!stat.isFile() || stat.size <= 0 || stat.size > 2_000_000) {
  throw new Error("HTML 파일 크기가 허용 범위를 벗어났습니다.");
}
const html = fs.readFileSync(resolved, "utf8");
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(match => match[1]);
if (scripts.length === 0) {
  throw new Error("인라인 JavaScript가 없습니다.");
}
for (const source of scripts) {
  new Function(source);
}
console.log(`인라인 JavaScript 구문 PASS — ${scripts.length}개 블록 · ${stat.size} bytes`);
