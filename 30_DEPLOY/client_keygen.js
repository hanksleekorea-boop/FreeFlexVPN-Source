/**
 * FreeFlexVPN client-side WireGuard key handling.
 *
 * The private key is generated and used only in this browser context.  It is
 * never placed in a request body or browser persistence by this module.
 */

const KEY_BYTES = 32;

function bytesToBase64(bytes) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function base64UrlToBytes(value) {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((value.length + 3) % 4);
  const binary = atob(padded);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

function decodeWireGuardKey(value, field) {
  if (typeof value !== "string" || !/^[A-Za-z0-9+/]{42}[AEIMQUYcgkosw048]=$/.test(value)) {
    throw new Error(`${field} must be a 32-byte WireGuard key`);
  }
  const decoded = Uint8Array.from(atob(value), (char) => char.charCodeAt(0));
  if (decoded.length !== KEY_BYTES) throw new Error(`${field} must be 32 bytes`);
  return decoded;
}

function requireWebCrypto(cryptoImpl) {
  if (!cryptoImpl || !cryptoImpl.subtle || typeof cryptoImpl.subtle.generateKey !== "function") {
    throw new Error("BROWSER_X25519_UNAVAILABLE");
  }
  return cryptoImpl;
}

export async function supportsBrowserX25519(cryptoImpl = globalThis.crypto) {
  try {
    const cryptoApi = requireWebCrypto(cryptoImpl);
    const pair = await cryptoApi.subtle.generateKey({ name: "X25519" }, true, ["deriveBits"]);
    const [privateJwk, publicJwk] = await Promise.all([
      cryptoApi.subtle.exportKey("jwk", pair.privateKey),
      cryptoApi.subtle.exportKey("jwk", pair.publicKey),
    ]);
    return Boolean(privateJwk.d && publicJwk.x);
  } catch (_error) {
    return false;
  }
}

export async function generateWireGuardKeyPair(cryptoImpl = globalThis.crypto) {
  const cryptoApi = requireWebCrypto(cryptoImpl);
  let pair;
  try {
    pair = await cryptoApi.subtle.generateKey({ name: "X25519" }, true, ["deriveBits"]);
  } catch (_error) {
    throw new Error("BROWSER_X25519_UNAVAILABLE");
  }

  const [privateJwk, publicJwk] = await Promise.all([
    cryptoApi.subtle.exportKey("jwk", pair.privateKey),
    cryptoApi.subtle.exportKey("jwk", pair.publicKey),
  ]);
  const privateBytes = base64UrlToBytes(privateJwk.d || "");
  const publicBytes = base64UrlToBytes(publicJwk.x || "");
  if (privateBytes.length !== KEY_BYTES || publicBytes.length !== KEY_BYTES) {
    throw new Error("BROWSER_X25519_INVALID_KEY");
  }
  return Object.freeze({
    privateKey: bytesToBase64(privateBytes),
    publicKey: bytesToBase64(publicBytes),
  });
}

export async function registerPublicKey({ apiBase, sessionToken, publicKey, serverId, fetchImpl = globalThis.fetch }) {
  decodeWireGuardKey(publicKey, "publicKey");
  if (!/^https:\/\//.test(apiBase || "")) throw new Error("HTTPS_API_REQUIRED");
  if (typeof sessionToken !== "string" || sessionToken.length < 20) throw new Error("SESSION_REQUIRED");
  if (!/^[a-z0-9][a-z0-9-]{1,62}$/.test(serverId || "")) throw new Error("SERVER_ID_INVALID");
  if (typeof fetchImpl !== "function") throw new Error("FETCH_UNAVAILABLE");

  const response = await fetchImpl(`${apiBase.replace(/\/$/, "")}/v1/devices`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${sessionToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ wg_public_key: publicKey, server_id: serverId }),
    credentials: "omit",
    cache: "no-store",
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || "DEVICE_REGISTRATION_FAILED");
  return payload;
}

export function renderWireGuardConfig(privateKey, registration) {
  decodeWireGuardKey(privateKey, "privateKey");
  if (!registration || typeof registration !== "object") throw new Error("REGISTRATION_INVALID");
  const configuration = registration.configuration || null;
  const normalized = configuration ? {
    address: configuration.addresses?.[0],
    dns: Array.isArray(configuration.dns) ? configuration.dns.join(", ") : configuration.dns,
    server_public_key: configuration.peer?.public_key,
    endpoint: configuration.peer?.endpoint,
  } : registration;
  decodeWireGuardKey(normalized.server_public_key, "serverPublicKey");
  if (!/^10\.66\.0\.(?:[2-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-4])\/32$/.test(normalized.address || "")) {
    throw new Error("ADDRESS_INVALID");
  }
  const endpoint = String(normalized.endpoint || "");
  if (!/^\[[0-9a-f:]+\]:\d{1,5}$/i.test(endpoint) && !/^[A-Za-z0-9.-]+:\d{1,5}$/.test(endpoint)) {
    throw new Error("ENDPOINT_INVALID");
  }
  const dns = String(normalized.dns || "");
  if (!dns || /[\r\n]/.test(dns)) throw new Error("DNS_INVALID");

  return [
    "[Interface]",
    `PrivateKey = ${privateKey}`,
    `Address = ${normalized.address}`,
    `DNS = ${dns}`,
    "",
    "[Peer]",
    `PublicKey = ${normalized.server_public_key}`,
    "AllowedIPs = 0.0.0.0/0, ::/0",
    `Endpoint = ${endpoint}`,
    "PersistentKeepalive = 25",
    "",
  ].join("\n");
}

export async function createDeviceProfile(options) {
  const keyPair = await generateWireGuardKeyPair(options.cryptoImpl || globalThis.crypto);
  const registration = typeof options.registerPublicKeyImpl === "function"
    ? await options.registerPublicKeyImpl(keyPair.publicKey, options.serverId)
    : await registerPublicKey({
        apiBase: options.apiBase,
        sessionToken: options.sessionToken,
        publicKey: keyPair.publicKey,
        serverId: options.serverId,
        fetchImpl: options.fetchImpl || globalThis.fetch,
      });
  return Object.freeze({
    config: renderWireGuardConfig(keyPair.privateKey, registration),
    publicKey: keyPair.publicKey,
    deviceId: registration.device_id || null,
  });
}

export const manualFallback = Object.freeze({
  code: "BROWSER_X25519_UNAVAILABLE",
  message: "이 브라우저에서는 안전한 키 생성을 지원하지 않습니다. 공식 WireGuard 앱에서 키를 만든 뒤 공개키만 등록하세요.",
});
