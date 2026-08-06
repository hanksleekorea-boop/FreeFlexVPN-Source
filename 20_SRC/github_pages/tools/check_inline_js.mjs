import fs from "node:fs";

const html = fs.readFileSync(new URL("../app.html", import.meta.url), "utf8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((match) => match[1]);

if (scripts.length === 0) {
  throw new Error("인라인 JavaScript가 없습니다.");
}
for (const source of scripts) {
  new Function(source);
}
console.log(`인라인 JavaScript 구문 PASS — ${scripts.length}개 블록`);
