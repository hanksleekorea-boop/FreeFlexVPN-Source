# AI 지속개발·Drive·GitHub 권한 정책 v5.2

- 계정·대화 기억은 정본이 아니다. AGENTS.md, 프로젝트 파일, Git 상태, 이 폴더의 검증 기록만 정본이다.
- 협업 LOCK/장기 lease를 만들지 않는다. SQLite·Git·OS의 순간적 내부 잠금은 개발 소유권 잠금이 아니다.
- 백업은 불변 backup_id로 추가하며 Drive의 기존 세대를 자동 삭제·덮어쓰기하지 않는다.
- Drive 업로드 뒤 독립 다운로드·해시·복원 검증 전에는 일반 프로젝트 파일을 정리하지 않는다.
- 예약 maintain은 백업·검증·정리계획만 수행하고 cleanup-apply를 호출하지 않는다.
- 비밀번호·토큰·쿠키·MFA·복구코드·복호화 키·계정 원문을 프로젝트나 로그에 기록하지 않는다.
- 현재 소스, 루트 .git, 사용자 변경, 연속성 정본, 보호 경로, 판단 불가 파일은 정리하지 않는다.

## 매 세션의 빠른 경로

1. `runtime/continuity-v520.py bootstrap --compact`의 JCS 한 줄과 `CONTEXT.md`만 먼저 읽는다.
2. 현재 사용자 요청이 있으면 그것을, 없으면 `다음 첫 행동`을 수행한다.
3. 무변경 HOT에서는 이 정책·전체 사건·백업 이력을 다시 읽지 않는다.
4. 종료 전 `checkpoint`를 실행한다. 의미 변화가 없고 최신 복구가 READY면 기록·업로드·검사를 반복하지 않는다.
5. 설치 영수증이나 정본 해시가 다를 때만 COLD로 전환해 필요한 파일을 선택적으로 읽는다.

## 승인과 권한

- 읽기, 프로젝트 내부 편집, 비파괴 검사와 로컬 연속성 기록은 현재 개발 요청 범위에서 자동 수행한다.
- push/merge, 공개·운영 배포, 비용, DNS·secret·production data, 공개범위 변경, 일반 프로젝트 파일 삭제는 실제 provider 권한과 현재 승인을 모두 확인한다.
- ChatGPT/AI 계정 이름은 권한이 아니다. 같은 OS 사용자·파일 권한·provider principal의 실제 capability readback으로 판단한다.
- 자격증명은 복사하지 않는다. 다른 PC에서는 승인된 인증과 신뢰 자료가 없으면 외부 작업만 HOLD하고 로컬 개발은 계속한다.
- 최초 준비 AI는 사용자가 승인한 GitHub 로그인 상태에서 `github-bind --confirm-owner-baseline`을 한 번 실행해 저장소 ID와 권한 booleans만 기준선으로 기록한다.
- 이후 AI는 GitHub 로그인 뒤 `github-verify`를 실행한다. 같은 GitHub principal은 GitHub가 부여한 동일 권한으로 통과하며, 다른 principal은 동일 저장소 권한이 기준선 이상일 때만 통과한다.
- GitHub login·PAT·쿠키·numeric user ID·login 이름은 저장하지 않는다. 로그인만으로 임의 계정에 권한을 부여하지 않으며 부족하면 조직 team/협업자 권한 또는 승인된 principal 재로그인이 필요하다.
- Admin 동등성이 확인돼도 저장소 삭제·이전·가시성 변경·멤버 관리·secret 변경은 별도 현재 승인을 요구한다.

## 백업과 PC 경량화

- Drive A/B에 full→delta→tombstone 불변 세대를 추가하고 COMPLETE를 마지막에 쓴다.
- 두 원격 각각 재다운로드·해시·임시 복원을 통과해야 READY다. 하나는 PARTIAL, 둘 실패는 BLOCKED다.
- 민감 파일은 프로젝트 밖 키를 쓰는 승인된 암호화 원격 두 개가 아니면 업로드하지 않는다.
- 로컬에는 활성 프로젝트, 최신 매니페스트 한 벌, 세대별 소형 영수증만 유지한다.
- 일반 정리는 대화형 plan hash, Drive A/B READY, 최신 복원 PASS, 후보 불변을 모두 확인한 뒤 격리→postcheck→제거한다. 예약 실행은 삭제하지 않는다.

## 충돌·복구·정직한 경계

- 다른 작업자의 현재 bytes를 덮지 않는다. 비중첩 변경은 병합하고 중첩 변경은 patch로 보존한다.
- COMPLETE 없는 준비물은 최신으로 승격하지 않는다. 손상·중단은 기존 성공 세대를 보존한 채 재시도한다.
- 실제 Drive privacy/readback, 다른 계정 수락, 예약 설치, macOS/Linux, provider 권한은 실행 증거가 없으면 NOT_RUN/UNKNOWN이다.
- 구조적 준비와 실제 외부 권한 상속을 구분하며, 전체 무오류나 권한 자동 복제를 주장하지 않는다.
