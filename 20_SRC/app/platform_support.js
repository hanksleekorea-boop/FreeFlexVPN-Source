export const PLATFORM_SUPPORT_VERSION = "2026-08-02.1";
export const WIREGUARD_INSTALL_URL = "https://www.wireguard.com/install/";

export const BROWSER_PROFILES = Object.freeze({
  edge: Object.freeze({ id: "edge", label: "Microsoft Edge" }),
  chrome: Object.freeze({ id: "chrome", label: "Chrome" }),
  safari: Object.freeze({ id: "safari", label: "Safari" }),
  firefox: Object.freeze({ id: "firefox", label: "Firefox" }),
  other: Object.freeze({ id: "other", label: "현재 브라우저" }),
});

const profiles = {
  windows: {
    id: "windows", label: "Windows PC", icon: "▣", deviceClass: "desktop",
    pwa: "Chrome 또는 Edge의 주소창 설치 아이콘으로 FreeFlexVPN을 PC 앱처럼 설치하세요.",
    wireguard: "공식 WireGuard Windows 앱을 설치한 뒤 FreeFlexVPN에서 받은 .conf 파일을 가져옵니다.",
    installLabel: "PC에 FreeFlexVPN 설치",
  },
  macos: {
    id: "macos", label: "Mac", icon: "◇", deviceClass: "desktop",
    pwa: "Safari의 Dock에 추가 또는 Chrome의 설치 메뉴로 FreeFlexVPN을 앱처럼 사용하세요.",
    wireguard: "공식 WireGuard macOS 앱을 설치한 뒤 이 기기 전용 구성을 가져옵니다.",
    installLabel: "Mac에 FreeFlexVPN 설치",
  },
  linux: {
    id: "linux", label: "Linux PC", icon: "▤", deviceClass: "desktop",
    pwa: "지원되는 Chromium 계열 브라우저의 설치 메뉴로 FreeFlexVPN을 독립 창에서 사용하세요.",
    wireguard: "배포판의 공식 패키지로 WireGuard를 설치하고 이 기기 전용 구성을 적용합니다.",
    installLabel: "Linux에 FreeFlexVPN 설치",
  },
  android: {
    id: "android", label: "Android", icon: "▯", deviceClass: "mobile",
    pwa: "브라우저 메뉴의 앱 설치 또는 홈 화면에 추가를 선택하세요.",
    wireguard: "공식 WireGuard Android 앱에서 이 기기 전용 구성을 가져옵니다.",
    installLabel: "Android 홈 화면에 설치",
  },
  ios: {
    id: "ios", label: "iPhone · iPad", icon: "▭", deviceClass: "mobile",
    pwa: "브라우저 공유 메뉴에서 홈 화면에 추가를 선택하세요.",
    wireguard: "App Store의 공식 WireGuard 앱에서 이 기기 전용 구성을 가져옵니다.",
    installLabel: "iPhone 홈 화면에 설치",
  },
};

export const PLATFORM_PROFILES = Object.freeze(Object.fromEntries(
  Object.entries(profiles).map(([key, value]) => [key, Object.freeze(value)]),
));

export function detectPlatform(input = {}) {
  const ua = String(input.userAgent || "").toLowerCase();
  const platform = String(input.platform || input.userAgentDataPlatform || "").toLowerCase();
  const touchPoints = Number(input.maxTouchPoints || 0);
  if (/iphone|ipad|ipod/.test(ua) || (platform.includes("mac") && touchPoints > 1)) return "ios";
  if (ua.includes("android")) return "android";
  if (platform.includes("win") || ua.includes("windows")) return "windows";
  if (platform.includes("mac") || ua.includes("macintosh")) return "macos";
  if (platform.includes("linux") || ua.includes("linux")) return "linux";
  return "windows";
}

export function getPlatformProfile(id = "") {
  return PLATFORM_PROFILES[id] || PLATFORM_PROFILES.windows;
}

export function detectBrowser(userAgent = "") {
  const ua = String(userAgent).toLowerCase();
  if (/edg\//.test(ua)) return "edge";
  if (/(chrome|crios)\//.test(ua) && !/edg\//.test(ua)) return "chrome";
  if (/firefox|fxios/.test(ua)) return "firefox";
  if (/safari\//.test(ua) && !/(chrome|crios|android)/.test(ua)) return "safari";
  return "other";
}

export function getInstallGuidance(platformId = "", browserId = "") {
  const platform = getPlatformProfile(platformId);
  const browser = BROWSER_PROFILES[browserId] || BROWSER_PROFILES.other;
  let mode = "browser_ui";
  let copy = platform.pwa;
  if (platform.id === "ios") copy = `${browser.label}의 공유 메뉴에서 홈 화면에 추가를 선택하세요.`;
  else if (platform.id === "macos" && browser.id === "safari") copy = "Safari의 파일 메뉴에서 Dock에 추가를 선택하세요.";
  else if (platform.deviceClass === "desktop" && browser.id === "firefox") {
    mode = "web_fallback";
    copy = "Firefox에서는 설치 버튼이 보이지 않을 수 있습니다. 웹으로 계속 사용하거나 Chrome·Edge·Safari의 앱 설치 기능을 이용하세요.";
  } else if (browser.id === "chrome" || browser.id === "edge") {
    mode = "install_prompt";
    copy = `${browser.label}의 주소창 설치 아이콘이나 이 화면의 설치 버튼을 사용하세요.`;
  }
  return Object.freeze({ platform, browser, mode, copy });
}

export function getPlatformReadiness(options = {}) {
  const profile = getPlatformProfile(options.platformId);
  const standalone = options.standalone === true;
  const serverReady = options.serverReady === true;
  const authenticated = options.authenticated === true;
  return Object.freeze({
    profile,
    webApp: standalone ? "installed" : "installable",
    vpnConfig: serverReady && authenticated ? "available" : serverReady ? "login_required" : "server_required",
    canIssueConfig: serverReady && authenticated,
    truth: "웹앱은 계정·잔액·추천·설정을 관리하고 실제 VPN 터널은 운영체제의 공식 WireGuard 앱이 실행합니다.",
  });
}
