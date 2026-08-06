# FreeFlexVPN v2.4 R6 실서버 사전점검 실행계획

> 상태: `VERIFIED_IMPLEMENTED_LOCAL`  
> 날짜: 2026-08-02  
> 이전 공개 롤백: v2.3 / Git main `08db94d017db52345eff157d6db1c5be4e512e64`

## 쉬운 요약

서버 계정이 도착했을 때 두 서버가 정말 서로 다른 공급자에서 살아 있고, 지금 읽은 상태와 앱에 보여줄
서버 목록이 같은지를 한 명령으로 확인한다. 하나라도 빠지면 앱에는 서버를 공개하지 않고 `BLOCKED`로 남긴다.

## 이번 구현

1. health 시각이 없거나 120초를 넘었거나 30초보다 미래이면 정상 판정을 거부한다.
2. 서로 다른 공급자 2곳과 서로 다른 출구 IP·endpoint·노드 ID·WireGuard 공개키를 요구한다.
3. 두 노드의 SSH health, 카운터, 공개 카탈로그가 모두 일치해야 PASS한다.
4. 결과는 기존 파일을 덮지 않는 새 JSON으로 원자 저장한다.
5. 증거에는 SSH host·identity/known_hosts 경로·endpoint·IP·공개키·공급자명을 넣지 않는다.

## 현재 증거와 경계

- I: 구현 완료 — `r6_preflight.py`, `run_r6_server_preflight.py`.
- L: 새 계약 6/6, 서버 카탈로그 10/10, SSH 어댑터 10/10 통과.
- 실제 서버: 0대. 실서버 명령 실행과 PASS 증거는 아직 없다.
- D/U: 실기기·독립 사용자 증거 없음.
- v2 기준선: 7/12 = 58.3% 유지. 이 도구는 M8 진입 준비이며 M8 자체가 아니다.

## 서버 접근 뒤 실행

```powershell
python 70_TOOLS/run_r6_server_preflight.py `
  --config 'C:\ProgramData\FreeFlexVPN\nodes.json' `
  --candidate-id 'R6-candidate-YYYYMMDD-01'
```

PASS 뒤에도 같은 후보로 iOS·Android·Windows 8개 안전 항목을 전부 확인해야 M9로 이동한다.

## 롤백

코드에서는 `r6_preflight.py`와 CLI를 제외하고 health 미래 시각 상한 변경을 되돌린다. 문서에서는 이 파일과
D51·D52를 제외한다. 공개 v2.3 산출물은 이번 로컬 준비 작업에서 수정하지 않았다.
