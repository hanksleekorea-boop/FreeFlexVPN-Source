# FreeFlexVPN v2.5 R6 설정 전용 사전검사 계획

> 상태: `VERIFIED_IMPLEMENTED_LOCAL`  
> 날짜: 2026-08-02  
> 이전 후보·롤백: v2.4 R6 실서버 사전점검

## 쉬운 요약

운영자가 서버 설정 파일을 만든 뒤 실제 서버에 접속하기 전에 구조와 2공급자 분산만 안전하게 확인한다.
검사 중 네트워크 요청은 0건이며, 통과해도 실제 VPN 서버가 정상이라는 뜻으로 표시하지 않는다.

## 결과 계약

- `configuration_ready=true`: 설정 구조·2노드·2공급자·중복 방지가 통과했다.
- `ready=false`: 설정 전용 검사는 실제 R6 완료가 될 수 없다.
- `network_attempted=false`: SSH·HTTP 요청을 만들지 않았다.
- 다음 관문: 같은 candidate ID와 설정으로 실서버 사전점검을 실행한다.

## 현재 증거와 경계

- I/L: 설정 전용 양성·단일 공급자 음성 대조를 포함한 R6 표적 계약 8/8 통과.
- 실제 서버·실기기·사용자: 증거 없음.
- v2 기준선: 7/12 = 58.3% 유지.

## 실행

```powershell
python 70_TOOLS/run_r6_server_preflight.py `
  --config 'C:\ProgramData\FreeFlexVPN\nodes.json' `
  --candidate-id 'R6-candidate-YYYYMMDD-01' `
  --config-only
```

## 롤백

CLI의 `--config-only` 분기와 `evaluate_configuration_preflight`를 제외하면 v2.4 동작으로 돌아간다.
v2.4 계획·증거·공개 v2.3 앱은 수정하지 않는다.
