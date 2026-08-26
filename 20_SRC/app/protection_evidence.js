const PROTECTION_FIELDS = Object.freeze(["tunnel", "external_ipv4_country", "dns_reachable", "ipv6", "webrtc", "kill_switch"]);
const REQUIRED_FIELDS = Object.freeze(["tunnel", "external_ipv4_country", "dns_reachable", "ipv6", "kill_switch"]);
const DEFAULT_MAX_AGE_MS = 5 * 60 * 1000;
const EVIDENCE_ID = /^[a-z][a-z0-9_-]{2,63}$/;
const ALLOWED_SOURCE_CLASSES = Object.freeze(["automatic", "browser", "android", "windows", "iphone", "transaction", "operation", "expert", "persona"]);

function strictBoolean(value) {
  return value === true ? true : value === false ? false : null;
}

function validTimestamp(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  const milliseconds = Date.parse(value);
  return Number.isFinite(milliseconds) ? new Date(milliseconds).toISOString() : null;
}

function evidenceId(value) {
  return typeof value === "string" && EVIDENCE_ID.test(value) ? value : null;
}

function sourceClass(value) {
  return ALLOWED_SOURCE_CLASSES.includes(value) ? value : null;
}

export function sanitizeProtectionEvidence(input = {}) {
  const checks = input && typeof input.checks === "object" && !Array.isArray(input.checks) ? input.checks : {};
  const sanitized = {
    state: ["setup_needed", "checking", "protected", "limited", "disconnected", "cancelled", "error"].includes(input.state) ? input.state : "limited",
    checked_at: validTimestamp(input.checked_at || input.checkedAt),
    expires_at: validTimestamp(input.expires_at || input.expiresAt),
    evidence_id: evidenceId(input.evidence_id || input.evidenceId),
    source_class: sourceClass(input.source_class || input.sourceClass),
    checks: {
      tunnel: strictBoolean(checks.tunnel),
      external_ipv4_country: strictBoolean(checks.external_ipv4_country ?? checks.exit_ip),
      dns_reachable: strictBoolean(checks.dns_reachable ?? checks.dns),
      ipv6: strictBoolean(checks.ipv6),
      webrtc: strictBoolean(checks.webrtc),
      kill_switch: strictBoolean(checks.kill_switch),
    },
  };
  return sanitized;
}

export function deriveProtectionEvidencePresentation(input = {}, options = {}) {
  const evidence = sanitizeProtectionEvidence(input);
  const nowMs = Date.parse(options.now || new Date().toISOString());
  const checkedMs = evidence.checked_at ? Date.parse(evidence.checked_at) : NaN;
  const explicitExpiryMs = evidence.expires_at ? Date.parse(evidence.expires_at) : NaN;
  const maxAgeMs = Number.isFinite(options.maxAgeMs) && options.maxAgeMs > 0 ? options.maxAgeMs : DEFAULT_MAX_AGE_MS;
  const expiryMs = Number.isFinite(explicitExpiryMs) ? explicitExpiryMs : checkedMs + maxAgeMs;
  const freshness = !Number.isFinite(checkedMs) ? "unknown" : (!Number.isFinite(nowMs) || nowMs > expiryMs ? "stale" : "fresh");
  const values = REQUIRED_FIELDS.map(name => evidence.checks[name]);
  const passed = values.filter(value => value === true).length;
  const failed = values.filter(value => value === false).length;
  const missing = values.filter(value => value === null).length;
  const directAndroidEvidence = evidence.source_class === "android" && evidence.evidence_id !== null;
  let presentation = "unverified";
  let evidenceGrade = "unconfirmed";
  let title = "확인 필요";
  let copy = "실제 터널·외부 경로·DNS·누수 방지 근거를 아직 모두 확인하지 못했습니다.";

  if (evidence.state === "checking") {
    presentation = "checking"; title = "확인 중"; copy = "최신 보호 근거를 확인하고 있습니다.";
  } else if (evidence.state === "cancelled") {
    presentation = "cancelled"; title = "확인 취소됨"; copy = "연결 상태는 바뀌지 않았습니다. 원할 때 다시 확인하세요.";
  } else if (evidence.state === "disconnected" || evidence.state === "error" || failed > 0) {
    presentation = "error"; title = "보호 안 됨"; copy = "필수 보호 근거가 일치하지 않습니다. 기존 설정을 지우지 말고 복구 안내를 확인하세요.";
  } else if (freshness === "stale" && passed > 0) {
    presentation = "stale"; evidenceGrade = "partial"; title = "다시 확인"; copy = "이전 확인 기록이 오래되었습니다. 현재 보호 상태로 사용하지 않습니다.";
  } else if (evidence.state === "protected" && passed === REQUIRED_FIELDS.length && freshness === "fresh" && directAndroidEvidence) {
    presentation = "protected"; evidenceGrade = "confirmed"; title = "보호됨"; copy = "필수 보호 근거가 모두 일치하며 최신입니다.";
  } else if (evidence.state === "protected" && passed === REQUIRED_FIELDS.length && freshness === "fresh") {
    presentation = "partial"; evidenceGrade = "partial"; title = "직접 확인 필요"; copy = "웹·자동 확인만으로는 실제 Android 보호 상태를 확정하지 않습니다.";
  } else if (passed > 0 || evidence.state === "protected") {
    presentation = "partial"; evidenceGrade = "partial"; title = "부분 보호"; copy = `${passed}/${REQUIRED_FIELDS.length}개 필수 근거만 확인했습니다. 미확인 항목을 완료로 표시하지 않습니다.`;
  }

  return Object.freeze({
    presentation,
    evidence_grade: evidenceGrade,
    freshness,
    title,
    copy,
    checked_at: evidence.checked_at,
    expires_at: evidence.expires_at,
    evidence_id: evidence.evidence_id,
    source_class: evidence.source_class,
    checks: Object.freeze({ ...evidence.checks }),
    counts: Object.freeze({ passed, failed, missing, required: REQUIRED_FIELDS.length }),
    scope: Object.freeze([...PROTECTION_FIELDS]),
  });
}
