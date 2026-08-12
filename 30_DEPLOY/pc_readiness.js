const API_MODES = new Set(["unconfigured", "connecting", "live", "unavailable"]);
const PROTECTION_STATES = new Set(["setup_needed", "checking", "protected", "limited", "disconnected", "unverified"]);

function boolean(value) {
  return value === true;
}

function enumValue(value, allowed, fallback) {
  return allowed.has(value) ? value : fallback;
}

export function evaluatePcReadiness(input = {}) {
  const apiMode = enumValue(input.apiMode, API_MODES, "unconfigured");
  const protectionState = enumValue(input.protectionState, PROTECTION_STATES, "unverified");
  const checks = [
    { id: "secure-context", state: boolean(input.secureContext) ? "pass" : "fail", evidence: "browser" },
    { id: "network", state: boolean(input.online) ? "pass" : "fail", evidence: "browser" },
    { id: "service-api", state: apiMode === "live" ? "pass" : "pending", evidence: "service" },
    { id: "wireguard-client", state: boolean(input.wireguardClientConfirmed) ? "self_reported" : "pending", evidence: "self_report" },
    { id: "profile-import", state: boolean(input.profileImportedConfirmed) ? "self_reported" : "pending", evidence: "self_report" },
    { id: "protection", state: protectionState === "protected" ? "pass" : protectionState === "disconnected" ? "fail" : "pending", evidence: "service" },
    { id: "recovery-drill", state: boolean(input.recoveryDrillConfirmed) ? "self_reported" : "pending", evidence: "self_report" },
  ];
  const completedCount = checks.filter(check => check.state === "pass" || check.state === "self_reported").length;
  const verifiedCount = checks.filter(check => check.state === "pass").length;
  return {
    schema: "freeflex-pc-readiness-v1",
    apiMode,
    protectionState,
    checks,
    completedCount,
    verifiedCount,
    readyForCandidateReview: completedCount === checks.length,
    commercialEvidenceReady: verifiedCount === checks.length,
  };
}

export function createRedactedPcDiagnostic(input = {}) {
  const readiness = evaluatePcReadiness(input);
  return {
    schema: "freeflex-pc-diagnostic-v1",
    generatedAt: typeof input.generatedAt === "string" ? input.generatedAt : new Date().toISOString(),
    browserFamily: ["chromium", "firefox", "safari", "other"].includes(input.browserFamily) ? input.browserFamily : "other",
    platformFamily: ["windows", "macos", "linux", "other"].includes(input.platformFamily) ? input.platformFamily : "other",
    standalone: boolean(input.standalone),
    apiMode: readiness.apiMode,
    protectionState: readiness.protectionState,
    checks: readiness.checks.map(({ id, state, evidence }) => ({ id, state, evidence })),
    privacy: {
      excluded: ["ip_address", "private_key", "configuration", "browsing_history", "account_identifier", "full_user_agent"],
      automaticallyTransmitted: false,
    },
  };
}

export function sanitizePcPreferenceBackup(input = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("BACKUP_INVALID");
  if (input.schema !== "freeflex-pc-preferences-v1") throw new Error("BACKUP_SCHEMA_UNSUPPORTED");
  const accessibility = input.accessibility && typeof input.accessibility === "object" ? input.accessibility : {};
  return {
    schema: "freeflex-pc-preferences-v1",
    accessibility: { large: boolean(accessibility.large), contrast: boolean(accessibility.contrast) },
    focusMode: boolean(input.focusMode),
  };
}

export function createPcPreferenceBackup(input = {}) {
  return sanitizePcPreferenceBackup({
    schema: "freeflex-pc-preferences-v1",
    accessibility: input.accessibility,
    focusMode: input.focusMode,
  });
}
