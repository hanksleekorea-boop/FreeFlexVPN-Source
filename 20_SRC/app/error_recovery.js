const RECOVERY = Object.freeze({
  NO_INTERNET: ["인터넷 연결 없음", "VPN 밖 일반 인터넷도 사용할 수 없습니다.", "Wi-Fi 또는 이동통신을 먼저 확인하세요.", true],
  PROFILE_EXPIRED: ["설정 수령 만료", "오래된 일회성 설정은 가져올 수 없습니다.", "기존 설정을 보존한 채 새 후보를 발급하세요.", false],
  SERVER_UNAVAILABLE: ["서버 사용 불가", "현재 후보 경로를 시작할 수 없습니다.", "기존 설정을 유지하고 검증된 다른 서버를 확인하세요.", true],
  DNS_FAILED: ["DNS 보호 확인 실패", "주소 찾기가 보호 경로와 일치하지 않습니다.", "후보를 끄고 일반 인터넷 복귀를 확인하세요.", true],
  PERMISSION_DENIED: ["권한 거부", "앱 설치·가져오기·연결 중 요청한 동작을 완료하지 못했습니다.", "운영체제 설정에서 필요한 권한을 직접 확인하세요.", false],
  BALANCE_EMPTY: ["사용 가능 데이터 없음", "새 보호 세션을 시작하지 않습니다.", "무료·충전·추천 잔액의 실제 원장을 확인하세요.", false],
  PAYMENT_PENDING: ["결제 확인 중", "잔액을 임의로 늘리거나 중복 결제하지 않습니다.", "재결제하지 말고 결제 상태 확인을 기다리세요.", false],
  EVIDENCE_STALE: ["보호 근거 오래됨", "이전 성공을 현재 보호 상태로 사용하지 않습니다.", "현재 기기에서 보호 확인을 다시 실행하세요.", true],
});

export function createRecoveryAction(errorCode, retryCount = 0) {
  const code = Object.hasOwn(RECOVERY, errorCode) ? errorCode : "UNKNOWN";
  const [title, impact, nextAction, retryable] = RECOVERY[code] || ["요청 중단", "현재 상태를 확인하지 못했습니다.", "기존 설정을 지우지 말고 가린 진단을 저장하세요.", false];
  const retries = Number.isInteger(retryCount) && retryCount >= 0 ? retryCount : 0;
  const retryAllowed = retryable && retries < 2;
  return Object.freeze({schema:"FreeFlexVPNRecoveryActionV1",code,title,impact,next_action:retryAllowed?nextAction:"재시도하지 말고 기존 설정을 보존한 채 지원 안내를 확인하세요.",retry_count:retries,retry_allowed:retryAllowed,retry_limit:2,focus_target:retryAllowed?"retry":"support",existing_profile_action:"preserve",automatic_profile_deletion:false,automatic_payment_retry:false,contains_sensitive_data:false});
}

export const RECOVERY_CODES = Object.freeze(Object.keys(RECOVERY));
