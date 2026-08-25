#!/usr/bin/env node
/*
 * Continuous Readiness Index analysis engine (public, dependency-free).
 * Input: crh-project-evidence/v1 JSON.  Output: crh-analysis-result/v1 JSON
 * and, when requested, a local Markdown report.  This file deliberately shares
 * the published lens next to it so a target project can run it without a server.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ENGINE_VERSION = '1.0.1';
const PLATFORM = { mobile: new Set(['C', 'M']), web: new Set(['C', 'W']) };
const FRESH_DAYS = { 1: 180, 2: 120, 3: 60, auto: 180, self: 365 };
const GRADE = [[90, 'L5', '출시·확장 가능'], [75, 'L4', '정식 출시 준비'], [60, 'L3', '오픈 베타 준비'], [40, 'L2', '기능 구축 중'], [0, 'L1', '기획·초기 구축']];
const DIMENSIONS = [
  ['feat', '기능 폭·깊이'], ['ux', 'UX 완성도'], ['perf', '성능·안정성'], ['trust', '평점·신뢰'],
  ['reach', '사용자 규모·도달'], ['price', '가격 경쟁력'], ['monet', '수익모델 성숙도'], ['local', '현지화·접근성'],
];
const DIRECTION = {
  model: {
    sub: { weights: { d1: 11, d2: 10, d3: 9, d4: 11, d5: 13, d6: 10, d7: 8, d8: 7, d9: 10, d10: 11 }, crit: ['m01', 'm08', 'b02', 'b05'] },
    com: { weights: { d1: 10, d2: 10, d3: 8, d4: 13, d5: 15, d6: 12, d7: 7, d8: 6, d9: 10, d10: 9 }, crit: ['m02', 'm03', 'm04', 'm06', 'l07', 'l08', 's12'] },
    b2b: { weights: { d1: 11, d2: 12, d3: 7, d4: 13, d5: 10, d6: 10, d7: 6, d8: 10, d9: 12, d10: 9 }, crit: ['o03', 'o04', 'q06', 's08', 'b02'] },
    ad: { weights: { d1: 12, d2: 10, d3: 11, d4: 10, d5: 7, d6: 11, d7: 9, d8: 9, d9: 8, d10: 13 }, crit: ['l06', 'b04', 'b10', 'b05'] }, one: { crit: ['m02', 'm04'] },
  },
  market: { kr: { crit: ['l07', 'l08'] }, glob: { crit: ['f07', 'l03', 'l06', 'm05', 'u03'] }, kr2g: { crit: ['f07', 'l03'] } },
  pay: { iap: { crit: ['m10', 'm11'] }, pg: { crit: ['m02', 'm06', 's12'] }, both: { crit: ['m02', 'm10', 'm06'] }, none: { crit: ['b04', 'b10'] } },
  pf: { app: { mix: [0.65, 0.35], crit: ['r04', 'r05', 'r06'] }, web: { mix: [0.35, 0.65], crit: ['p07', 'p08', 'p09', 'r08'] }, eq: { mix: [0.5, 0.5] } },
  stage: { cb: { target: 60 }, ob: { target: 70, crit: ['m02', 'q02'] }, ga: { target: 75, crit: ['q04', 'r02', 'o02'] }, scale: { target: 85, crit: ['b02', 'b06', 'b10', 'q05'] } },
  sens: { low: {}, mid: { delta: { d4: 2, d6: 2, d8: -1, d7: -1, d3: -1, d10: -1 }, crit: ['s03', 'l02', 'l04'] }, high: { delta: { d4: 4, d6: 2, d8: -2, d7: -1, d3: -1, d10: -2 }, crit: ['s03', 's05', 's08', 'q06'] } },
  team: { s: { crit: ['o01', 'o05', 'q01'] }, m: { crit: ['o02', 'o05'] }, l: { crit: ['o02', 'o06', 'o09'] } },
  edge: { price: { crit: ['b02', 'b09'] }, feat: { crit: ['u04', 'q01'] }, ux: { crit: ['u04', 'u05', 'p07'] }, content: { crit: ['l10'] }, net: { crit: ['b05', 'o04'] } },
  when: { m1: { crit: ['r02', 'r05', 'q04'] }, m3: { crit: ['r03'] }, m6: {} },
};

const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const round = value => value === null || value === undefined ? null : Math.round(value * 100) / 100;
const plain = value => String(value ?? '').replace(/[|\r\n]/g, ' ').trim();
const isoDay = value => /^\d{4}-\d{2}-\d{2}$/.test(String(value || '')) ? String(value) : null;
function fail(message) { throw new Error(`CRH engine: ${message}`); }
function itemWeight(item) { return item.g ? 2 : 1; }
function inPlatform(item, platform) { return PLATFORM[platform].has(item.p); }
function statusValue(raw) {
  if (raw === 'na' || raw === 'unknown' || raw === 'unk' || raw === null || raw === undefined) return raw === 'unknown' || raw === 'unk' ? 'unk' : raw;
  const value = typeof raw === 'object' ? raw.score : raw;
  if (!Number.isInteger(value) || value < 0 || value > 4) fail(`점수는 0~4 정수여야 합니다: ${value}`);
  return value;
}
function freshness(raw, assessedAt, warnings, itemId, platform) {
  if (typeof raw !== 'object' || !raw) return { factor: 1, observedAt: null, tier: 'self', stale: false };
  const observedAt = isoDay(raw.observedAt || raw.date);
  const tier = String(raw.tier || raw.evidenceTier || 'self');
  if (!observedAt) { warnings.push(`${platform}.${itemId}: 확인일이 없어 자가신고 365일 기준으로 처리했습니다.`); return { factor: 1, observedAt: null, tier, stale: false }; }
  const expiry = FRESH_DAYS[tier] ?? FRESH_DAYS.self;
  const days = Math.floor((Date.parse(`${assessedAt}T00:00:00Z`) - Date.parse(`${observedAt}T00:00:00Z`)) / 86400000);
  const stale = days > expiry;
  return { factor: stale ? 0.5 : 1, observedAt, tier, stale, days, expiry };
}
function loadLens(lensPath) {
  const lens = readJson(lensPath);
  if (lens.schema !== 'crh-lens' || !Array.isArray(lens.domains)) fail('유효한 crh-lens 파일이 아닙니다.');
  const items = new Map();
  lens.domains.forEach(domain => (domain.items || []).forEach(item => {
    if (items.has(item.id)) fail(`렌즈에 중복 항목 ID가 있습니다: ${item.id}`);
    items.set(item.id, { ...item, domain });
  }));
  return { lens, items };
}
function normalizeEvidence(input, items, warnings) {
  const source = input.evidence || {};
  const out = { mobile: {}, web: {} };
  for (const platform of Object.keys(out)) {
    for (const [id, raw] of Object.entries(source[platform] || {})) {
      const entry = items.get(id);
      if (!entry) fail(`${platform}.${id}: 렌즈에 없는 항목 ID입니다.`);
      if (!inPlatform(entry, platform)) fail(`${platform}.${id}: 이 플랫폼에 적용되지 않는 항목입니다.`);
      const value = statusValue(raw);
      out[platform][id] = { value, raw, fresh: freshness(raw, input.assessedAt, warnings, id, platform) };
    }
  }
  return out;
}
function directionConfig(direction = {}) {
  const weights = {};
  const critical = new Set();
  let mix = [0.5, 0.5], target = null;
  for (const [key, value] of Object.entries(direction)) {
    const option = DIRECTION[key]?.[value];
    if (!option) continue;
    if (option.weights) Object.assign(weights, option.weights);
    if (option.delta) for (const [domain, delta] of Object.entries(option.delta)) weights[domain] = (weights[domain] || 0) + delta;
    (option.crit || []).forEach(id => critical.add(id));
    if (option.mix) mix = option.mix;
    if (option.target) target = option.target;
  }
  return { weights, critical: [...critical], mix, target, selected: Object.keys(direction).filter(key => DIRECTION[key]?.[direction[key]]) };
}
function scopedItems(lens, config, scope) {
  const all = lens.domains.flatMap(domain => domain.items.map(item => ({ item, domain })));
  if (scope === 'all') return new Set(all.map(x => x.item.id));
  const gates = all.filter(x => x.item.g).sort((a, b) => (b.domain.weight * itemWeight(b.item)) - (a.domain.weight * itemWeight(a.item)));
  if (scope === 'min') return new Set(gates.slice(0, 8).map(x => x.item.id));
  if (scope === 'gate') return new Set(gates.slice(0, 20).map(x => x.item.id));
  if (scope === 'core') return new Set([...gates.map(x => x.item.id), ...config.critical]);
  fail(`지원하지 않는 범위입니다: ${scope}. all|min|gate|core 중 하나여야 합니다.`);
}
function domainWeights(lens, config) { return Object.fromEntries(lens.domains.map(d => [d.id, config.weights[d.id] ?? Number(d.weight) ?? 0])); }
function scorePlatform(lens, evidence, platform, selected, weights) {
  const domains = [];
  let allTotal = 0, allDone = 0, allUnknown = 0, stale = 0, selfN = 0, extN = 0, selfD = 0, extD = 0;
  for (const domain of lens.domains) {
    let num = 0, den = 0, total = 0, done = 0, unknown = 0, na = 0, domainStale = 0;
    for (const item of domain.items) {
      if (!inPlatform(item, platform) || !selected.has(item.id)) continue;
      const rated = evidence[platform][item.id];
      const value = rated?.value;
      if (value === 'na') { na++; continue; }
      total++; allTotal++;
      if (value === 'unk') { unknown++; allUnknown++; continue; }
      if (typeof value !== 'number') continue;
      const weight = itemWeight(item), factor = rated.fresh.factor;
      done++; allDone++; num += weight * value * factor; den += weight * 4;
      if (rated.fresh.stale) { stale++; domainStale++; }
      if (item.obs === 'ext') { extN += weight * value; extD += weight * 4; } else { selfN += weight * value; selfD += weight * 4; }
    }
    domains.push({ id: domain.id, name: domain.name, weight: weights[domain.id], score: den ? round(num / den * 100) : null, total, done, unknown, na, stale: domainStale });
  }
  const active = domains.filter(domain => domain.score !== null);
  const denom = active.reduce((sum, domain) => sum + domain.weight, 0);
  const score = denom ? active.reduce((sum, domain) => sum + domain.weight * domain.score, 0) / denom : null;
  return { score: round(score), domains, total: allTotal, done: allDone, unknown: allUnknown, stale, progress: allTotal ? round(allDone / allTotal) : 0, selfShare: (selfN + extN) ? round(selfN / (selfN + extN)) : null, externalScore: extD ? round(extN / extD * 100) : null, selfScore: selfD ? round(selfN / selfD * 100) : null };
}
function gates(lens, evidence, platform) {
  const list = lens.domains.flatMap(domain => domain.items.filter(item => item.g && inPlatform(item, platform)).map(item => {
    const value = evidence[platform][item.id]?.value;
    const status = value === 'na' ? 'na' : value === 'unk' ? 'unknown' : typeof value !== 'number' ? 'unrated' : value >= 3 ? 'pass' : 'fail';
    return { id: item.id, title: item.t, domain: domain.name, score: typeof value === 'number' ? value : null, status };
  }));
  return { items: list, pass: list.filter(x => x.status === 'pass').length, fail: list.filter(x => x.status === 'fail').length, unrated: list.filter(x => x.status === 'unrated' || x.status === 'unknown').length, na: list.filter(x => x.status === 'na').length };
}
function grade(score, progress, gateResult) {
  if (score === null) return { code: '—', name: '평가 전', score: null, blockers: gateResult.fail, confidence: 'none' };
  const [, baseCode, baseName] = GRADE.find(([minimum]) => score >= minimum);
  if (progress < 0.7) return { code: `${baseCode}?`, name: '판정 보류', score, blockers: gateResult.fail, confidence: 'low', reason: `평가 진행률 ${round(progress * 100)}%가 70% 미만` };
  if (gateResult.fail && (baseCode === 'L4' || baseCode === 'L5')) return { code: 'L3*', name: '게이트 미충족', score, blockers: gateResult.fail, confidence: 'normal', reason: `필수 게이트 ${gateResult.fail}건 미충족` };
  return { code: baseCode, name: baseName, score, blockers: gateResult.fail, confidence: 'normal' };
}
function combine(mobile, web, mix) { if (mobile === null && web === null) return null; if (mobile === null) return web; if (web === null) return mobile; return round(mix[0] * mobile + mix[1] * web); }
function benchmark(input, scores) {
  const bench = input.benchmark || {}, comparators = Array.isArray(bench.comparators) ? bench.comparators : [];
  if (comparators.length < 3) return { score: null, status: 'unavailable', reason: '비교 대상이 3개 미만입니다.', comparators: comparators.length, dimensions: [] };
  const toFive = value => value === null || value === undefined ? null : round(value / 20);
  const derived = {
    feat: toFive(scores.combinedDomains.d1),
    ux: toFive(scores.combinedDomains.d8),
    perf: toFive(average([scores.combinedDomains.d2, scores.combinedDomains.d3])),
    monet: toFive(scores.combinedDomains.d5),
  };
  const derivedCoverage = {
    feat: scores.combinedDomainCoverage.d1,
    ux: scores.combinedDomainCoverage.d8,
    perf: average([scores.combinedDomainCoverage.d2, scores.combinedDomainCoverage.d3]),
    monet: scores.combinedDomainCoverage.d5,
  };
  const ours = { ...derived, ...(bench.ours || {}) };
  const dimensions = [];
  for (const [key, name] of DIMENSIONS) {
    const own = Number(ours[key]);
    const values = comparators.map(row => Number(row?.scores?.[key])).filter(value => Number.isFinite(value) && value >= 0 && value <= 5);
    if (!Number.isFinite(own) || own < 0 || own > 5 || values.length < 3) continue;
    const below = values.filter(value => value < own - 1e-9).length;
    const equal = values.filter(value => Math.abs(value - own) <= 1e-9).length;
    const fromInput = Object.hasOwn(bench.ours || {}, key);
    dimensions.push({ key, name, ours: round(own), percentile: round((below + 0.5 * equal) / values.length * 100), comparisonCount: values.length, source: fromInput ? 'input' : 'derived-from-readiness', readinessCoverage: fromInput ? null : round(derivedCoverage[key]) });
  }
  if (!dimensions.length) return { score: null, status: 'unavailable', reason: '3개 이상 비교 가능한 차원이 없습니다.', comparators: comparators.length, dimensions: [] };
  const lowCoverage = dimensions.filter(row => row.source === 'derived-from-readiness' && (row.readinessCoverage === null || row.readinessCoverage < 0.7));
  return { score: round(average(dimensions.map(row => row.percentile))), status: 'calculated', confidence: lowCoverage.length ? 'low' : 'normal', caution: lowCoverage.length ? `준비도에서 자동 유도한 ${lowCoverage.length}개 차원의 증거 진행률이 70% 미만입니다.` : null, comparators: comparators.length, dimensions };
}
function average(values) { const valid = values.filter(value => value !== null && value !== undefined && Number.isFinite(value)); return valid.length ? valid.reduce((sum, value) => sum + value, 0) / valid.length : null; }
function directionAxis(lens, evidence, config) {
  if (!config.critical.length) return { score: null, status: 'unavailable', reason: '제품 방향을 선택하지 않았습니다.', total: 0, rated: 0, critical: [] };
  let total = 0, rated = 0, num = 0;
  for (const id of config.critical) {
    const item = lens.domains.flatMap(domain => domain.items).find(candidate => candidate.id === id);
    if (!item) continue;
    for (const platform of ['mobile', 'web']) {
      if (!inPlatform(item, platform)) continue;
      const value = evidence[platform][id]?.value;
      if (value === 'na') continue;
      total++;
      if (typeof value === 'number') { rated++; num += value; }
    }
  }
  return { score: rated ? round(num / (rated * 4) * 100) : null, status: rated ? 'calculated' : 'unavailable', reason: rated ? undefined : '방향 핵심 항목에 입력된 점수가 없습니다.', total, rated, critical: config.critical };
}
function gapAnalysis(lens, evidence, selected, weights, platform) {
  const sumWeights = Object.values(weights).reduce((sum, value) => sum + value, 0) || 1;
  const rows = [];
  for (const domain of lens.domains) for (const item of domain.items) {
    if (!inPlatform(item, platform) || !selected.has(item.id)) continue;
    const entry = evidence[platform][item.id], value = entry?.value;
    if (value === 'na' || value === 4) continue;
    const rated = typeof value === 'number', current = rated ? value : 0;
    rows.push({ platform, id: item.id, title: item.t, domain: domain.name, gate: Boolean(item.g), currentScore: rated ? value : null, status: value === 'unk' ? 'unknown' : rated ? 'rated' : 'unrated', impact: round(weights[domain.id] / sumWeights * 100 * itemWeight(item) * (4 - current) * (item.g ? 1.6 : 1) * (rated ? 1 : 0.85)), evidence: entry?.raw?.note || entry?.raw?.source || null });
  }
  return rows.sort((a, b) => b.impact - a.impact || Number(b.gate) - Number(a.gate));
}
function reportMarkdown(result) {
  const project = result.project || {}, featureRows = (project.features || []).slice(0, 30).map(feature => `| ${plain(feature.name || feature.feature || '이름 없음')} | ${plain(feature.platform || '공통')} | ${plain(feature.status || '미확인')} | ${plain(feature.evidence || feature.note || '')} |`).join('\n') || '| 입력된 기능이 없습니다. | - | - | - |';
  const gaps = result.gaps.slice(0, 20).map((gap, i) => `${i + 1}. **${gap.title}** (${gap.platform}, ${gap.domain}) — 현재 ${gap.currentScore ?? '미평가'}/4, 영향도 ${gap.impact}${gap.gate ? ', 필수 게이트' : ''}`).join('\n') || '입력된 범위에 갭이 없습니다.';
  const bench = result.benchmark.status === 'calculated' ? result.benchmark.dimensions.map(row => `| ${row.name} | ${row.ours}/5 | ${row.percentile}% | ${row.comparisonCount} | ${row.source} | ${row.readinessCoverage === null ? '—' : `${round(row.readinessCoverage * 100)}%`} |`).join('\n') : `계산 불가: ${result.benchmark.reason}`;
  return `# ${plain(project.name || '대상 프로젝트')} — Continuous Readiness Index 분석 보고서\n\n생성 시각: ${result.generatedAt}\n\n## 판정 요약\n\n| 구분 | 점수 | 등급 | 진행률 | 필수 게이트 실패 |\n|---|---:|---|---:|---:|\n| 모바일 | ${result.mobile.score ?? '—'} | ${result.mobile.grade.code} | ${round(result.mobile.progress * 100)}% | ${result.mobile.gates.fail} |\n| PC 웹 | ${result.web.score ?? '—'} | ${result.web.grade.code} | ${round(result.web.progress * 100)}% | ${result.web.gates.fail} |\n| 통합 준비도 | ${result.composite.score ?? '—'} | ${result.composite.grade?.code ?? '—'} | - | ${result.composite.blockers} |\n\n→ 이 표의 뜻: 점수와 등급은 입력된 증거만 사용하며, 진행률 70% 미만은 등급 끝의 ?로 표시합니다.\n\n## 대상 제품과 확인 기능\n\n${plain(project.description || '설명 미입력')}\n\n| 기능 | 플랫폼 | 상태 | 근거 |\n|---|---|---|---|\n${featureRows}\n\n→ 이 표의 뜻: 대상 프로젝트에서 실제로 제공한다고 입력된 기능과 그 근거를 기록합니다.\n\n## 가장 큰 갭 20개\n\n${gaps}\n\n## 시장 상대 위치\n\n${result.benchmark.status === 'calculated' ? `비교 백분위: **${result.benchmark.score}%** (비교 서비스 ${result.benchmark.comparators}개, 신뢰도 ${result.benchmark.confidence})${result.benchmark.caution ? `\n\n주의: ${result.benchmark.caution}` : ''}\n\n| 차원 | 우리 점수 | 백분위 | 비교 수 | 산출 근거 | 준비도 증거 진행률 |\n|---|---:|---:|---:|---|---:|\n${bench}\n\n→ 이 표의 뜻: 높을수록 입력된 비교 서비스 집단 안에서 상대 위치가 높다는 의미이며, 시장 전체 순위는 아닙니다. 준비도 증거 진행률이 낮으면 잠정 결과입니다.` : bench}\n\n## 방향 정합도\n\n${result.direction.status === 'calculated' ? `방향 핵심 항목 점수: **${result.direction.score}점** (${result.direction.rated}/${result.direction.total}개 증거 입력)` : `계산 불가: ${result.direction.reason}`}\n\n## 해석 주의\n\n- 이 결과는 ${result.lens.itemCount}개 기준과 입력 증거를 바탕으로 한 제품 준비도 진단이며, 법률 자문·준수 인증·시장 성과 보증이 아닙니다.\n- 자동/외부 검증과 자가 신고는 입력의 근거 등급과 확인일로 구분합니다. 실제 Android 기기 시험은 별도 증거가 없으면 미실시입니다.\n- 경고 ${result.warnings.length}건: ${result.warnings.length ? result.warnings.join(' / ') : '없음'}\n`;
}
export function analyze(input, options = {}) {
  if (!input || typeof input !== 'object') fail('입력 JSON 객체가 필요합니다.');
  if (input.schema && input.schema !== 'crh-project-evidence/v1') fail(`지원하지 않는 입력 schema: ${input.schema}`);
  const assessedAt = isoDay(input.assessedAt) || new Date().toISOString().slice(0, 10);
  input = { ...input, assessedAt };
  const { lens, items } = loadLens(options.lensPath || path.join(HERE, 'lens-core-v2.1.json'));
  const warnings = [];
  const evidence = normalizeEvidence(input, items, warnings);
  const config = directionConfig(input.direction);
  const scope = input.scope || 'all';
  const selected = scopedItems(lens, config, scope);
  const weights = domainWeights(lens, config);
  const mobile = scorePlatform(lens, evidence, 'mobile', selected, weights), web = scorePlatform(lens, evidence, 'web', selected, weights);
  mobile.gates = gates(lens, evidence, 'mobile'); web.gates = gates(lens, evidence, 'web');
  mobile.grade = grade(mobile.score, mobile.progress, mobile.gates); web.grade = grade(web.score, web.progress, web.gates);
  const combinedDomains = Object.fromEntries(lens.domains.map(domain => [domain.id, combine(mobile.domains.find(row => row.id === domain.id).score, web.domains.find(row => row.id === domain.id).score, config.mix)]));
  const scores = { combinedDomains };
  const combinedDomainCoverage = Object.fromEntries(lens.domains.map(domain => {
    const rows = [mobile, web].map(platform => platform.domains.find(row => row.id === domain.id)).filter(row => row.total > 0);
    return [domain.id, rows.length ? round(average(rows.map(row => row.done / row.total))) : null];
  }));
  scores.combinedDomainCoverage = combinedDomainCoverage;
  const bench = benchmark(input, scores), direction = directionAxis(lens, evidence, config);
  const axisWeights = { a1: Number(input.axisWeights?.a1 ?? 50), a2: Number(input.axisWeights?.a2 ?? 25), a3: Number(input.axisWeights?.a3 ?? 25) };
  const a1 = combine(mobile.score, web.score, config.mix), parts = [[axisWeights.a1, a1], [axisWeights.a2, bench.score], [axisWeights.a3, direction.score]].filter(([, value]) => value !== null && Number.isFinite(value));
  const compositeScore = parts.length ? round(parts.reduce((sum, [weight, value]) => sum + weight * value, 0) / parts.reduce((sum, [weight]) => sum + weight, 0)) : null;
  const blockers = mobile.gates.fail + web.gates.fail;
  const base = compositeScore === null ? null : GRADE.find(([minimum]) => compositeScore >= minimum);
  const composite = { score: compositeScore, axesUsed: parts.length, blockers, grade: base ? { code: blockers && (base[1] === 'L4' || base[1] === 'L5') ? 'L3*' : base[1], name: blockers && (base[1] === 'L4' || base[1] === 'L5') ? '게이트 미충족' : base[2] } : null };
  const result = { schema: 'crh-analysis-result/v1', engineVersion: ENGINE_VERSION, generatedAt: new Date().toISOString(), assessedAt, project: input.project || {}, lens: { name: lens.name, version: lens.version, itemCount: items.size, gateCount: [...items.values()].filter(entry => entry.g).length }, scope: { id: scope, selectedItems: selected.size }, direction: { ...direction, selected: config.selected, target: config.target, platformMix: { mobile: config.mix[0], web: config.mix[1] } }, mobile, web, axes: { general: a1, benchmark: bench.score, direction: direction.score, weights: axisWeights }, benchmark: bench, composite, gaps: [...gapAnalysis(lens, evidence, selected, weights, 'mobile'), ...gapAnalysis(lens, evidence, selected, weights, 'web')].sort((a, b) => b.impact - a.impact), warnings };
  return { ...result, reportMarkdown: reportMarkdown(result) };
}
function parseArgs(argv) {
  const result = {}; for (let i = 0; i < argv.length; i++) { const arg = argv[i]; if (arg === '--help' || arg === '-h') result.help = true; else if (['--input', '--out', '--markdown', '--lens'].includes(arg)) result[arg.slice(2)] = argv[++i]; else if (arg === '--force') result.force = true; else fail(`알 수 없는 인수: ${arg}`); } return result;
}
function usage() { return `사용법: node readiness-engine.mjs --input <evidence.json> [--out <result.json>] [--markdown <report.md>] [--lens <lens.json>] [--force]\n\n입력 형식과 예제: project-evidence.example.json`; }
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const args = parseArgs(process.argv.slice(2)); if (args.help) { console.log(usage()); process.exit(0); }
    if (!args.input) fail('--input이 필요합니다.');
    const result = analyze(readJson(path.resolve(args.input)), { lensPath: args.lens && path.resolve(args.lens) });
    for (const [kind, filename] of [['out', args.out], ['markdown', args.markdown]]) if (filename) {
      const target = path.resolve(filename); if (fs.existsSync(target) && !args.force) fail(`${target} 파일이 이미 있습니다. 덮어쓰려면 --force를 사용하세요.`);
      fs.mkdirSync(path.dirname(target), { recursive: true }); fs.writeFileSync(target, kind === 'out' ? `${JSON.stringify({ ...result, reportMarkdown: undefined }, null, 2)}\n` : result.reportMarkdown, 'utf8');
    }
    if (!args.out && !args.markdown) console.log(JSON.stringify({ ...result, reportMarkdown: undefined }, null, 2));
    else console.log(JSON.stringify({ ok: true, engineVersion: ENGINE_VERSION, json: args.out || null, markdown: args.markdown || null, composite: result.composite.score }, null, 2));
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
