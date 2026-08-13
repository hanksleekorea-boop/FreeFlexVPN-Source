const MOBILE_API_MODES = new Set(["unconfigured", "connecting", "live", "unavailable"]);
const MOBILE_PROTECTION_STATES = new Set(["setup_needed", "checking", "protected", "limited", "disconnected", "unverified"]);
const MOBILE_PLATFORMS = new Set(["android", "ios", "other"]);

function mobileBoolean(value) {
  return value === true;
}

function mobileEnum(value, allowed, fallback) {
  return allowed.has(value) ? value : fallback;
}

export function evaluateMobileReadiness(input = {}) {
  const apiMode = mobileEnum(input.apiMode, MOBILE_API_MODES, "unconfigured");
  const protectionState = mobileEnum(input.protectionState, MOBILE_PROTECTION_STATES, "unverified");
  const platform = mobileEnum(input.platform, MOBILE_PLATFORMS, "other");
  const checks = [
    { id: "secure-context", state: mobileBoolean(input.secureContext) ? "pass" : "fail", evidence: "browser" },
    { id: "network", state: mobileBoolean(input.online) ? "pass" : "fail", evidence: "browser" },
    { id: "service-api", state: apiMode === "live" ? "pass" : "pending", evidence: "service" },
    { id: "install-mode", state: mobileBoolean(input.standalone) ? "pass" : "pending", evidence: "browser" },
    { id: "wireguard-client", state: mobileBoolean(input.wireguardClientConfirmed) ? "self_reported" : "pending", evidence: "self_report" },
    { id: "profile-import", state: mobileBoolean(input.profileImportedConfirmed) ? "self_reported" : "pending", evidence: "self_report" },
    { id: "protection", state: protectionState === "protected" ? "pass" : protectionState === "disconnected" ? "fail" : "pending", evidence: "service" },
    { id: "recovery-drill", state: mobileBoolean(input.recoveryDrillConfirmed) ? "self_reported" : "pending", evidence: "self_report" },
  ];
  const completedCount = checks.filter(check => check.state === "pass" || check.state === "self_reported").length;
  const verifiedCount = checks.filter(check => check.state === "pass").length;
  return {
    schema: "freeflex-mobile-readiness-v1",
    platform,
    apiMode,
    protectionState,
    checks,
    completedCount,
    verifiedCount,
    readyForCandidateReview: completedCount === checks.length,
    commercialEvidenceReady: verifiedCount === checks.length,
  };
}

export function createMobileRecoveryCard(input = {}) {
  const platform = mobileEnum(input.platform, MOBILE_PLATFORMS, "other");
  const stores = {
    android: "https://play.google.com/store/apps/details?id=com.wireguard.android",
    ios: "https://apps.apple.com/app/wireguard/id1441195209",
    other: "https://www.wireguard.com/install/",
  };
  return {
    schema: "freeflex-mobile-recovery-v1",
    platform,
    officialWireGuardUrl: stores[platform],
    steps: [
      "공식 WireGuard 앱의 터널 상태를 확인합니다.",
      "인터넷이 막혔으면 터널·항상 연결·차단 모드를 끄고 일반 웹 복귀를 확인합니다.",
      "기존 설정을 삭제하거나 덮어쓰지 말고 지원 시각과 실패 단계만 기록합니다.",
    ],
    privacy: {
      excluded: ["ip_address", "private_key", "configuration", "browsing_history", "account_identifier"],
      automaticallyTransmitted: false,
    },
  };
}
