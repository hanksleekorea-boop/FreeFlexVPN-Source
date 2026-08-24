/** FreeFlexVPN PWA control-plane client. Tokens remain in memory/session scope. */

const TOKEN_KEY = "ffvpn-session-v1";
const API_TIMEOUT_MS = 12_000;

export class FreeFlexApiError extends Error {
  constructor(code, status, message) {
    super(message || "요청을 완료하지 못했습니다.");
    this.name = "FreeFlexApiError";
    this.code = code || "API_ERROR";
    this.status = Number(status || 0);
  }
}

export class SessionVault {
  constructor(storage) {
    this.storage = null;
    this.memoryToken = null;
    this.persistence = "memory";
    try {
      this.storage = storage === undefined ? globalThis.sessionStorage : storage;
      const stored = this.storage?.getItem(TOKEN_KEY);
      if (stored) this.memoryToken = stored;
      if (this.storage) this.persistence = "session";
    } catch (_error) {
      this.storage = null;
      this.persistence = "memory";
    }
  }

  get() { return this.memoryToken; }

  set(token) {
    if (typeof token !== "string" || token.length < 32) throw new Error("SESSION_TOKEN_INVALID");
    this.memoryToken = token;
    try {
      this.storage?.setItem(TOKEN_KEY, token);
      if (this.storage) this.persistence = "session";
    } catch (_error) {
      this.persistence = "memory";
    }
    return this.persistence;
  }

  clear() {
    this.memoryToken = null;
    try { this.storage?.removeItem(TOKEN_KEY); } catch (_error) { /* memory was cleared */ }
  }
}

function validateApiBase(value) {
  let url;
  try { url = new URL(value); } catch (_error) { throw new Error("API_BASE_INVALID"); }
  if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash) {
    throw new Error("HTTPS_API_BASE_REQUIRED");
  }
  return url.href.replace(/\/$/, "");
}

export class FreeFlexApiClient {
  constructor({ apiBase, fetchImpl = globalThis.fetch, vault = new SessionVault(), timeoutMs = API_TIMEOUT_MS }) {
    this.apiBase = validateApiBase(apiBase);
    if (typeof fetchImpl !== "function") throw new Error("FETCH_UNAVAILABLE");
    if (!Number.isInteger(timeoutMs) || timeoutMs < 1_000 || timeoutMs > 30_000) throw new Error("TIMEOUT_INVALID");
    this.fetchImpl = (...args) => fetchImpl(...args);
    this.vault = vault;
    this.timeoutMs = timeoutMs;
  }

  async request(path, { method = "GET", body, authenticated = false, deviceId, deletionToken } = {}) {
    if (!/^\/v1\/[a-z0-9/_-]+$/i.test(path)) throw new Error("API_PATH_INVALID");
    const headers = { "Accept": "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (authenticated) {
      const token = this.vault.get();
      if (!token) throw new FreeFlexApiError("AUTH_REQUIRED", 401, "로그인 수령 링크가 필요합니다.");
      headers.Authorization = `Bearer ${token}`;
    }
    if (deviceId) headers["X-FreeFlex-Device"] = deviceId;
    if (deletionToken) headers["X-FreeFlex-Deletion-Token"] = deletionToken;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    let response;
    try {
      response = await this.fetchImpl(`${this.apiBase}${path}`, {
        method, headers, body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal, credentials: "omit", cache: "no-store",
      });
    } catch (error) {
      const code = error?.name === "AbortError" ? "API_TIMEOUT" : "API_UNREACHABLE";
      throw new FreeFlexApiError(code, 0, "FreeFlexVPN 서버에 연결할 수 없습니다.");
    } finally {
      clearTimeout(timer);
    }
    let payload;
    try { payload = await response.json(); } catch (_error) {
      throw new FreeFlexApiError("INVALID_API_RESPONSE", response.status, "서버 응답 형식이 올바르지 않습니다.");
    }
    if (!response.ok || !payload || typeof payload !== "object" || Array.isArray(payload)) {
      if (authenticated && response.status === 401) this.vault.clear();
      throw new FreeFlexApiError(payload?.error, response.status, payload?.message);
    }
    return payload;
  }

  catalog() { return this.request("/v1/catalog"); }
  wallet() { return this.request("/v1/wallet", { authenticated: true }); }
  usage() { return this.request("/v1/usage", { authenticated: true }); }
  devices() { return this.request("/v1/devices", { authenticated: true }); }
  referrals() { return this.request("/v1/referrals", { authenticated: true }); }
  issueReferral() { return this.request("/v1/referrals", { method: "POST", authenticated: true }); }
  check(deviceId) { return this.request("/v1/check", { authenticated: Boolean(this.vault.get()), deviceId }); }
  registerDevice(publicKey, serverId) {
    return this.request("/v1/devices", {
      method: "POST", authenticated: true, body: { wg_public_key: publicKey, server_id: serverId },
    });
  }
  revokeDevice(deviceId) {
    if (!/^[a-f0-9]{32}$/.test(deviceId || "")) throw new Error("DEVICE_ID_INVALID");
    return this.request(`/v1/devices/${deviceId}`, { method: "DELETE", authenticated: true });
  }
  exportAccountData() {
    return this.request("/v1/account/export", {
      method: "POST", authenticated: true, body: { confirm: "EXPORT" },
    });
  }
  async requestAccountDeletion() {
    const result = await this.request("/v1/account/delete", {
      method: "POST", authenticated: true, body: { confirm: "DELETE" },
    });
    this.vault.clear();
    return result;
  }
  deletionStatus(requestId, statusToken) {
    if (!/^[a-f0-9]{32}$/.test(requestId || "") || typeof statusToken !== "string" || statusToken.length < 32) {
      throw new Error("DELETION_STATUS_CREDENTIAL_INVALID");
    }
    return this.request(`/v1/account/deletion-status/${requestId}`, { deletionToken: statusToken });
  }

  async exchangeClaim(claim, referralToken = null) {
    if (typeof claim !== "string" || claim.length < 32) throw new FreeFlexApiError("INVALID_CLAIM", 401, "수령 링크가 올바르지 않습니다.");
    const body = { claim };
    if (referralToken) body.referral_token = referralToken;
    const result = await this.request("/v1/claims/exchange", { method: "POST", body });
    const persistence = this.vault.set(result.access_token);
    const { access_token: _discarded, ...safeResult } = result;
    return { ...safeResult, session_persistence: persistence };
  }
}

export function consumeLaunchParameters(client, locationImpl = globalThis.location, historyImpl = globalThis.history) {
  const url = new URL(locationImpl.href);
  const hashText = url.hash.startsWith("#claim=") || url.hash.startsWith("#ref=") ? url.hash.slice(1) : "";
  const hashParams = new URLSearchParams(hashText);
  const claim = hashParams.get("claim") || url.searchParams.get("claim");
  const referral = hashParams.get("ref") || url.searchParams.get("ref");
  if (!claim) return Promise.resolve({ exchanged: false, referral });
  return client.exchangeClaim(claim, referral).then((result) => {
    url.searchParams.delete("claim");
    url.searchParams.delete("ref");
    if (hashText) url.hash = "";
    historyImpl.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
    return { exchanged: true, result };
  });
}

export function buildClaimLaunchUrl(appUrl, claim, referralToken = null) {
  const url = new URL(appUrl);
  if (url.protocol !== "https:" || url.username || url.password) throw new Error("HTTPS_APP_URL_REQUIRED");
  if (typeof claim !== "string" || claim.length < 32) throw new Error("CLAIM_INVALID");
  url.searchParams.delete("claim");
  url.searchParams.delete("ref");
  const fragment = new URLSearchParams({ claim });
  if (referralToken) fragment.set("ref", referralToken);
  url.hash = fragment.toString();
  return url.href;
}

export function bytesToGb(value) {
  const number = Number(value);
  if (!Number.isSafeInteger(number) || number < 0) throw new Error("BYTE_COUNT_INVALID");
  return (number / 1_000_000_000).toFixed(2);
}
