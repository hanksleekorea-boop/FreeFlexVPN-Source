import { FreeFlexApiClient, FreeFlexApiError, bytesToGb, consumeLaunchParameters } from "./pwa_api_client.js";
import { createDeviceProfile, manualFallback, supportsBrowserX25519 } from "./client_keygen.js";
import { MOMENTS, TIER_LABELS, getCountryPolicy, recommendMoments } from "./moment_catalog.js";
import { WIREGUARD_INSTALL_URL, detectBrowser, detectPlatform, getInstallGuidance, getPlatformProfile, getPlatformReadiness } from "./platform_support.js";
import { createPcPreferenceBackup, createRedactedPcDiagnostic, evaluatePcReadiness, sanitizePcPreferenceBackup } from "./pc_readiness.js";
import { createMobileRecoveryCard, evaluateMobileReadiness } from "./mobile_readiness.js";
import { createIncidentChecklist, createRedactedSupportBundle, evaluateCommercialReadiness } from "./commercial_readiness.js";

const apiMeta = document.querySelector('meta[name="freeflex-api-base"]');
const apiBase = apiMeta?.content?.trim() || "";
const root = document.documentElement;
const runtimeBanner = document.getElementById("runtimeBanner");
const setupBanner = document.getElementById("setupRuntimeBanner");
const createProfileButton = document.getElementById("createProfileButton");
const profilePanel = document.getElementById("profilePanel");
const profileConfig = document.getElementById("profileConfig");
const downloadProfileButton = document.getElementById("downloadProfileButton");
const serverCatalog = document.getElementById("serverCatalog");
const shareButton = document.getElementById("shareReferralButton");
const shareOutput = document.getElementById("shareReferralOutput");
const deviceList = document.getElementById("deviceList");
const deviceCount = document.getElementById("deviceCountValue");
const replacementGuard = document.getElementById("replacementGuard");
const replacementGuardCopy = document.getElementById("replacementGuardCopy");
const confirmReturnPathButton = document.getElementById("confirmReturnPathButton");
const currentCountrySelect = document.getElementById("currentCountrySelect");
const destinationCountrySelect = document.getElementById("destinationCountrySelect");
const momentCategorySelect = document.getElementById("momentCategorySelect");
const momentSearchInput = document.getElementById("momentSearchInput");
const countryPolicyBanner = document.getElementById("countryPolicyBanner");
const momentSummary = document.getElementById("momentRecommendationSummary");
const momentList = document.getElementById("momentRecommendationList");
const platformDetected = document.getElementById("platformDetected");
const platformPwaTitle = document.getElementById("platformPwaTitle");
const platformPwaCopy = document.getElementById("platformPwaCopy");
const platformWireguardCopy = document.getElementById("platformWireguardCopy");
const platformInstallButton = document.getElementById("platformInstallButton");
const platformInstallState = document.getElementById("platformInstallState");
const platformVpnState = document.getElementById("platformVpnState");
const wireguardInstallLink = document.getElementById("wireguardInstallLink");
const pcReadiness = document.querySelector("[data-pc-readiness]");
const pcReadinessBadge = document.querySelector("[data-pc-readiness-badge]");
const pcReadinessCopy = document.querySelector("[data-pc-readiness-copy]");
const pcConfirmationInputs = [...document.querySelectorAll("[data-pc-confirm]")];
const mobileReadiness = document.querySelector("[data-mobile-readiness]");
const mobileReadinessBadge = document.querySelector("[data-mobile-readiness-badge]");
const mobileReadinessCopy = document.querySelector("[data-mobile-readiness-copy]");
const mobileConfirmationInputs = [...document.querySelectorAll("[data-mobile-confirm]")];
let selectedServerId = null;
let activeDeviceId = null;
let candidateDeviceId = null;
let replacementPhase = "idle";
let lastDevicesPayload = null;
let currentConfig = null;
let availableServers = [];
let serverCatalogKnown = false;
let selectedTier = "all";
let pcProtectionState = "unverified";
const PC_ACK_KEY = "freeflex-pc-readiness-v1";
const MOBILE_ACK_KEY = "freeflex-mobile-readiness-v1";
const COMMERCIAL_DOCUMENTED = ["privacy-rights", "support-diagnostic", "rollback-playbook"];
const operationalNodes = {
  card: document.querySelector("[data-svc-operations-state]"),
  copy: document.querySelector("[data-svc-operations-copy]"),
  source: document.querySelector("[data-svc-operations-source]"),
  measured: document.querySelector("[data-svc-operations-measured]"),
  availability: document.querySelector("[data-svc-operations-availability]"),
  congestion: document.querySelector("[data-svc-operations-congestion]"),
  alternative: document.querySelector("[data-svc-alternative]"),
  usageGrid: document.querySelector("[data-svc-usage-state]"),
  usageSource: document.querySelector("[data-svc-usage-source]"),
  usageEmpty: document.querySelector("[data-svc-usage-empty]"),
  usageForecast: document.querySelector("[data-svc-usage-forecast]"),
  usageUpdated: document.querySelector("[data-svc-usage-updated]"),
};
const detectedPlatformId = detectPlatform({
  userAgent: navigator.userAgent,
  platform: navigator.platform,
  userAgentDataPlatform: navigator.userAgentData?.platform,
  maxTouchPoints: navigator.maxTouchPoints,
});
let selectedPlatformId = detectedPlatformId;
const detectedBrowserId = detectBrowser(navigator.userAgent);

function notify(message) {
  if (typeof globalThis.toast === "function") globalThis.toast(message);
}

function safeLocalRead(key) {
  try { return localStorage.getItem(key); } catch (_error) { return null; }
}

function safeLocalWrite(key, value) {
  try { localStorage.setItem(key, value); return true; } catch (_error) { return false; }
}

function readPcAcknowledgements() {
  try {
    const value = JSON.parse(safeLocalRead(PC_ACK_KEY) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch (_error) { return {}; }
}

function pcReadinessInput() {
  const acknowledgements = readPcAcknowledgements();
  return {
    secureContext: globalThis.isSecureContext === true,
    online: navigator.onLine !== false,
    apiMode: root.dataset.apiMode || "unconfigured",
    wireguardClientConfirmed: acknowledgements.wireguardClient === true,
    profileImportedConfirmed: acknowledgements.profileImport === true,
    protectionState: pcProtectionState,
    recoveryDrillConfirmed: acknowledgements.recoveryDrill === true && pcProtectionState === "protected",
  };
}

function renderPcReadiness() {
  if (!pcReadiness) return;
  const result = evaluatePcReadiness(pcReadinessInput());
  const details = {
    "secure-context": { pass: "브라우저 보안 연결 확인됨", fail: "HTTPS 연결 필요" },
    network: { pass: "브라우저 온라인", fail: "오프라인" },
    "service-api": { pass: "실제 서비스 API 응답", pending: "운영 API 연결 전" },
    "wireguard-client": { self_reported: "사용자가 설치 확인 · 자동 증거 아님", pending: "사용자 확인 전" },
    "profile-import": { self_reported: "사용자가 가져오기 확인 · 키는 읽지 않음", pending: "별도 PC 설정 필요" },
    protection: { pass: "서비스 보호 근거 확인", fail: "연결 끊김", pending: "실제 보호 근거 확인 전" },
    "recovery-drill": { self_reported: "보호 확인 뒤 일반망 복귀 자가 확인", pending: "실제 보호 확인 뒤 연습 가능" },
  };
  for (const check of result.checks) {
    const row = pcReadiness.querySelector(`[data-pc-check="${check.id}"]`);
    if (!row) continue;
    row.dataset.state = check.state;
    const detail = row.querySelector("small");
    if (detail) detail.textContent = details[check.id]?.[check.state] || "확인 전";
  }
  const acknowledgements = readPcAcknowledgements();
  for (const input of pcConfirmationInputs) {
    const key = input.dataset.pcConfirm === "wireguard-client" ? "wireguardClient" : input.dataset.pcConfirm === "profile-import" ? "profileImport" : "recoveryDrill";
    input.checked = acknowledgements[key] === true && (key !== "recoveryDrill" || pcProtectionState === "protected");
    if (key === "recoveryDrill") input.disabled = pcProtectionState !== "protected";
  }
  pcReadinessBadge.textContent = `${result.completedCount} / ${result.checks.length} · ${result.readyForCandidateReview ? "후보 검토 가능" : "준비 중"}`;
  pcReadinessCopy.textContent = result.readyForCandidateReview
    ? "이 브라우저의 로컬 점검은 끝났습니다. 실제 Windows VPN·운영·지원 증거를 별도 원장으로 확인해야 출시 후보가 됩니다."
    : "자동 확인과 자가 확인을 분리합니다. 파란 점은 사용자 확인이며 실제 상용 증거로 자동 승격되지 않습니다.";
}

function downloadJson(filename, value) {
  const blob = new Blob([`${JSON.stringify(value, null, 2)}\n`], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = filename; document.body.append(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

function browserFamily() {
  return detectedBrowserId === "chrome" || detectedBrowserId === "edge" ? "chromium" : detectedBrowserId;
}

function mobilePlatformFamily() {
  return detectedPlatformId === "android" || detectedPlatformId === "ios" ? detectedPlatformId : "other";
}

function readMobileAcknowledgements() {
  try {
    const value = JSON.parse(safeLocalRead(MOBILE_ACK_KEY) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch (_error) { return {}; }
}

function mobileReadinessInput() {
  const acknowledgements = readMobileAcknowledgements();
  return {
    platform: mobilePlatformFamily(),
    secureContext: globalThis.isSecureContext === true,
    online: navigator.onLine !== false,
    apiMode: root.dataset.apiMode || "unconfigured",
    standalone: globalThis.freeflexIsStandalone === true,
    wireguardClientConfirmed: acknowledgements.wireguardClient === true,
    profileImportedConfirmed: acknowledgements.profileImport === true,
    protectionState: pcProtectionState,
    recoveryDrillConfirmed: acknowledgements.recoveryDrill === true && pcProtectionState === "protected",
  };
}

function renderMobileReadiness() {
  if (!mobileReadiness) return;
  const result = evaluateMobileReadiness(mobileReadinessInput());
  const details = {
    "secure-context": { pass: "브라우저 보안 연결 확인됨", fail: "HTTPS 연결 필요" },
    network: { pass: "기기 온라인", fail: "오프라인 · 저장한 복구 카드 사용" },
    "service-api": { pass: "실제 서비스 API 응답", pending: "운영 API 연결 전" },
    "install-mode": { pass: "홈 화면 설치 모드", pending: "브라우저에서 실행 중" },
    "wireguard-client": { self_reported: "사용자가 공식 앱 확인 · 자동 증거 아님", pending: "사용자 확인 전" },
    "profile-import": { self_reported: "사용자가 별도 설정 확인 · 원문은 읽지 않음", pending: "별도 모바일 설정 필요" },
    protection: { pass: "서비스 보호 근거 확인", fail: "연결 끊김", pending: "실제 보호 근거 확인 전" },
    "recovery-drill": { self_reported: "보호 뒤 일반망 복귀 자가 확인", pending: "실제 보호 확인 뒤 연습 가능" },
  };
  for (const item of result.checks) {
    const row = mobileReadiness.querySelector(`[data-mobile-check="${item.id}"]`);
    if (!row) continue;
    row.dataset.state = item.state;
    const detail = row.querySelector("small");
    if (detail) detail.textContent = details[item.id]?.[item.state] || "확인 전";
  }
  const acknowledgements = readMobileAcknowledgements();
  for (const input of mobileConfirmationInputs) {
    const key = input.dataset.mobileConfirm === "wireguard-client" ? "wireguardClient" : input.dataset.mobileConfirm === "profile-import" ? "profileImport" : "recoveryDrill";
    input.checked = acknowledgements[key] === true && (key !== "recoveryDrill" || pcProtectionState === "protected");
    if (key === "recoveryDrill") input.disabled = pcProtectionState !== "protected";
  }
  if (mobileReadinessBadge) mobileReadinessBadge.textContent = `${result.completedCount} / ${result.checks.length} · ${result.readyForCandidateReview ? "후보 검토 가능" : "준비 중"}`;
  if (mobileReadinessCopy) mobileReadinessCopy.textContent = result.readyForCandidateReview
    ? "이 기기의 로컬 점검은 끝났습니다. Android·iPhone 실기기와 운영 증거를 별도로 확인해야 출시 후보가 됩니다."
    : "자동 확인과 자가 확인을 분리합니다. 자가 확인은 상용 증거로 자동 승격되지 않습니다.";
}

function renderCommercialReadiness() {
  const panel = document.querySelector("[data-commercial-readiness]");
  if (!panel) return;
  const result = evaluateCommercialReadiness({ documented: COMMERCIAL_DOCUMENTED });
  const details = {
    "privacy-rights": { documented: "로컬 자료 최소화·내보내기·삭제 경로 문서화" },
    "support-diagnostic": { documented: "민감정보 없는 지원 묶음 준비" },
    "rollback-playbook": { documented: "기존 설정 보존·일반망 복귀 절차 문서화" },
    "payment-roundtrip": { blocked: "실제 결제 왕복 없음" },
    "refund-roundtrip": { blocked: "실제 취소·환불 왕복 없음" },
    "legal-review": { blocked: "개인정보·약관 최종 법률 검토 전" },
    "operations-monitoring": { blocked: "독립 운영 감시·장애 훈련 전" },
    "limited-release": { blocked: "최신 후보 제한 공개·관찰 전" },
  };
  for (const item of result.checks) {
    const row = panel.querySelector(`[data-commercial-check="${item.id}"]`);
    if (!row) continue;
    row.dataset.state = item.state;
    const detail = row.querySelector("small");
    if (detail) detail.textContent = details[item.id]?.[item.state] || "외부 증거 확인 전";
  }
  const badge = panel.querySelector("[data-commercial-readiness-badge]");
  if (badge) badge.textContent = `${result.documentedCount} / ${result.checks.length} 문서화 · 실제 검증 ${result.verifiedCount}`;
}

function setBanner(element, strong, copy, state = "") {
  if (!element) return;
  element.dataset.runtimeState = state;
  element.replaceChildren();
  const title = document.createElement("strong");
  title.textContent = strong;
  element.append(title, document.createTextNode(` — ${copy}`));
}

function formatMeasuredAt(value) {
  const measured = new Date(value || "");
  if (Number.isNaN(measured.getTime())) return null;
  return measured.toLocaleString("ko-KR", { dateStyle: "short", timeStyle: "short" });
}

function renderOperationalState({ state, copy, source, measuredAt = null, available = null, congestion = null, alternative = null }) {
  const measured = formatMeasuredAt(measuredAt);
  if (operationalNodes.card) operationalNodes.card.dataset.svcOperationsState = state;
  if (operationalNodes.copy) operationalNodes.copy.textContent = copy;
  if (operationalNodes.source) operationalNodes.source.textContent = source;
  if (operationalNodes.measured) operationalNodes.measured.textContent = measured || "확인 전";
  if (operationalNodes.availability) operationalNodes.availability.textContent = available ?? "판정 불가";
  if (operationalNodes.congestion) operationalNodes.congestion.textContent = congestion ?? "판정 불가";
  if (operationalNodes.alternative && alternative) operationalNodes.alternative.innerHTML = `<strong>대안 경로</strong><br>${alternative}`;
}

function renderUsageEmptyState({ state, source, copy, updated = null }) {
  if (operationalNodes.usageGrid) operationalNodes.usageGrid.dataset.svcUsageState = state;
  if (operationalNodes.usageSource) operationalNodes.usageSource.textContent = source;
  if (operationalNodes.usageEmpty) operationalNodes.usageEmpty.innerHTML = `<b>${copy}</b><p>그래프, 남은 시간, 소진 예상은 실제 사용량과 갱신 시각이 확인된 뒤에만 표시합니다.</p>`;
  if (operationalNodes.usageForecast) operationalNodes.usageForecast.textContent = "계산 불가";
  if (operationalNodes.usageUpdated) operationalNodes.usageUpdated.textContent = formatMeasuredAt(updated) ? `갱신 시각 ${formatMeasuredAt(updated)}` : "갱신 시각 확인 전";
}

function readableError(error) {
  if (error instanceof FreeFlexApiError) return error.message;
  return "요청을 안전하게 완료하지 못했습니다.";
}

function destinationText(value) {
  if (value === "AUTO_NEAREST") return "가장 가까운 실제 서버";
  if (value === "ORG_DEFINED") return "회사 정책 지정";
  return value ? `목적지 ${value}` : "목적지 없음";
}

function recommendationStatus(item) {
  if (item.support === "not_supported") return "비지원";
  if (item.support === "specialized_required") return "전문 서비스 필요";
  if (item.support === "premium_planned") return "출시 예정";
  return item.actionable ? "서버 선택 가능" : "조건 확인 필요";
}

function applyRecommendation(item) {
  const server = item.destination === "AUTO_NEAREST"
    ? availableServers[0]
    : availableServers.find(candidate => String(candidate.country_code).toUpperCase() === item.destination);
  if (!item.actionable || !server) return;
  selectedServerId = server.server_id;
  serverCatalog?.querySelectorAll(".server").forEach(button => {
    button.classList.toggle("selected", button.dataset.serverId === server.server_id);
  });
  createProfileButton.disabled = !client?.vault.get();
  notify(`${item.title}: ${server.country} · ${server.city} 서버를 선택했습니다.`);
  globalThis.go?.("locations");
}

function renderMomentRecommendations() {
  if (!momentList) return;
  const result = recommendMoments({
    currentCountry: currentCountrySelect?.value,
    destinationCountry: destinationCountrySelect?.value,
    category: momentCategorySelect?.value || "all",
    tier: selectedTier,
    query: momentSearchInput?.value,
    availableCountryCodes: availableServers.map(server => server.country_code),
    catalogKnown: serverCatalogKnown,
  });
  const policy = getCountryPolicy(currentCountrySelect?.value);
  countryPolicyBanner.className = `country-policy ${policy.level === "normal" ? "" : policy.level}`.trim();
  countryPolicyBanner.textContent = currentCountrySelect?.value ? `${policy.name}: ${policy.notice}` : "현재 국가를 선택하면 현지 상황에 맞춘 주의사항을 보여줍니다.";
  momentSummary.textContent = `${result.total}개 순간 · 전체 ${MOMENTS.length}개`;
  momentList.replaceChildren();
  for (const item of result.recommendations) {
    const card = document.createElement("article"); card.className = "recommendation-card"; card.dataset.momentId = item.id;
    const header = document.createElement("header");
    const rank = document.createElement("span"); rank.className = "recommendation-rank"; rank.textContent = String(item.rank);
    const copy = document.createElement("div");
    const title = document.createElement("h3"); title.textContent = item.title;
    const why = document.createElement("p"); why.textContent = item.why;
    copy.append(title, why); header.append(rank, copy);
    const meta = document.createElement("div"); meta.className = "recommendation-meta";
    for (const value of [destinationText(item.destination), TIER_LABELS[item.tier], recommendationStatus(item)]) {
      const chip = document.createElement("span"); chip.textContent = value; meta.append(chip);
    }
    const button = document.createElement("button"); button.type = "button"; button.disabled = !item.actionable;
    button.textContent = item.actionable ? "이 추천으로 실제 서버 선택" : item.actionReason;
    button.addEventListener("click", () => applyRecommendation(item));
    card.append(header, meta, button); momentList.append(card);
  }
}

function renderPlatformSupport(platformId = selectedPlatformId) {
  if (!platformDetected) return;
  selectedPlatformId = platformId;
  const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  const readiness = getPlatformReadiness({
    platformId,
    standalone,
    serverReady: availableServers.length > 0,
    authenticated: Boolean(client?.vault.get()),
  });
  const profile = getPlatformProfile(platformId);
  const guidance = getInstallGuidance(platformId, detectedBrowserId);
  platformDetected.textContent = `${getPlatformProfile(detectedPlatformId).label}${platformId === detectedPlatformId ? " · 자동 감지" : ` · ${profile.label} 선택`}`;
  platformPwaTitle.textContent = profile.installLabel;
  platformPwaCopy.textContent = guidance.copy;
  platformWireguardCopy.textContent = profile.wireguard;
  platformInstallButton.textContent = standalone ? "이미 이 기기에 설치됨" : profile.installLabel;
  platformInstallButton.disabled = standalone;
  platformInstallState.textContent = standalone ? "설치됨" : "브라우저 설치 지원에 따라 가능";
  platformVpnState.textContent = readiness.vpnConfig === "available" ? "이 기기 구성 발급 가능" : readiness.vpnConfig === "login_required" ? "로그인 필요" : "실제 서버 필요";
  wireguardInstallLink.href = WIREGUARD_INSTALL_URL;
  document.querySelectorAll("[data-platform]").forEach(button => button.classList.toggle("active", button.dataset.platform === platformId));
}

function renderCatalog(payload) {
  const servers = Array.isArray(payload?.servers) ? payload.servers : [];
  availableServers = servers;
  serverCatalogKnown = true;
  serverCatalog.dataset.serverCount = String(servers.length);
  const measuredAt = payload?.measured_at || null;
  const staleAfterSeconds = Number(payload?.stale_after_seconds || 0);
  const measuredAgeSeconds = measuredAt ? Math.max(0, (Date.now() - new Date(measuredAt).getTime()) / 1000) : Number.POSITIVE_INFINITY;
  const stale = !measuredAt || !Number.isFinite(measuredAgeSeconds) || (staleAfterSeconds > 0 && measuredAgeSeconds > staleAfterSeconds);
  if (stale) {
    renderOperationalState({
      state: "stale", source: "서버 자료", measuredAt,
      copy: "서버 자료의 갱신 시각이 없거나 유효 기간을 지났습니다. 연결 가능 여부를 표시하지 않습니다.",
      alternative: "오래된 자료로는 대안을 추천하지 않습니다. 새 점검 결과가 필요합니다.",
    });
  } else if (!servers.length) {
    renderOperationalState({
      state: "empty", source: "서버 자료", measuredAt,
      copy: "현재 유효한 가동 서버가 없습니다. 연결을 시작하거나 혼잡도를 추정하지 않습니다.",
      available: "0대", congestion: "판정 대상 없음",
      alternative: "검증된 대안 경로가 없습니다. 새 서버 점검이 끝난 뒤 다시 확인하세요.",
    });
  } else {
    const highestCapacity = Math.max(...servers.map(server => Number(server.capacity_percent) || 0));
    renderOperationalState({
      state: "live", source: "서버 자료", measuredAt,
      copy: "검증된 서버 자료를 받았습니다. 실제 선택지는 아래 목록에서 고르세요.",
      available: `${servers.length}대`, congestion: highestCapacity >= 85 ? "혼잡 가능" : "정상 범위",
      alternative: servers.length > 1 ? `${servers.length - 1}개 대안 경로를 함께 표시합니다.` : "검증된 대안 경로는 아직 1개뿐입니다.",
    });
  }
  serverCatalog.replaceChildren();
  if (!servers.length) {
    serverCatalog.className = "empty-catalog";
    const icon = document.createElement("span"); icon.className = "flag"; icon.textContent = "∅";
    const title = document.createElement("b"); title.textContent = "현재 가동 서버가 없습니다";
    const copy = document.createElement("p"); copy.textContent = "실제 health 확인을 통과한 서버가 생길 때까지 연결을 시작하지 않습니다.";
    serverCatalog.append(icon, title, copy);
    selectedServerId = null;
    renderMomentRecommendations();
    renderPlatformSupport();
    return;
  }
  serverCatalog.className = "server-list runtime-server-list";
  for (const [index, server] of servers.entries()) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `server${index === 0 ? " selected" : ""}`;
    button.dataset.serverId = server.server_id;
    const flag = document.createElement("span"); flag.className = "flag"; flag.textContent = server.country_code;
    const grow = document.createElement("span"); grow.className = "grow";
    const title = document.createElement("b"); title.textContent = `${server.country} · ${server.city}`;
    const detail = document.createElement("small"); detail.textContent = `${server.health} · 용량 ${server.capacity_percent}% 사용`;
    const radio = document.createElement("span"); radio.className = "radio";
    grow.append(title, detail); button.append(flag, grow, radio);
    button.addEventListener("click", () => {
      serverCatalog.querySelectorAll(".server").forEach(item => item.classList.toggle("selected", item === button));
      selectedServerId = server.server_id;
      createProfileButton.disabled = !client?.vault.get();
      notify(`${title.textContent} 서버를 선택했습니다.`);
    });
    serverCatalog.append(button);
  }
  selectedServerId = servers[0].server_id;
  renderMomentRecommendations();
  renderPlatformSupport();
}

function renderWallet(wallet) {
  const balances = wallet?.balances;
  if (!balances) return;
  const total = bytesToGb(wallet.total_available_bytes);
  document.getElementById("balanceValue").textContent = total;
  document.querySelector('[data-wallet-bucket="free"] b').textContent = `${bytesToGb(balances.free)}GB`;
  document.querySelector('[data-wallet-bucket="earned"] b').textContent = `${bytesToGb(balances.earned)}GB`;
  document.querySelector('[data-wallet-bucket="paid"] b').textContent = `${bytesToGb(balances.paid)}GB`;
  document.querySelector('[data-wallet-view="free"] strong').textContent = `${bytesToGb(balances.free)}GB`;
  document.querySelector('[data-wallet-view="earned"] strong').textContent = `${bytesToGb(balances.earned)}GB`;
  document.querySelector('[data-wallet-view="paid"] strong').textContent = `${bytesToGb(balances.paid)}GB`;
  document.getElementById("usageEarned").textContent = `${bytesToGb(balances.earned)}GB`;
  document.getElementById("usagePaid").textContent = `${bytesToGb(balances.paid)}GB`;
  document.getElementById("topupCurrent").textContent = `${bytesToGb(balances.paid)}GB`;
  document.getElementById("walletTotalValue").textContent = total;
  document.getElementById("walletRuntimeBanner").innerHTML = "<strong>실제 계정 잔액</strong> — 제어 API 원장과 동기화됐습니다.";
  document.querySelector("[data-svc-usage-free]").textContent = `${bytesToGb(balances.free)}GB`;
  document.querySelector("[data-svc-usage-earned]").textContent = `${bytesToGb(balances.earned)}GB`;
  document.querySelector("[data-svc-usage-paid]").textContent = `${bytesToGb(balances.paid)}GB`;
  renderUsageEmptyState({ state: "wallet-live", source: "잔액 원장 확인됨", copy: "최근 7일 사용량 자료는 아직 받지 않았습니다." });
}

function renderReplacementGuard() {
  if (!replacementGuard || !replacementGuardCopy || !confirmReturnPathButton) return;
  replacementGuard.dataset.replacementState = replacementPhase;
  const copy = {
    idle: "새 구성을 만들더라도 기존 WireGuard 설정은 자동으로 지우거나 바꾸지 않습니다.",
    candidate_unverified: "새 후보를 WireGuard에서 직접 켠 뒤 보호 확인을 실행하세요. 기존 설정은 계속 보존됩니다.",
    candidate_live_verified: "후보의 터널·외부 경로·서버 악수·DNS가 확인됐습니다. 후보를 직접 끄고 일반 웹이 돌아온 뒤 아래 확인을 누르세요.",
    ready_to_replace: "후보 연결과 일반망 복귀를 각각 확인했습니다. 기존 설정 폐기는 여전히 마지막 확인 뒤에만 실행됩니다.",
    replacement_completed: "기존 설정 폐기 요청을 보냈습니다. 새 후보의 실제 연결 상태를 다시 확인하세요.",
  };
  replacementGuardCopy.textContent = copy[replacementPhase] || copy.idle;
  confirmReturnPathButton.hidden = !candidateDeviceId;
  confirmReturnPathButton.disabled = replacementPhase !== "candidate_live_verified";
}

function candidateRuntimeEvidencePassed(result) {
  const checks = result?.checks || {};
  return result?.state === "protected" && ["tunnel", "exit_ip", "handshake", "server", "dns"].every(name => checks[name] === true);
}

function chooseActiveDevice(devices) {
  const activeIds = devices.filter(device => device.status === "active").map(device => device.device_id);
  if (candidateDeviceId && activeIds.includes(candidateDeviceId)) return candidateDeviceId;
  if (activeDeviceId && activeIds.includes(activeDeviceId)) return activeDeviceId;
  return activeIds.length === 1 ? activeIds[0] : null;
}

function canRevokeDevice(deviceId) {
  if (deviceId === candidateDeviceId) return true;
  return Boolean(candidateDeviceId && replacementPhase === "ready_to_replace");
}

function renderDevices(payload) {
  const devices = Array.isArray(payload?.devices) ? payload.devices : [];
  lastDevicesPayload = payload;
  deviceCount.textContent = `${payload.active_count || 0} / ${payload.active_limit || 2}`;
  deviceList.replaceChildren();
  activeDeviceId = chooseActiveDevice(devices);
  if (!devices.length) {
    deviceList.className = "empty-catalog";
    deviceList.innerHTML = '<span class="flag">▯</span><b>등록된 기기가 없습니다</b><p>서버를 고른 뒤 이 기기에서 새 키를 만들 수 있습니다.</p>';
    return;
  }
  deviceList.className = "state-legend";
  for (const device of devices) {
    const row = document.createElement("div"); row.className = "state-row";
    row.dataset.deviceId = device.device_id;
    row.dataset.deviceRole = device.device_id === candidateDeviceId ? "candidate" : "existing";
    const dot = document.createElement("i");
    const content = document.createElement("div");
    const role = device.device_id === candidateDeviceId ? "새 교체 후보" : "기존 설정";
    const title = document.createElement("b"); title.textContent = `${role} · ${device.server_id} · ${device.status}`;
    const detail = document.createElement("small"); detail.textContent = `식별자 ${device.device_id.slice(0, 8)} · 주소와 키는 표시하지 않음`;
    content.append(title, detail); row.append(dot, content);
    if (device.status === "active") {
      const revoke = document.createElement("button"); revoke.type = "button"; revoke.className = "text-btn";
      const allowed = canRevokeDevice(device.device_id);
      revoke.disabled = !allowed;
      revoke.textContent = device.device_id === candidateDeviceId ? "후보 폐기" : (allowed ? "기존 설정 폐기" : "후보 확인 전 보존");
      revoke.addEventListener("click", async () => {
        if (!canRevokeDevice(device.device_id)) { notify("후보 연결과 일반망 복귀를 먼저 확인하세요. 기존 설정은 보존됩니다."); return; }
        const isCandidate = device.device_id === candidateDeviceId;
        const accepted = globalThis.confirm(isCandidate
          ? "새 교체 후보만 폐기합니다. 기존 설정은 보존됩니다. 계속할까요?"
          : "기존 설정 폐기는 되돌릴 수 없습니다. 후보 연결과 일반망 복귀를 모두 직접 확인했습니까?");
        if (!accepted) { notify("폐기를 취소했습니다. 설정은 그대로 보존됩니다."); return; }
        revoke.disabled = true;
        try {
          await client.revokeDevice(device.device_id);
          if (isCandidate) { candidateDeviceId = null; replacementPhase = "idle"; activeDeviceId = null; }
          else replacementPhase = "replacement_completed";
          await syncAccount(); renderReplacementGuard(); notify("기기 폐기 상태를 확인했습니다.");
        }
        catch (error) { notify(readableError(error)); revoke.disabled = false; }
      });
      row.append(revoke);
    }
    deviceList.append(row);
  }
}

function setConnectionFromResult(result) {
  const state = ["setup_needed", "checking", "protected", "limited", "disconnected"].includes(result?.state)
    ? result.state : "limited";
  pcProtectionState = state;
  renderPcReadiness();
  renderMobileReadiness();
  globalThis.setConnectionState?.(state);
  const checks = result?.checks || {};
  if (activeDeviceId && activeDeviceId === candidateDeviceId && candidateRuntimeEvidencePassed(result)) {
    replacementPhase = "candidate_live_verified";
    renderReplacementGuard();
  }
  globalThis.dispatchEvent(new CustomEvent("freeflex:protection-evidence", {
    detail: {
      state,
      checks: {
        tunnel: checks.tunnel,
        exit_ip: checks.exit_ip,
        dns: checks.dns,
        ipv6: checks.ipv6,
        kill_switch: checks.kill_switch,
      },
      checked_at: result?.checked_at || null,
    },
  }));
  const map = {
    tunnel: checks.tunnel,
    "exit-ip": checks.exit_ip,
    dns: checks.dns,
    ipv6: checks.ipv6,
    "kill-switch": checks.kill_switch,
    "checked-at": result.checked_at,
  };
  for (const [name, value] of Object.entries(map)) {
    const row = document.querySelector(`[data-check="${name}"]`);
    if (!row) continue;
    row.dataset.pass = value === true || (name === "checked-at" && Boolean(value)) ? "true" : "false";
    const detail = row.querySelector("small");
    detail.textContent = name === "checked-at" ? (value || "확인 성공 기록 없음") : (value === true ? "확인됨" : "확인되지 않음");
  }
}

async function syncAccount() {
  const [wallet, devices] = await Promise.all([client.wallet(), client.devices()]);
  renderWallet(wallet); renderDevices(devices);
  try {
    renderUsage(await client.usage());
  } catch (_error) {
    renderUsage({ sessions: [] });
  }
}

function renderUsage(payload) {
  const sessions = Array.isArray(payload?.sessions) ? payload.sessions : [];
  const updated = sessions[0]?.updated_at || null;
  renderUsageEmptyState({
    state: sessions.length ? "usage-live" : "usage-empty",
    source: sessions.length ? "사용량 원장 확인됨" : "사용량 원장에 기록 없음",
    copy: sessions.length ? "사용량 기록을 받았지만, 7일 차트와 소진 예상은 다음 화면 묶음에서 완성합니다." : "아직 사용량 기록이 없어 소진 예상도 계산하지 않습니다.",
    updated,
  });
}

async function createProfile() {
  if (!selectedServerId || !client.vault.get()) return;
  createProfileButton.disabled = true;
  setBanner(setupBanner, "기기 키 생성 중", "개인키는 이 브라우저 메모리 안에서만 사용합니다.", "working");
  try {
    const profile = await createDeviceProfile({
      serverId: selectedServerId,
      registerPublicKeyImpl: (publicKey, serverId) => client.registerDevice(publicKey, serverId),
    });
    currentConfig = profile.config;
    profileConfig.value = profile.config;
    profilePanel.hidden = false;
    activeDeviceId = profile.deviceId;
    candidateDeviceId = profile.deviceId;
    replacementPhase = "candidate_unverified";
    renderReplacementGuard();
    setBanner(setupBanner, "기기 구성 준비됨", "아래 파일을 이 기기에 저장해 공식 WireGuard 앱으로 가져오세요.", "ready");
    syncAccount().catch(() => notify("구성은 준비됐지만 기기 목록 새로고침은 다음 연결에서 다시 시도합니다."));
  } catch (error) {
    setBanner(setupBanner, "구성 생성 중단", readableError(error), "error");
    createProfileButton.disabled = false;
  }
}

function downloadProfile() {
  if (!currentConfig) return;
  const blob = new Blob([currentConfig], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = `FreeFlexVPN-${selectedServerId || "device"}.conf`; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

let client = null;

async function initialize() {
  if (!apiBase) {
    root.dataset.apiMode = "unconfigured";
    renderOperationalState({ state: "unconfigured", source: "연결 전", copy: "운영 서버 자료가 아직 연결되지 않았습니다. 연결 가능 여부와 혼잡도는 판단하지 않습니다.", alternative: "현재 검증된 가동 서버 목록이 없으므로 대안을 추천하지 않습니다. 자료가 연결된 뒤에만 실제 선택지를 표시합니다." });
    renderUsageEmptyState({ state: "unconfigured", source: "자료 연결 전", copy: "사용량 원장을 아직 받지 못했습니다" });
    return;
  }
  root.dataset.apiMode = "connecting";
  try {
    client = new FreeFlexApiClient({ apiBase });
    const launch = await consumeLaunchParameters(client);
    const catalog = await client.catalog();
    renderCatalog(catalog);
    root.dataset.apiMode = "live";
    setBanner(runtimeBanner, "실제 서버 API 연결", `${catalog.available_count || 0}대가 health 확인을 통과했습니다.`, "live");
    const cryptoReady = await supportsBrowserX25519();
    const topup = document.getElementById("topupButton");
    if (topup) { topup.disabled = true; topup.textContent = "실제 결제 기능 준비 전"; }
    if (!cryptoReady) setBanner(setupBanner, "브라우저 키 생성 미지원", manualFallback.message, "unsupported");
    if (client.vault.get()) {
      await syncAccount();
      createProfileButton.disabled = !cryptoReady || !selectedServerId;
      setBanner(setupBanner, "로그인 확인됨", client.vault.persistence === "session" ? "이 탭 세션 동안만 인증을 보관합니다." : "브라우저 저장이 차단되어 새로고침하면 다시 로그인해야 합니다.", "authenticated");
      shareButton.disabled = false;
      const addDevice = document.getElementById("addDeviceButton");
      if (addDevice) addDevice.disabled = false;
      renderPlatformSupport();
    } else {
      setBanner(setupBanner, "로그인 수령 링크 필요", "Telegram에서 받은 10분 링크로 들어오면 기기 구성을 만들 수 있습니다.", "auth-required");
    }
    if (launch.exchanged) notify("안전한 일회용 수령 링크를 확인했습니다.");
  } catch (error) {
    root.dataset.apiMode = "unavailable";
    setBanner(runtimeBanner, "서버 API 연결 안 됨", readableError(error), "error");
    setBanner(setupBanner, "설정 생성 불가", "API가 다시 확인될 때까지 개인키나 가짜 구성을 만들지 않습니다.", "error");
    renderOperationalState({ state: "error", source: "서버 자료 연결 실패", copy: "운영 자료를 받지 못했습니다. 이전 값이나 추정값으로 연결 가능 여부를 표시하지 않습니다.", alternative: "오류가 해소되어 새 서버 점검 자료를 받을 때까지 대안을 추천하지 않습니다." });
    renderUsageEmptyState({ state: "error", source: "사용량 원장 연결 실패", copy: "사용량 자료를 받지 못했습니다" });
  }
}

createProfileButton?.addEventListener("click", createProfile);
downloadProfileButton?.addEventListener("click", downloadProfile);
confirmReturnPathButton?.addEventListener("click", () => {
  if (!candidateDeviceId || replacementPhase !== "candidate_live_verified") return;
  replacementPhase = "ready_to_replace";
  renderReplacementGuard();
  if (lastDevicesPayload) renderDevices(lastDevicesPayload);
  notify("일반망 복귀 확인을 기록했습니다. 기존 설정은 아직 보존 중입니다.");
});
window.addEventListener("freeflex:check-protection", async () => {
  if (!client) return;
  try { setConnectionFromResult(await client.check(activeDeviceId)); }
  catch (error) { globalThis.setConnectionState?.("limited"); notify(readableError(error)); }
});
shareButton?.addEventListener("click", async () => {
  shareButton.disabled = true;
  try {
    const issued = await client.issueReferral();
    shareOutput.value = issued.share_url;
    shareOutput.hidden = false;
    if (navigator.share) await navigator.share({ title: "FreeFlexVPN", text: "필요할 때만 쓰는 VPN — 둘 다 500MB 받기", url: issued.share_url });
    else if (navigator.clipboard) { await navigator.clipboard.writeText(issued.share_url); notify("추천 링크를 복사했습니다."); }
  } catch (error) { notify(readableError(error)); }
  finally { shareButton.disabled = false; }
});
document.getElementById("addDeviceButton")?.addEventListener("click", () => globalThis.go?.("setup"));
for (const input of pcConfirmationInputs) {
  input.addEventListener("change", () => {
    const acknowledgements = readPcAcknowledgements();
    const key = input.dataset.pcConfirm === "wireguard-client" ? "wireguardClient" : input.dataset.pcConfirm === "profile-import" ? "profileImport" : "recoveryDrill";
    if (key === "recoveryDrill" && pcProtectionState !== "protected") { input.checked = false; notify("실제 보호 근거가 확인된 뒤에만 일반망 복귀 연습을 기록할 수 있습니다."); return; }
    acknowledgements[key] = input.checked;
    safeLocalWrite(PC_ACK_KEY, JSON.stringify(acknowledgements));
    renderPcReadiness();
  });
}
for (const input of mobileConfirmationInputs) {
  input.addEventListener("change", () => {
    const acknowledgements = readMobileAcknowledgements();
    const key = input.dataset.mobileConfirm === "wireguard-client" ? "wireguardClient" : input.dataset.mobileConfirm === "profile-import" ? "profileImport" : "recoveryDrill";
    if (key === "recoveryDrill" && pcProtectionState !== "protected") { input.checked = false; notify("실제 보호 근거가 확인된 뒤에만 일반망 복귀 연습을 기록할 수 있습니다."); return; }
    acknowledgements[key] = input.checked;
    safeLocalWrite(MOBILE_ACK_KEY, JSON.stringify(acknowledgements));
    renderMobileReadiness();
  });
}
document.querySelector("[data-mobile-download-recovery]")?.addEventListener("click", () => {
  downloadJson("FreeFlexVPN-mobile-offline-recovery.json", createMobileRecoveryCard({ platform: mobilePlatformFamily() }));
  notify("개인 설정·IP·계정 정보가 없는 오프라인 복구 카드를 저장했습니다.");
});
document.querySelector("[data-commercial-download-support]")?.addEventListener("click", () => {
  downloadJson("FreeFlexVPN-redacted-support-bundle.json", createRedactedSupportBundle({
    generatedAt: new Date().toISOString(),
    platformFamily: ["android", "ios", "windows", "macos", "linux"].includes(detectedPlatformId) ? detectedPlatformId : "other",
    browserFamily: browserFamily(),
    online: navigator.onLine !== false,
    standalone: globalThis.freeflexIsStandalone === true,
    apiMode: root.dataset.apiMode || "unconfigured",
    protectionState: pcProtectionState,
    commercial: { documented: COMMERCIAL_DOCUMENTED },
  }));
  notify("IP·키·설정·계정·결제수단을 제외한 지원 묶음을 저장했습니다.");
});
document.querySelector("[data-commercial-download-incident]")?.addEventListener("click", () => {
  downloadJson("FreeFlexVPN-incident-checklist.json", createIncidentChecklist({ platform: innerWidth <= 760 ? "mobile" : "pc" }));
  notify("삭제·덮어쓰기 없는 장애 복구 체크리스트를 저장했습니다.");
});
document.querySelector("[data-pc-download-diagnostic]")?.addEventListener("click", () => {
  const diagnostic = createRedactedPcDiagnostic({
    ...pcReadinessInput(),
    generatedAt: new Date().toISOString(),
    browserFamily: browserFamily(),
    platformFamily: ["windows", "macos", "linux"].includes(detectedPlatformId) ? detectedPlatformId : "other",
    standalone: globalThis.freeflexIsStandalone === true,
  });
  downloadJson("FreeFlexVPN-PC-redacted-diagnostic.json", diagnostic);
  notify("IP·개인키·설정·방문 기록을 제외한 진단을 이 PC에 저장했습니다.");
});
document.querySelector("[data-pc-export-preferences]")?.addEventListener("click", () => {
  let accessibility = {};
  try { accessibility = JSON.parse(safeLocalRead("freeflex-accessibility-v1") || "{}"); } catch (_error) { accessibility = {}; }
  downloadJson("FreeFlexVPN-PC-reading-preferences.json", createPcPreferenceBackup({
    accessibility,
    focusMode: safeLocalRead("freeflex-pc-focus-v1") === "true",
  }));
  notify("글씨·고대비·집중 보기만 백업했습니다. VPN 설정과 계정 정보는 포함하지 않습니다.");
});
document.querySelector("[data-pc-import-preferences]")?.addEventListener("change", async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const backup = sanitizePcPreferenceBackup(JSON.parse(await file.text()));
    safeLocalWrite("freeflex-accessibility-v1", JSON.stringify(backup.accessibility));
    safeLocalWrite("freeflex-pc-focus-v1", String(backup.focusMode));
    globalThis.dispatchEvent(new CustomEvent("freeflex:restore-reading-preferences", { detail: backup }));
    notify("읽기 설정을 복원해 바로 적용했습니다.");
  } catch (_error) { notify("지원하는 FreeFlexVPN 읽기 설정 백업 파일이 아닙니다."); }
  event.target.value = "";
});
new MutationObserver(renderPcReadiness).observe(root, { attributes: true, attributeFilter: ["data-api-mode"] });
new MutationObserver(renderMobileReadiness).observe(root, { attributes: true, attributeFilter: ["data-api-mode"] });
window.addEventListener("online", () => { renderPcReadiness(); renderMobileReadiness(); });
window.addEventListener("offline", () => { renderPcReadiness(); renderMobileReadiness(); });
for (const control of [currentCountrySelect, destinationCountrySelect, momentCategorySelect]) {
  control?.addEventListener("change", renderMomentRecommendations);
}
momentSearchInput?.addEventListener("input", renderMomentRecommendations);
document.querySelectorAll("[data-tier-filter]").forEach(button => button.addEventListener("click", () => {
  selectedTier = button.dataset.tierFilter || "all";
  document.querySelectorAll("[data-tier-filter]").forEach(item => item.classList.toggle("active", item === button));
  renderMomentRecommendations();
}));
document.querySelectorAll("[data-platform]").forEach(button => button.addEventListener("click", () => renderPlatformSupport(button.dataset.platform)));
platformInstallButton?.addEventListener("click", async () => {
  const installed = await globalThis.freeflexRequestInstall?.();
  if (installed) renderPlatformSupport();
  else globalThis.freeflexShowInstallHelp?.();
});

renderMomentRecommendations();
renderPlatformSupport();
renderReplacementGuard();
renderPcReadiness();
renderMobileReadiness();
renderCommercialReadiness();
initialize();
