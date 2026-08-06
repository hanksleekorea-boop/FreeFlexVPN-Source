# FreeFlexVPN v2.17 — T1~T10 원본 증거 계약

상태: `VERIFIED_IMPLEMENTED_LOCAL_ONLY`  
실제 서버·기기·사용자 증거: `0`  
제품 진척: `7/12 = 58.3%` 유지

## v2.17에서 닫은 통과 우회

- 자기기입 `actual_target` JSON만으로는 더 이상 `ready=true`가 되지 않는다.
- 번들과 원본은 프로젝트 밖 같은 폴더에 두며, 상대경로와 SHA-256이 모두 일치해야 한다.
- 상위경로·절대경로·프로젝트 내부 파일·심볼릭 링크·빈 파일·50MB 초과 파일을 거부한다.
- 후보 ID와 판정 시각을 번들·측정값·모든 원본에 결속한다.
- T1~T10 전건에 허용된 종류의 원본이 있어야 하며 같은 경로·같은 내용의 중복 등록을 거부한다.
- T1 세션 ID, T4 측정 ID, T10 참여자 참조는 고유해야 한다.
- T10은 독립·동의·실제 보호·무도움 성공뿐 아니라 최소 4주 관찰을 요구한다.
- 판정 결과에는 원본 경로와 파일 내용이 포함되지 않는다.

## 실행

1. `60_OUTPUTS/FreeFlexVPN_runtime_evidence_workbench_v2.17_2026-08-03.html`을 로컬에서 연다.
2. 개인키·토큰·결제수단·실명·원본 IP 등 불필요한 민감값을 제거한 원본을 T1~T10에 연결한다.
3. 생성한 `bundle.json`을 원본 파일과 같은 프로젝트 밖 폴더에 둔다.
4. `python 70_TOOLS/evaluate_runtime_acceptance.py <외부 bundle.json>`을 실행한다.

반환 코드 `0`과 `ready=true`가 함께 있어야 판정기가 통과한 것이다. 그래도 원본의 의미가 실제 대상환경을 증명하는지는 운영 검토자가 확인해야 하며, 로컬 자동검사만으로 D/U 증거를 주장하지 않는다.

## 테스트별 허용 원본 종류

| 테스트 | 허용 종류 |
|---|---|
| T1 | log, screenshot |
| T2 | measurement, screenshot |
| T3 | pcap_summary, measurement |
| T4 | measurement |
| T5~T7 | log, screenshot |
| T8 | pcap_summary, measurement |
| T9 | log, screenshot |
| T10 | consent_record |

이 계약은 실제 결제·환불(M10)과 추천 파일럿(M11)을 대체하지 않는다. 해당 마일스톤은 승인된 PG와 동의된 실제 추천 증거가 별도로 필요하다.
