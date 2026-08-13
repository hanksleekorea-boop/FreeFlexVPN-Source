const COMMERCIAL_GATE_IDS = Object.freeze([
  "privacy-rights",
  "support-diagnostic",
  "rollback-playbook",
  "payment-roundtrip",
  "refund-roundtrip",
  "legal-review",
  "operations-monitoring",
  "limited-release",
]);

function commercialBoolean(value) {
  return value === true;
}

export function evaluateCommercialReadiness(input = {}) {
  const documented = new Set(Array.isArray(input.documented) ? input.documented.filter(value => COMMERCIAL_GATE_IDS.includes(value)) : []);
  const verified = new Set(Array.isArray(input.verified) ? input.verified.filter(value => COMMERCIAL_GATE_IDS.includes(value)) : []);
  const checks = COMMERCIAL_GATE_IDS.map(id => ({
    id,
    state: verified.has(id) ? "verified" : documented.has(id) ? "documented" : "blocked",
    evidence: verified.has(id) ? "external_evidence" : documented.has(id) ? "local_contract" : "missing",
  }));
  return {
    schema: "freeflex-commercial-readiness-v1",
    checks,
    documentedCount: checks.filter(check => check.state === "documented" || check.state === "verified").length,
    verifiedCount: checks.filter(check => check.state === "verified").length,
    commercialEvidenceReady: checks.every(check => check.state === "verified"),
  };
}

export function createRedactedSupportBundle(input = {}) {
  const commercial = evaluateCommercialReadiness(input.commercial);
  return {
    schema: "freeflex-support-bundle-v1",
    generatedAt: typeof input.generatedAt === "string" ? input.generatedAt : new Date().toISOString(),
    platformFamily: ["android", "ios", "windows", "macos", "linux", "other"].includes(input.platformFamily) ? input.platformFamily : "other",
    browserFamily: ["chromium", "firefox", "safari", "other"].includes(input.browserFamily) ? input.browserFamily : "other",
    online: commercialBoolean(input.online),
    standalone: commercialBoolean(input.standalone),
    apiMode: ["unconfigured", "connecting", "live", "unavailable"].includes(input.apiMode) ? input.apiMode : "unconfigured",
    protectionState: ["setup_needed", "checking", "protected", "limited", "disconnected", "unverified"].includes(input.protectionState) ? input.protectionState : "unverified",
    commercialChecks: commercial.checks,
    privacy: {
      excluded: ["ip_address", "private_key", "configuration", "browsing_history", "account_identifier", "payment_method", "full_user_agent"],
      automaticallyTransmitted: false,
    },
  };
}

export function createIncidentChecklist(input = {}) {
  const platform = ["mobile", "pc"].includes(input.platform) ? input.platform : "mobile";
  return {
    schema: "freeflex-incident-checklist-v1",
    platform,
    steps: [
      "보호됨 표시를 믿지 말고 공식 WireGuard 앱의 터널 상태를 확인합니다.",
      "인터넷이 막혔으면 후보 터널·항상 연결·차단 모드를 끄고 일반 웹 복귀를 확인합니다.",
      "기존 프로필을 삭제·덮어쓰지 않고 발생 시각과 실패 단계만 지원 담당자에게 전달합니다.",
      "서비스 상태·비용·지원 채널이 확인될 때까지 결제나 새 사용자 확대를 중단합니다.",
    ],
    destructiveActionsAuthorized: false,
    sensitiveValuesRequired: false,
  };
}
