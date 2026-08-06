import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const prototypePath = path.resolve(
  here,
  "../60_OUTPUTS/prototype/FreeFlexVPN_app_prototype_v1.1.html",
);
const html = fs.readFileSync(prototypePath, "utf8");

const checks = [];
const check = (name, condition) => {
  checks.push({ name, pass: Boolean(condition) });
};

const screenNames = [...html.matchAll(/<section[^>]+data-screen="([^"]+)"/g)].map(
  (match) => match[1],
);
const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map((match) => match[1]);
const uniqueIds = new Set(ids);
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);

check("9개 핵심 화면", screenNames.length === 9);
check("공식 채택 표식", html.includes("ADOPTED") && html.includes("UI · UX v1.1"));
check("화면 이름 중복 없음", new Set(screenNames).size === screenNames.length);
check("HTML id 중복 없음", uniqueIds.size === ids.length);
check("월 1GB 무료 계약", html.includes("월 1GB 무료"));
check("충전 용량 무기한 계약", html.includes("충전분 무기한"));
check("구독 없음 계약", html.includes("자동결제·정기구독 없음"));
check("기획 가격 설계안", html.includes("3GB") && html.includes("1,500원"));
check("벌크 가격 설계안", html.includes("300GB") && html.includes("39,900원"));
check("가격 미검증 고지", html.includes("지불의사 미검증"));
check("WireGuard 온보딩", html.includes("WireGuard"));
check("최대 2대 기기 제한", html.includes("최대 2대"));
check("무료 용량 우선 사용", html.includes("무료분이 먼저 쓰이고"));
check("프로토타입 정직 고지", html.includes("실제 VPN·결제·계정 발급 기능 없음"));
check("하단 메뉴 터치 겹침 교정", html.includes("position:relative;height:72px;margin:18px -12px -82px"));
check("영속 저장 미사용", !html.includes("localStorage"));
check("인라인 스크립트 존재", Boolean(scriptMatch));

if (scriptMatch) {
  try {
    // 구문만 검사한다. DOM이 없는 Node 환경에서 스크립트를 실행하지 않는다.
    new Function(scriptMatch[1]);
    check("JavaScript 구문", true);
  } catch (error) {
    check(`JavaScript 구문: ${error.message}`, false);
  }
}

const failures = checks.filter((item) => !item.pass);
for (const item of checks) {
  console.log(`${item.pass ? "PASS" : "FAIL"}  ${item.name}`);
}
console.log(`\nRESULT ${checks.length - failures.length}/${checks.length} PASS`);

if (failures.length > 0) {
  process.exitCode = 1;
}
