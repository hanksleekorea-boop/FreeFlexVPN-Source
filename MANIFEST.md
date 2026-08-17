# MANIFEST — FreeFlexVPN 이관 묶음

| 항목 | 값 |
|---|---|
| 파일 수 | 509 |
| 총 바이트 | 12,188,397 |

## 지문 규칙

- 텍스트 파일은 줄바꿈(CRLF/LF)을 LF로 맞춘 뒤 SHA-256을 계산한다. 따라서 Windows·macOS·Linux 복제본도 같은 내용이면 같은 지문값이다.
- 이미지·압축 파일 등 이진 파일은 원래 바이트 그대로 SHA-256을 계산한다.

## 제외 (검사 실행 시 재생성)

- `60_OUTPUTS/checks/*`
- `60_OUTPUTS/checks/**/*`
- `60_OUTPUTS/AI_HANDOFF_CURRENT/*`
- `60_OUTPUTS/AI_HANDOFF_CURRENT/**/*`
- `.project-continuity/LOCK*.json`
- `*.pyc`
- `*.log`
- `*.tmp`
- `.project-continuity/local/**` (기기별 인계 원장)
- `MANIFEST.md` (자기 자신)

## 대청소 이동 기록

| 원래 위치 | 새 위치 | 바이트 | 용도 |
|---|---|---:|---|
| `00_START/HANDOFF_V2_2026-08-01.md` | `90_ARCHIVE/00_START_legacy/HANDOFF_V2_2026-08-01.md` | 2,352 | 이전 시작 안내 |
| `00_START/README.md` | `90_ARCHIVE/00_START_legacy/README.md` | 5,242 | 이전 시작 안내 |
| `10_STATE/APP_SERVICE_PLAN_v2.0_2026-08-01.md` | `90_ARCHIVE/10_STATE_plans/APP_SERVICE_PLAN_v2.0_2026-08-01.md` | 24,251 | 과거 제품 기획 |
| `10_STATE/APP_SERVICE_PLAN_v3.0_2026-08-05.md` | `90_ARCHIVE/10_STATE_plans/APP_SERVICE_PLAN_v3.0_2026-08-05.md` | 8,313 | 과거 제품 기획 |
| `10_STATE/APP_SERVICE_PLAN_v4.0_2026-08-06.md` | `90_ARCHIVE/10_STATE_plans/APP_SERVICE_PLAN_v4.0_2026-08-06.md` | 8,941 | 과거 제품 기획 |
| `10_STATE/DEV_EXECUTION_PLAN_v2.0_2026-08-01.md` | `90_ARCHIVE/10_STATE_plans/DEV_EXECUTION_PLAN_v2.0_2026-08-01.md` | 26,975 | 과거 상세 실행계획 |
| `10_STATE/DEV_EXECUTION_PLAN_v3.0_2026-08-05.md` | `90_ARCHIVE/10_STATE_plans/DEV_EXECUTION_PLAN_v3.0_2026-08-05.md` | 11,921 | 과거 상세 실행계획 |
| `10_STATE/DEV_EXECUTION_PLAN_v4.0_2026-08-06.md` | `90_ARCHIVE/10_STATE_plans/DEV_EXECUTION_PLAN_v4.0_2026-08-06.md` | 15,009 | 과거 상세 실행계획 |

## 파일별 목록

| 파일 | 바이트 | 용도 | sha256 |
|---|---:|---|---|
| `.gitattributes` | 218 | 분류 확인 필요 | `cb2bdf9a1edbaf913f6f89daa2c98933d30cc8464941a29808981502349c1e93` |
| `.github/CODEOWNERS` | 143 | 분류 확인 필요 | `2ffe28e90a580d6b22e09a92d171683f53c689d618d1dd62f582171c80e02523` |
| `.github/CONTRIBUTING.md` | 428 | 분류 확인 필요 | `ae0624eb0861e01a89b08d7bae6a9221690f87c9af6975328adfe93bd05512ac` |
| `.github/dependabot.yml` | 350 | 분류 확인 필요 | `2dd209f285ddbdc4b7bc2209af996536b246074a5cef272491796b4ae8092a3b` |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | 431 | 분류 확인 필요 | `fcea5deb3912e7e0630804a45155e5a35b5dd11a30aee8fe4de966ca4cde6859` |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | 384 | 분류 확인 필요 | `1013065a745fabf3886d4ec88ba2b23bb3c49eeeba241f38b27a3f3ec4a99e34` |
| `.github/pull_request_template.md` | 433 | 분류 확인 필요 | `dd08e8c207bd2b4d5434efc5329524067df50ad0f1607de1b3162e9e061a4bef` |
| `.github/SECURITY.md` | 419 | 분류 확인 필요 | `5c452b3cace207d707675ab6e6deabee9e0928862b7c4b29033bd5818c8f5836` |
| `.github/workflows/ci.yml` | 1,612 | 분류 확인 필요 | `0c0fc67ff258f650f00afb18de9ff9de7cd71dce40671ab59e357d6f4cb2fbf7` |
| `.gitignore` | 374 | 버전 관리 제외 규칙 | `5bb0dde7ad78d5c4a281d1f4641f4cbff7f18f5557e36e8c024fb28b3d2a3d6a` |
| `.project-continuity/APPROVALS.md` | 8,187 | 공동개발 연속성 기록 | `d1d8fda06ab505ecb88363139794a941a2151dbdb1408f85ce10ac0bc8af20ba` |
| `.project-continuity/BACKUP_LATEST.json` | 518 | 공동개발 연속성 기록 | `4dd198c72238ab82974bc544a03701134c940026df6f8f11242e53275c3a2e72` |
| `.project-continuity/BACKUPS.jsonl` | 5,319 | 공동개발 연속성 기록 | `c7ed9dc4e1b65fe2747c9bc9a27ac98dac58c995837dfefa88f92914472cea58` |
| `.project-continuity/CLEANUP-PLAN.json` | 360 | 공동개발 연속성 기록 | `962a16c7aace9e99890ef297ec717bb3660ca31c2bf396f9792683655769842e` |
| `.project-continuity/COMPLETION.md` | 870 | 공동개발 연속성 기록 | `765ea806a447d93e183845a01db536ad3e78784947d82cedaf85bee8fb7a6254` |
| `.project-continuity/CONFIG.json` | 373 | 공동개발 연속성 기록 | `0769c778d0052b9f9ad0e06721bc5d71bd74aa70d285dd44053a3fdea34f3849` |
| `.project-continuity/CONSULTING.md` | 2,610 | 공동개발 연속성 기록 | `256fbf28a6e7d1ee10a035c43b63fee7150e68f4be7c33137d97381cf372bce1` |
| `.project-continuity/CONTEXT.md` | 214 | 공동개발 연속성 기록 | `831639ee4a39e666d9e4a5638ad0599e5eb4631b9d8c1a37672b35a952d60c07` |
| `.project-continuity/DRIVE-PRIVACY.json` | 646 | 공동개발 연속성 기록 | `921be92678e7c42b6aac52b54c9010857a742bbc2a9516704e154c67611797fb` |
| `.project-continuity/EVENTS.jsonl` | 1,717 | 공동개발 연속성 기록 | `3c2e17bacf6039460e050a70f540845060d954087ebc7d766401343b046212f4` |
| `.project-continuity/gitdir-pointer-removed-20260815.txt` | 141 | 공동개발 연속성 기록 | `f8a283c584374417ce161a8c86a634d43180b5b549297181d97f9f34e7115de6` |
| `.project-continuity/GITHUB-ACCESS-BASELINE.json` | 283 | 공동개발 연속성 기록 | `5806d36a71f70da78bddfa8e86713dacb64b78a3ae639af07c4745f2aa71ac1b` |
| `.project-continuity/GITHUB-ACCESS.json` | 105 | 공동개발 연속성 기록 | `eb769638ad75b177a6dbdde678e7c3a29c75a2d9495760d1544a134eace8ef11` |
| `.project-continuity/GITHUB_AUDIT.md` | 5,070 | 공동개발 연속성 기록 | `b724bee35264ae43b82a0fb6021446eaf0f92565fe386254dae554ba2a1f5008` |
| `.project-continuity/HANDOFF_CAPSULE.json` | 1,967 | 공동개발 연속성 기록 | `839914aa92a0e41382468e9bf7cd1e9d1f916dbe0ab6dd78e0b7aa39d0bb8f79` |
| `.project-continuity/HISTORY.md` | 98,287 | 공동개발 연속성 기록 | `a89be6712cbea3188bf0ee2e132bcb281bb147a12359e3d834f77ee99c675649` |
| `.project-continuity/INSTALL-RECEIPT.json` | 341 | 공동개발 연속성 기록 | `78304aad40f0511e288305551c314e365b13a90fb793211c790db53c8dc6031d` |
| `.project-continuity/MANIFEST-LATEST.json` | 810,130 | 공동개발 연속성 기록 | `f67d23015940235ec0752a20c0195e575e3a94b4330475f7928c4a1f27d3ffbc` |
| `.project-continuity/NO_LOCK_POLICY.md` | 1,281 | 공동개발 연속성 기록 | `d91c91ca5378b30825c10879fb1e0b741f5ba130dfdc4f46385639397b470526` |
| `.project-continuity/OWNER_CONTROL.md` | 3,517 | 공동개발 연속성 기록 | `0d99cbaa21aea7625d1f9e18f751f226311bc3526f405bc9a66981a1421d4817` |
| `.project-continuity/PC-LIGHTWEIGHT-PLAN.json` | 9,955 | 공동개발 연속성 기록 | `b89228654df548c68986aaae764b9a06d3103c07fc9cbc4169e4e0b60b5828f3` |
| `.project-continuity/PC-LIGHTWEIGHT-RECEIPT.json` | 2,098 | 공동개발 연속성 기록 | `e2b4232181ab38ad2ceca7e154ea97c1b4503f4d4e2be70b3c40e5e7ce13fdf0` |
| `.project-continuity/PERMISSION-BASELINE.json` | 461 | 공동개발 연속성 기록 | `0335bf1f68c7aa01aaf2b6c5ef4f0de03db994c411864b9b4b2de2c95327042f` |
| `.project-continuity/POLICY-v5.2.md` | 4,344 | 공동개발 연속성 기록 | `21f7d638dded946aaa7c8ebf8f6307201c1ea275c794a31e38a01687c92deccb` |
| `.project-continuity/runs/20260814T092035Z-7e1868a557fe-d03ff7db.json` | 518 | 공동개발 연속성 기록 | `21da7eca692079b291da7596f1e1c7c367fec6620e22051d7cc3a813d773ea5e` |
| `.project-continuity/runs/20260814T093531Z-7e1868a557fe-c8eee2c9.json` | 518 | 공동개발 연속성 기록 | `4e766790b0270eb7317097a9fcff2de4072a5f99a34b921852fc026b73b9413e` |
| `.project-continuity/runs/20260814T100507Z-c38f5b482884-9368a0c0.json` | 555 | 공동개발 연속성 기록 | `c0f6697430f489a0ee2ece0934ebfa20457c22b3126b408be955c5a140842050` |
| `.project-continuity/runs/20260814T162800Z-9ed343f353dc-4e66e763.json` | 555 | 공동개발 연속성 기록 | `f5eeaedb2864f0efc45323073061887de15509ab6ffcfbd498ab88d7d209e91c` |
| `.project-continuity/runs/20260814T201559Z-fbf5b4657398-b6630d43.json` | 536 | 공동개발 연속성 기록 | `db665c94e007a302256460a734cd4d0e0a671b94f8acf4d2a547ee2108b49721` |
| `.project-continuity/runs/20260817T155604Z-74faffca4b5e-3182c0a2.json` | 555 | 공동개발 연속성 기록 | `6b81b16d27d4abec07163b608a68eef2f921e025e8400a6545b475e466af586e` |
| `.project-continuity/runs/20260817T171746Z-a6c5ceaf4ee3-7da418c5.json` | 518 | 공동개발 연속성 기록 | `047045b042a917e5e20f9bdb0b3f068ad6b61798c7aa242c1ff3fcc2276f3a52` |
| `.project-continuity/runs/20260817T175925Z-e5d55290274b-ad613c80.json` | 518 | 공동개발 연속성 기록 | `2de1c2cc90726540d44883d7fd6450db268cf28e81ba21f1476fe4e3c016a1cf` |
| `.project-continuity/runs/20260817T180107Z-c5e57ef66782-f9fb17fd.json` | 518 | 공동개발 연속성 기록 | `188d62098282939746258edbf0c9dea9f5cd52f6226c943e21c520ecfcb7c9ae` |
| `.project-continuity/runs/20260817T182337Z-e4dbeb4d41c3-0a56e813.json` | 518 | 공동개발 연속성 기록 | `4dd198c72238ab82974bc544a03701134c940026df6f8f11242e53275c3a2e72` |
| `.project-continuity/runs/regression-20260817T232601.json` | 12,058 | 공동개발 연속성 기록 | `6036b92c076eb7315c55a5fadd2e7d54ad9970c9a3222983461f23629b42c122` |
| `.project-continuity/runs/RUN-9e5d65a1bcef4fb482ca06c630dd4e95.json` | 1,642 | 공동개발 연속성 기록 | `e78dcec654a29779315a14771967b559d0ec98d32b42e7c4bf6029f46b0b1d27` |
| `.project-continuity/runtime/continuity-v520.py` | 70,672 | 공동개발 연속성 기록 | `7c08ebf5fed65e46a3bd99473fb33a48f7981d612f294da04e10d23b438537ba` |
| `.project-continuity/SCHEMA_VERSION` | 4 | 공동개발 연속성 기록 | `01d0b2eba879dda9fd27bf01b46c7d1a34b92ecbb459d2d8dd3b3feebe933266` |
| `.project-continuity/SITE-CAPABILITIES.json` | 1,490 | 공동개발 연속성 기록 | `47be12234c407daaa469f938680a250e3b4f0391714d471a36679122d3a12fe0` |
| `.project-continuity/STATE.json` | 640 | 공동개발 연속성 기록 | `be79fddea8a95b601c838cb3e39439bf95fc34ccff984795e03c1b7acf32b54b` |
| `.project-continuity/STATE.md` | 48,171 | 공동개발 연속성 기록 | `3b58e7560caa91553321d308c246fd4c48ccdf1fb64fdeff0e0d34ddbcc2445a` |
| `.project-continuity/TEST_EVIDENCE.md` | 93,858 | 공동개발 연속성 기록 | `e123361a9baf622278e6ed4c1ef7e78471c905a230ca4d9d9d17266c7b9aedb1` |
| `00_START/COLLABORATION_GATEWAY.md` | 1,964 | 시작·인수인계 | `d017dc34b6c7853c5d9cbf0dd1433677df9f1d0ec64a7c08200975fa23e1ad5d` |
| `00_START/DEVELOPMENT_DASHBOARD.md` | 18,185 | 시작·인수인계 | `7d680612364e4dbf1e9ab3f4c0ee4f190cb3029b60645c36c07cce9fc67410f9` |
| `00_START/HANDOFF_PROMPT.md` | 14,622 | 시작·인수인계 | `08e5083c7e875677743e1b0ee1cc6ee1fee40fd736f559c56fcd80c88ecfe26b` |
| `00_START/NEW_CODEX_ACCOUNT_HANDOFF.md` | 6,646 | 시작·인수인계 | `9700eb7ea66e2e41f5070e2fcf56a7bc693b3c4401a20fa4ae4f65d74d14613e` |
| `00_START/NEW_PC_SETUP.md` | 3,343 | 시작·인수인계 | `504e9f96a672697e8af10ca2afa76afa59df2e40da5590b87e0c5b38dbf06a21` |
| `00_START/RECEIVER_HANDOFF_PROMPT.md` | 1,747 | 시작·인수인계 | `0ae6065e90ecc60cfdbbb312d1ed93d456e3900a6693489a9ade9310eca6203e` |
| `00_START/시작하세요.md` | 1,904 | 시작·인수인계 | `011ccda4eb89087cad0d112aaf14a022c12203d03512b9c244f75277e1362c18` |
| `10_PLAN/COMMERCIAL_RELEASE_GATE_PLAN_v1_2026-08-10.md` | 15,229 | 현재 기획·실행 정본 | `061b59f4190cbe3a93112d8fec93344838bb9a929232cd076ada57672ac3d400` |
| `10_PLAN/CURRENT_DEVELOPMENT_EXECUTION_PLAN.md` | 17,588 | 현재 기획·실행 정본 | `53577d0ad0f01322718bc76db922269771f4bace257f92459def4836527d9c5c` |
| `10_PLAN/CURRENT_SERVICE_PLAN.md` | 9,454 | 현재 기획·실행 정본 | `e2ac2690da78937c4d8e38a8572296543865a43ad74e76a03001d89bc3bdf026` |
| `10_STATE/A56_TEST_AND_USABILITY_REPORT_2026-08-05.md` | 5,529 | 상태·근거·기록 | `5bc856a25e01ac9ca4d49138b8b992b555194124c313ce1688c5da292a3d5ca5` |
| `10_STATE/ANDROID_DEVICE_SMOKE_2026-08-05.md` | 1,047 | 상태·근거·기록 | `87b2a3d33f05d34495fa64504b856affbbd2a5b7e2261fd5f4059a6c23a930e4` |
| `10_STATE/ANDROID_USB_NETWORK_CHECK_2026-08-05.md` | 1,833 | 상태·근거·기록 | `1102130d42ef0884099db7e861ab943abbc3882fe5c254f5601ed90925543d45` |
| `10_STATE/CONTRACTS.json` | 1,889 | 상태·근거·기록 | `fbb44678c17ce84db11152ece70c5780c12b9954d223ab5e7405ca18118a2290` |
| `10_STATE/CROSS_PLATFORM_PLAN_v2.2_2026-08-02.md` | 5,058 | 상태·근거·기록 | `d035d38b22645835cca390b887b15f6b3476b501ffa82e78f38cc88938b8afa0` |
| `10_STATE/DECISIONS.md` | 20,408 | 상태·근거·기록 | `45ee1bf655897f141945fd652d2047c271555ed9bc16dcc12f24002d76bcfd07` |
| `10_STATE/DEPLOYMENT_BLOCK_PROBE_V2_10_2026-08-03.json` | 2,142 | 상태·근거·기록 | `be1131b2c1e49c57e886e7778fc49cf3ab0ba241f62548d60ec8f3c634648b1d` |
| `10_STATE/DEPLOYMENT_BLOCK_PROBE_V2_11_2026-08-03.json` | 2,186 | 상태·근거·기록 | `ac267373c0f45712808aba7529a84acd5823adbd005659fff9dd182c3c71f7a4` |
| `10_STATE/DEPLOYMENT_BLOCK_PROBE_V2_12_2026-08-03.json` | 2,635 | 상태·근거·기록 | `a6e16a5a7e1e00138e609649c6bf6c61420c950dcd9d6b8ff9050e653b6400df` |
| `10_STATE/DEPLOYMENT_BLOCK_PROBE_V2_13_2026-08-03.json` | 2,567 | 상태·근거·기록 | `7bffe5d16b7c0cc77935032ec39225b9dfa2bf6fcfac5b8834607ff169165ba9` |
| `10_STATE/DEPLOYMENT_BLOCK_PROBE_V2_9_2026-08-02.json` | 2,491 | 상태·근거·기록 | `e308551e94ef69a19d7908ea93fc99e47d5843c36f63392f365612dc84161696` |
| `10_STATE/DESKTOP_APP_MODE_PLAN_v2.3_2026-08-02.md` | 2,457 | 상태·근거·기록 | `eaf228ceb937ed7cb85c366e61ebe2762f0b77d83c94728c03bf7ae1eeae4ec6` |
| `10_STATE/FEATURE_FIRST_ROADMAP_100_v4.0_2026-08-06.md` | 6,549 | 상태·근거·기록 | `b21dcf8bfba8b9dc4b749c9f4d77cc5e5951f0f930d0fd96c96e8f3a07540884` |
| `10_STATE/FREEFLEXVPN_PUBLIC_DEVICE_QA_v1_1_2026-08-10.md` | 9,967 | 상태·근거·기록 | `013e4741a86dfb21f2c21d2f5add313b8e616d8b9bea8e19e3a8ac22ad90e920` |
| `10_STATE/G1R_PROFILE_PEER_REISSUE_READONLY_2026-08-14.md` | 3,280 | 상태·근거·기록 | `f25d68571583e389239432c6e5a0ac09d5c93087062f578e8d6321988466a657` |
| `10_STATE/G1R_PROFILE_REISSUE_LIVE_DECISION_2026-08-17.json` | 1,474 | 상태·근거·기록 | `b3aeada75661ce2cdc7a6dd71e98f6967726dd61de6910ea15977a28285e8577` |
| `10_STATE/G1R_PROFILE_REISSUE_LIVE_INPUT_2026-08-17.json` | 781 | 상태·근거·기록 | `c8ec6c629a4881062194e99696b69f24234b57daed9d740635e4d9be5c5a2e0c` |
| `10_STATE/G1R_PROFILE_REISSUE_READONLY_2026-08-14.json` | 1,548 | 상태·근거·기록 | `ca9fa63e32d46cb9e04f93db76063d727f6d28a58a0a5f1e85d172f329234b17` |
| `10_STATE/GCP_BILLING_REVIEW_PLAN_v2.13_2026-08-03.md` | 2,696 | 상태·근거·기록 | `446ecbe5f8f6ba0c0bee3697589c87d3acfac140adb5739d206fd921440994d3` |
| `10_STATE/GCP_COST_REVIEW_PLAN_v2.12_2026-08-03.md` | 2,598 | 상태·근거·기록 | `ed99be6de728267d1de240ee552d656c62a61f18a872ff66af3cc2af587f7372` |
| `10_STATE/GCP_FIRST_NODE_PLAN_v2.8_2026-08-02.md` | 3,498 | 상태·근거·기록 | `5b5085dcd9c2545513a613f2fd6fe8ba802463fb066b6be28feac13b5c11de1d` |
| `10_STATE/GCP_READBACK_ACCESS_2026-08-18.json` | 541 | 상태·근거·기록 | `487ab756c2fa7c5efc9f2f98645e756bcb5fa74e9db7659ba17fac3e4f426b8f` |
| `10_STATE/GCP_READBACK_ACCESS_2026-08-18_2.json` | 541 | 상태·근거·기록 | `ec83a8599c745cd2e162cf881ef9bb0e450a6cb569d363667df470a1d036eff6` |
| `10_STATE/GCP_READBACK_FULL_REGRESSION_2026-08-18.json` | 12,330 | 상태·근거·기록 | `898845e0c78bba71fec6d34eb3137fcfd4740d1fc4898167a935f196ea0c9dc4` |
| `10_STATE/GCP_S1_DIRECT_EXECUTION_v2.14_2026-08-03.md` | 2,289 | 상태·근거·기록 | `c877de51c12ee08534aaa1e413d6b98e9cd47cc67830ba4c0e8366eb1dea11b2` |
| `10_STATE/GCP_S1_S2_EXECUTION_v2.18_2026-08-04.md` | 3,672 | 상태·근거·기록 | `e7297bb5eac11eeeb6fa9733fdbba7c5fa2b287353198c3037b73c6c6321cd08` |
| `10_STATE/GENERATED_GCP_COST_REVIEW_V2_12_2026-08-03.json` | 2,742 | 상태·근거·기록 | `c5738fd4f49d8bd510c43292486780a28ee90f0f3dd32daa943dde6dae4e5429` |
| `10_STATE/GENERATED_PROGRESS_V2_10_2026-08-03.json` | 2,849 | 상태·근거·기록 | `b39cee7e18efec78fc809268b35359516b15a8666217e16bdb66065aad87b296` |
| `10_STATE/GENERATED_PROGRESS_V2_11_2026-08-03.json` | 2,950 | 상태·근거·기록 | `a31030091a01112800fe1dd0b6f983742acc4981c65345fed9702e14e44bdf67` |
| `10_STATE/GENERATED_PROGRESS_V2_12_2026-08-03.json` | 3,048 | 상태·근거·기록 | `b5199f37f270df05a0a28a54b0830c72c74a5b1ab673a6f2ae3de30f32e49cb0` |
| `10_STATE/GENERATED_PROGRESS_V2_13_2026-08-03.json` | 3,031 | 상태·근거·기록 | `18033da2d78ff20c32d032c319c1168fa3e1db5c7430c4af6b1bea9d0174b958` |
| `10_STATE/GENERATED_PROGRESS_V2_14_2026-08-03.json` | 2,317 | 상태·근거·기록 | `eed6a4460b826b97e6b06cdafa2bf8c8b8d78dc96dacac233f68ac9033795f24` |
| `10_STATE/GENERATED_PROGRESS_V2_15_2026-08-03.json` | 4,498 | 상태·근거·기록 | `1005b94075e5c7e045173e025544145432b5ae0de9016d82b9dae20062b02ef2` |
| `10_STATE/GENERATED_PROGRESS_V2_15_R2_2026-08-03.json` | 4,518 | 상태·근거·기록 | `718b183ae2d9d65ae7e3ad46127813311ab94ad0a6f96e315b28f6346ffae353` |
| `10_STATE/GENERATED_PROGRESS_V2_9_2026-08-02.json` | 2,602 | 상태·근거·기록 | `8c4e3b71c596419dd2c50c415cf45b8af320516fd69a29d5443d7782e5283859` |
| `10_STATE/GENERATED_PROGRESS_V2_9_R2_2026-08-02.json` | 2,605 | 상태·근거·기록 | `ad96a802d19687d9d328e7aae8e1159536e8354478c9f691dfe1894a8ac0e8df` |
| `10_STATE/GENERIC_REAL_DEVICE_PUBLIC_QA_PROMPT_v1_1.md` | 7,139 | 상태·근거·기록 | `164f9628ae0b58cb24ba72b1100b12316e8c19ff8669ccaac97d21cd693d28e2` |
| `10_STATE/HANDOFF_EVIDENCE_2026-08-03.json` | 2,530 | 상태·근거·기록 | `c0c87a85672b434fc1b187c20b02650b644aa6da86d0a8f97bbeb1adab04dffe` |
| `10_STATE/LESSONS.md` | 3,658 | 상태·근거·기록 | `8147772b181de559938177ca2269ef20a9188c12a975431c62e10f621b4c7a44` |
| `10_STATE/LOCAL_EVIDENCE_CONTROL_SAFETY_V2_2026-08-02.json` | 4,862 | 상태·근거·기록 | `ba3240fdc7cbf1b0077305b40e78362c7c5dc8a99ec93453733b5923366c9e96` |
| `10_STATE/LOCAL_EVIDENCE_FULL_REGRESSION_CURRENT_DEVICES_2026-08-05.json` | 7,389 | 상태·근거·기록 | `9f1a42c34d6118ecb7b4f1baba4eefaceed290df753dbd82a73846a61cf8ac26` |
| `10_STATE/LOCAL_EVIDENCE_FULL_REGRESSION_USABILITY_2026-08-05.json` | 7,297 | 상태·근거·기록 | `2ca74c3ec47f8fb614d11589266429d4821b3ea84a88c3203527cd8bd70680dc` |
| `10_STATE/LOCAL_EVIDENCE_FULL_REGRESSION_V2_15_R2_2026-08-03.json` | 5,676 | 상태·근거·기록 | `e5223850c2f9a731ef2a5612bc126bba15ec8f44eb421517d7094c96777c382e` |
| `10_STATE/LOCAL_EVIDENCE_GCP_BILLING_REVIEW_V2_13_2026-08-03.json` | 2,867 | 상태·근거·기록 | `4d13e3551c9927d17af24a118fa74a14f425b5b9bebfb4ad21718c35b5589edf` |
| `10_STATE/LOCAL_EVIDENCE_GCP_CLOUD_SHELL_V2_10_2026-08-03.json` | 3,589 | 상태·근거·기록 | `f8828e4726c7bdfed5435e9fa9ebf57979baa8a8e9bf5eba6b3a25ac309284e9` |
| `10_STATE/LOCAL_EVIDENCE_GCP_COST_REVIEW_V2_12_2026-08-03.json` | 3,461 | 상태·근거·기록 | `dfa6f3bbc001145ca1f6fbb8e1008abcb1dc18c1bac3ae2e6fc6c15aac755134` |
| `10_STATE/LOCAL_EVIDENCE_GCP_FIRST_NODE_V2_8_2026-08-02.json` | 4,895 | 상태·근거·기록 | `e8500270f769fcd5c8becb4dbfe100ed377519224707d982b56f7a39e03ed951` |
| `10_STATE/LOCAL_EVIDENCE_GCP_PROVIDER_READBACK_V2_11_2026-08-03.json` | 4,575 | 상태·근거·기록 | `427057a9eec6d26857c1649373f3a9791d18c0cbf9bd217bb169c9ec1cf908bf` |
| `10_STATE/LOCAL_EVIDENCE_GCP_S1_DIRECT_EXECUTION_V2_14_2026-08-03.json` | 1,736 | 상태·근거·기록 | `a63facbd5dd3f8b7afa08263b742c5e30acbc5bf353070babd7b291df5ca58a3` |
| `10_STATE/LOCAL_EVIDENCE_GCP_S1_S2_EXECUTION_V2_18_2026-08-04.json` | 2,829 | 상태·근거·기록 | `20408876787ca634e845f16aea4fb6a0d8434f7809ca4fce676dab0f329653eb` |
| `10_STATE/LOCAL_EVIDENCE_PAGES_REVIEW_PROBE_FIX_2026-08-05.json` | 658 | 상태·근거·기록 | `56f0f08055e2966682c072a19f1a80406378589c48130c58b726e23da8d36175` |
| `10_STATE/LOCAL_EVIDENCE_PC1_FULL_REGRESSION_V2_19_2026-08-04.json` | 6,768 | 상태·근거·기록 | `e63994b6f8a77b89d07b6f17c97b53b6860c8eef0e10677a612137c00fba7b33` |
| `10_STATE/LOCAL_EVIDENCE_PC1_FULL_REGRESSION_V2_19_R2_2026-08-04.json` | 6,775 | 상태·근거·기록 | `584ede3fbe3c64918f0d2e2b74c711fca7c7e4840ad8bf0a9220a923896d78f9` |
| `10_STATE/LOCAL_EVIDENCE_PC1_FULL_REGRESSION_V2_19_R3_2026-08-04.json` | 6,737 | 상태·근거·기록 | `2d34c852f4b22dfafad0365546bb920f23184f90f0cb553e7acec475d174fa27` |
| `10_STATE/LOCAL_EVIDENCE_PC1_V2_19_2026-08-04.json` | 2,020 | 상태·근거·기록 | `d53c719fbda723e99e52b8a33fae137799b4e9224f74d139cfeed52a11aabdd7` |
| `10_STATE/LOCAL_EVIDENCE_PC23_FULL_REGRESSION_V2_20_2026-08-04.json` | 6,990 | 상태·근거·기록 | `37173d08ae0aedfb0ca92e95a69307b9431633ba101d8089c41328b1ee23e8d4` |
| `10_STATE/LOCAL_EVIDENCE_PC23_V2_20_2026-08-04.json` | 1,865 | 상태·근거·기록 | `6d02973491e0e27472794a8a746eee48ec44a4ff6e53a99974cd3b488c3fe2c1` |
| `10_STATE/LOCAL_EVIDENCE_PC_PUBLIC_FULL_REGRESSION_V2_21_2026-08-04.json` | 6,981 | 상태·근거·기록 | `0d786e32a1ffe0342ead0641f077361f3692c6ea65d03e64d151a10f6b3f711e` |
| `10_STATE/LOCAL_EVIDENCE_POLICY_DRAFT_PACK_V0_1_2026-08-03.json` | 984 | 상태·근거·기록 | `8dc6b69d937536581ac04f7ea132aee80759acdad9431e248fa1a01e9150b139` |
| `10_STATE/LOCAL_EVIDENCE_PROGRESS_DASHBOARD_V2_9_R2_2026-08-02.json` | 2,624 | 상태·근거·기록 | `032fe5e46b2a1c9cb9412244625005954d85d6749dfba737cf998b7744e6f482` |
| `10_STATE/LOCAL_EVIDENCE_PWA_API_READY_V2_2026-08-02.json` | 5,224 | 상태·근거·기록 | `22f8c98468444c590645fb504b38330e7a0f1ad149fee94c6874986bbba27ae0` |
| `10_STATE/LOCAL_EVIDENCE_R6_CANDIDATE_BINDING_V2_6_2026-08-02.json` | 1,901 | 상태·근거·기록 | `252ad785805196cccbdd7389f25a567b2a5c8eb4d63e5882467ecdf8d06efdb5` |
| `10_STATE/LOCAL_EVIDENCE_R6_EVIDENCE_CHAIN_V2_7_2026-08-02.json` | 2,226 | 상태·근거·기록 | `e215d2526f249bad471e7ad705e189dab3cab3b5f0b29e9842cc1f177f2c6d1e` |
| `10_STATE/LOCAL_EVIDENCE_SERVER_ADAPTER_KEYGEN_V2_2026-08-02.json` | 5,636 | 상태·근거·기록 | `cea8ee07a1c45a49bba568964c71a04ffe44f078f7e29a048baa767d971bacb6` |
| `10_STATE/LOCAL_EVIDENCE_SERVICE_UI_V2_6_FULL_REGRESSION_2026-08-05.json` | 7,187 | 상태·근거·기록 | `246b5074082a9c8fb3df4ef30e6ccfe1f19cb5371a38b67cdabb4ebfe5c7a2fe` |
| `10_STATE/LOCAL_EVIDENCE_SERVICE_UI_V2_6_FULL_REGRESSION_R2_2026-08-05.json` | 7,150 | 상태·근거·기록 | `c49c071edd518175e6ebe71b49c4f9905a8cfc82f3b5082aa99db58a83e6f4a1` |
| `10_STATE/LOCAL_EVIDENCE_SERVICE_UI_V3_FULL_REGRESSION_2026-08-05.json` | 7,369 | 상태·근거·기록 | `684c09c97f05b7eb891567a0faad54d7094ec910554a6b61daca632d2d6373af` |
| `10_STATE/LOCAL_EVIDENCE_SERVICE_UI_V3_RECONCILED_2026-08-05.json` | 1,726 | 상태·근거·기록 | `a59a860543e26f5cb25ebc172b7ed98a31fe46af3e8ab96ade9a6c7ce8abea89` |
| `10_STATE/LOCAL_EVIDENCE_V2_16_2026-08-03.json` | 6,202 | 상태·근거·기록 | `ee0bf99c2181e852b4e9bcf96b6df228bed7463d04ae2c5f0d7c4121423d2566` |
| `10_STATE/LOCAL_EVIDENCE_V2_16_R2_2026-08-03.json` | 6,209 | 상태·근거·기록 | `4bc83cceb9f14b110d0b7de5bdf79408b7dd0440e5ced8d5c541ef5e3bb074ec` |
| `10_STATE/LOCAL_EVIDENCE_V2_17_2026-08-03.json` | 6,509 | 상태·근거·기록 | `1dd0888f13bb4bb7a694c85626d92bc894f55297752c1d9c4d3e5f115d678ec8` |
| `10_STATE/LOCAL_EVIDENCE_V2_17_R2_2026-08-03.json` | 6,476 | 상태·근거·기록 | `02438611ff1668a0de7f3e990a092ed7fa1d54346f267e8408b0146765217290` |
| `10_STATE/LOCAL_EVIDENCE_V7_6_PROGRESS_AND_LANDING_V2_15_R2_2026-08-03.json` | 3,315 | 상태·근거·기록 | `d4e2c24380c1eedbbb48dfb12ef054ab044be986f713eabe561c2842990729ca` |
| `10_STATE/MOMENT_DESTINATION_PLAN_v2.1_2026-08-02.md` | 8,667 | 상태·근거·기록 | `3e3bdd4b19c497228702be4a73f2758300867769b2a1fa5448ca812a6d3b15fb` |
| `10_STATE/PC_COMMERCIAL_READINESS_PUBLIC_BASELINE_2026-08-12.json` | 860 | 상태·근거·기록 | `3406dba9b09931d0f41448298a024863edd986c50e00f6666008086d51d98c8a` |
| `10_STATE/PC_WEB_MISSION_V2_19_PC1_2026-08-04.md` | 4,544 | 상태·근거·기록 | `20b524541d9b1e184c7ec7b5760c19eb24c3caac443ba4f00bafc74f1cef3ede` |
| `10_STATE/PC_WEB_MISSION_V2_20_PC23_2026-08-04.md` | 3,375 | 상태·근거·기록 | `380483882a018eed0c6fd9ed58bd4befd00409d2e7c40343b2b91d204879f544` |
| `10_STATE/PC_WEB_PUBLIC_COMPLETE_V2_21_EASY_2026-08-04.md` | 3,059 | 상태·근거·기록 | `2910a8e66b0608bab2be6d127ffaf3f057134daa3b1fefe3546622cc76eaef35` |
| `10_STATE/PLAN.md` | 2,625 | 상태·근거·기록 | `115d5c19f101af8680c12c6d724ca8a6320196babfba45e93f5177a8d3653d52` |
| `10_STATE/PLAN_v2_2026-08-01.md` | 4,760 | 상태·근거·기록 | `c7199bc67d8533a525b84f0f5beaf8afa23356625809d1805b6f7824dfc99bd6` |
| `10_STATE/POLICY_CODE_CONSISTENCY_v0.2_2026-08-03.md` | 2,930 | 상태·근거·기록 | `6788890fb841ffa15d08b42bba282a54350e6386b47816e261946a3cf9517aa4` |
| `10_STATE/PRIORITIES.md` | 5,244 | 상태·근거·기록 | `6cde370cf83ad7d84fbc0e198d76ea13d7b3bd8d9619bcd8a0d10c9776201629` |
| `10_STATE/PRIORITIES_v2_2026-08-01.md` | 10,658 | 상태·근거·기록 | `da56dfbe73295b1bd2295dc909f528c1678e60f5f02784f3e28cac4164b5dc8e` |
| `10_STATE/PRODUCT_UX_100_PRIORITY_CATALOG_v3.0_2026-08-05.md` | 10,961 | 상태·근거·기록 | `7af5e687d00f50d71ddfa62ffeac70bbefc84139417157a994e21fe0a67f5e88` |
| `10_STATE/PROGRESS_DASHBOARD_ALWAYS_VISIBLE_2026-08-05.md` | 1,004 | 상태·근거·기록 | `166d169985c8af5bca6fefb67c5cb619d52e974b720043941bde01996be65578` |
| `10_STATE/progress_dashboard_v2.10.json` | 5,370 | 상태·근거·기록 | `9e71e86ff0b97e0d548111ebf540a4906a2ca10c66b4fccbadb0acd9a8512e25` |
| `10_STATE/progress_dashboard_v2.11.json` | 5,477 | 상태·근거·기록 | `05b6f449c18b29e3cb4b8516d3d20d56ff9247aa038578bd49f592792bb85e76` |
| `10_STATE/progress_dashboard_v2.12.json` | 5,574 | 상태·근거·기록 | `c83ed7d2af1ace84413fc33c9041d0834c12a28bb532d228d08894880bc92a22` |
| `10_STATE/progress_dashboard_v2.13.json` | 5,557 | 상태·근거·기록 | `87c47bf36ae77625e8fad973afc6960b79941e4832c688b6553972dcf64c47d1` |
| `10_STATE/progress_dashboard_v2.14.json` | 4,704 | 상태·근거·기록 | `11ccb7d1d7a137de101c8fe08a4351ba636b129af72e2e863a4285cc6a64a980` |
| `10_STATE/progress_dashboard_v2.15.json` | 7,530 | 상태·근거·기록 | `8850a25d9309d74ff343d3a2b8f3b0714166c5a833e1fb2d2966dc6f398d784d` |
| `10_STATE/progress_dashboard_v2.9.json` | 5,098 | 상태·근거·기록 | `75591480269229703b28718d427ed7ca8f0d836e7e67f813b02b8ed35a63592c` |
| `10_STATE/PUBLIC_EVIDENCE.json` | 1,988 | 상태·근거·기록 | `96ef4adbb3bf6f930cdd24b4c9161b31bed400a67c51d3b0de00183e8ba5fb5b` |
| `10_STATE/PUBLIC_EVIDENCE_PC_WEB_V2_5_2026-08-04.json` | 721 | 상태·근거·기록 | `e8ce315f635d8729d60413ba885434262d2dca0a79d11bcfbcac02ae06576224` |
| `10_STATE/PUBLIC_EVIDENCE_R1_PAGES_2026-07-31.json` | 939 | 상태·근거·기록 | `1fa5ad2124ed1c58451771383e08a023ae60e69d9af26354f0075f8e3cb8ec7c` |
| `10_STATE/PUBLIC_EVIDENCE_R2_UI_V1_1_2026-08-01.json` | 810 | 상태·근거·기록 | `5c4c3bf982bd87b48f988cad27a9043e162b42d6963c9157eb1d97c61bcb650c` |
| `10_STATE/PUBLIC_EVIDENCE_R5_R7_UI_V2_2026-08-01.json` | 1,524 | 상태·근거·기록 | `9e01e764ad6fa686e5c12b6a8e7a9f84a607f68c6a6bb993fbe8b31fbc269ce7` |
| `10_STATE/PUBLIC_EVIDENCE_R6_PWA_API_READY_V2_2026-08-02.json` | 2,383 | 상태·근거·기록 | `b7b735a647af7d648d2e80244905495513a65fce177c1843ae3979fb82f27af6` |
| `10_STATE/PUBLIC_EVIDENCE_R7_MOMENT30_V2_1_2026-08-02.json` | 2,635 | 상태·근거·기록 | `ab336c8abcb67a2f05e46cf4680d87d3b43517c018cf6649b900a294cfabf50e` |
| `10_STATE/PUBLIC_EVIDENCE_R8_ALL_DEVICES_V2_2_2026-08-02.json` | 2,933 | 상태·근거·기록 | `c2de3f32bff449bffce235989b10a9b22ebf78e80ff47315c1bf552ee0d7da6a` |
| `10_STATE/PUBLIC_EVIDENCE_R9_DESKTOP_APP_V2_3_2026-08-02.json` | 2,081 | 상태·근거·기록 | `a456433410a3994479c5b79f532dea9b97ec3d10bf6d2b95414135d932db86b4` |
| `10_STATE/PUBLIC_PC_VERIFY_2026-08-18.json` | 883 | 상태·근거·기록 | `d2f1ee5a03dcc47c3b4f0be9c7bb1c41cc77e0c53a822587d44484cab3194433` |
| `10_STATE/PUBLIC_RELEASE_SERVICE_UI_V3_2026-08-05.json` | 1,198 | 상태·근거·기록 | `b2f6feb44c1a7df22ee6201442f356e8b559f69d44d66226c0e57455332ffba0` |
| `10_STATE/PUBLIC_SERVICE_VERIFY_2026-08-18.json` | 871 | 상태·근거·기록 | `601b8a5f8c11d8df16ff21ba5e92edcfef8991dd0666938731f38374be8bed44` |
| `10_STATE/R6_CANDIDATE_BINDING_PLAN_v2.6_2026-08-02.md` | 2,382 | 상태·근거·기록 | `7ddf78996b23fa60f36348e4149f3a507dd5be52d5f115ca6506e09f7de4a0ac` |
| `10_STATE/R6_CONFIG_PREFLIGHT_PLAN_v2.5_2026-08-02.md` | 1,429 | 상태·근거·기록 | `f7efe3f302a8a0603675338080b598e1fbc926dc201beaac99d114a1133093af` |
| `10_STATE/R6_EVIDENCE_CHAIN_PLAN_v2.7_2026-08-02.md` | 2,347 | 상태·근거·기록 | `2edf4cbc8ca0788cf81f65e3fd364f094766c0917f2096b76ee321534a2ecc25` |
| `10_STATE/R6_SERVER_PREFLIGHT_PLAN_v2.4_2026-08-02.md` | 2,021 | 상태·근거·기록 | `f2deb30623156f197ae1dfc988aec53e91ee87e51cfc4891dc1d0f8317f57b1f` |
| `10_STATE/RELEASE_DIFF_V2_16_2026-08-03.json` | 2,982 | 상태·근거·기록 | `b6c45b274c1efe5a744db7c6f40491b5d337bc80bc2251ac76da9825d61c6b5a` |
| `10_STATE/RELEASE_DIFF_V2_17_2026-08-03.json` | 4,010 | 상태·근거·기록 | `f9ee2b10545777b1f969dcac2c973dffb39ed39f7f0f546333bb83fd6f065137` |
| `10_STATE/RELEASE_DIFF_V2_17_R2_2026-08-03.json` | 4,010 | 상태·근거·기록 | `ead8cc15ae7d6a642a84c7bfa7ff60b15cf73e734a4ea672bded2deb3793151a` |
| `10_STATE/RELEASE_DIFF_V2_19_PC1_2026-08-04.json` | 5,887 | 상태·근거·기록 | `a0776554ef92a5620e7b57d35fa26f89cf91285627c8617a74a4c25fe8104abf` |
| `10_STATE/RELEASE_DIFF_V2_20_PC2_PC3_2026-08-04.json` | 6,462 | 상태·근거·기록 | `b200dcbebdc4234c970f7689835c4a4d2d3b113c0c4936448d1d572c9b5a0713` |
| `10_STATE/RELEASE_DIFF_V2_21_PC_PUBLIC_2026-08-04.json` | 6,808 | 상태·근거·기록 | `5a9fc96e1239fbce11a90ec921fadaf23870fc8336e956d74ba58b3cb95ef3b8` |
| `10_STATE/RUNTIME_ACCEPTANCE_PLAN_v2.16_2026-08-03.md` | 3,301 | 상태·근거·기록 | `2cb0ae83282953152b20bf22c91d9ede6101bf78941a30b31e8238d44a137f84` |
| `10_STATE/RUNTIME_EVIDENCE_CONTRACT_v2.17_2026-08-03.md` | 2,213 | 상태·근거·기록 | `d2bfab19ba8ba44f6172f1a20a08d92291e181a4882c030519a8536c642da254` |
| `10_STATE/SERVICE_UI_UX_REDESIGN_V2_6_2026-08-04.md` | 15,156 | 상태·근거·기록 | `8b71465d1db07a3acc7feae1821d70aefd7fcee1478462ca124ca25322e99b77` |
| `10_STATE/SERVICE_UI_V2_6_IMPLEMENTATION_REPORT_2026-08-05.md` | 6,563 | 상태·근거·기록 | `ef94c2224624f0a85e8912d79f8ddad88bf81a09edb6aedeed9acb3135405973` |
| `10_STATE/STATE.md` | 3,863 | 상태·근거·기록 | `fd4bd20249e87d99af8051d6f4b0b478d1d16ef51552474e2dc461431cc0e4f0` |
| `10_STATE/TEST_AND_USABILITY_STATUS_2026-08-05.md` | 2,081 | 상태·근거·기록 | `55c11f94f6396ce4dbfdb79784c230438f5992bb283b210f86fa50542a0f174c` |
| `10_STATE/UI_DESIGN_v1.0_2026-08-01.md` | 3,807 | 상태·근거·기록 | `9ab55106bfabfa486e18c69ac41643ee659374bd2e22611f278fe7dbf1f426f0` |
| `10_STATE/UI_DESIGN_v1.1_2026-08-01.md` | 2,814 | 상태·근거·기록 | `16b3f04de94b4c27ed18147f63a30e57cc7859757c7b82fbf2b15fe67b9146bb` |
| `10_STATE/USABILITY_SIMULATION_1000_2026-08-05.json` | 1,305,911 | 상태·근거·기록 | `e1027a5d9991b88d4ce1dcfe31956f69f2dab34675c0381365c4e805e31d8853` |
| `10_STATE/USABILITY_SIMULATION_1000_REPORT_2026-08-05.md` | 5,258 | 상태·근거·기록 | `45c29d9f8f0341062de3a893aa8054f687d645f86cc4d51394c833800ab655d5` |
| `10_STATE/USABILITY_SIMULATION_A56_1000_2026-08-05.json` | 1,305,911 | 상태·근거·기록 | `e1027a5d9991b88d4ce1dcfe31956f69f2dab34675c0381365c4e805e31d8853` |
| `10_STATE/USABILITY_SIMULATION_A56_1000_REPORT_2026-08-05.md` | 5,258 | 상태·근거·기록 | `45c29d9f8f0341062de3a893aa8054f687d645f86cc4d51394c833800ab655d5` |
| `20_SRC/app/__init__.py` | 150 | 현행 소스 | `8558798754cf10f51a8b405c87556ed5337ed3b60540435f936b3aa6406fdc7d` |
| `20_SRC/app/client_keygen.js` | 6,030 | 현행 소스 | `829abf635971782969044a1d6295937110b80bee8fa328fda822f26a269e17f5` |
| `20_SRC/app/collaboration_gateway.py` | 28,420 | 현행 소스 | `4f7e4a04fe66fde6ab69fa9110fa6e86fa4769f62d59766266f733125b5c2abd` |
| `20_SRC/app/collaboration_http.py` | 19,186 | 현행 소스 | `a031101bb4807f8438d9e941ca8e1db95d753e926a8c08a85af21c150e9a0b96` |
| `20_SRC/app/collaboration_runtime.py` | 11,816 | 현행 소스 | `5f73cbdaa2ea1140a9552f6ac36effdd36451c64c4bb6519a7c2d76a0ce440ad` |
| `20_SRC/app/collaboration_workspace.py` | 10,228 | 현행 소스 | `dde9ffbafea4fb4dececee7761ce549c5fcc7cb5a4b9bd39aa295bc0434fb11f` |
| `20_SRC/app/commercial_readiness.js` | 3,235 | 현행 소스 | `8471d1cc238317e6ee542c21f297cd5dd945a66dc9e9116fd8b5b76bcff8369d` |
| `20_SRC/app/connection_check.py` | 3,971 | 현행 소스 | `fe2d3a41a005fd432a0e9a5aa078538c04d2a04c192657b48045fb18b4ce71f9` |
| `20_SRC/app/control_api.py` | 32,803 | 현행 소스 | `50953a6d767b2b882e0e54895dc1086b8bc31911ca17c38cca2bdec0880f5158` |
| `20_SRC/app/control_http.py` | 7,007 | 현행 소스 | `518454189416c605efeaa1b5dd1f3a0efb59ba364e58baa495351a989b77bc37` |
| `20_SRC/app/control_runtime.py` | 5,935 | 현행 소스 | `6c4fad5ae0fc69fd7f87ac3932b867248d6aa26bccd0271babfdfffbb4a48058` |
| `20_SRC/app/db_migrations/001_v2_alpha.sql` | 7,006 | 현행 소스 | `b307c3c7f8406dec9796e012c332b4a97bc710692cf268ef77048df4604f831e` |
| `20_SRC/app/gcp_node_admission.py` | 5,341 | 현행 소스 | `327d13b9e2910b822195521db12cc6156073dbd172243e8fc0eb66f5e81ceb55` |
| `20_SRC/app/mobile_readiness.js` | 3,192 | 현행 소스 | `d31598333a9fd3a2f026b4cd2f1d49fe04fee6d091929281330822459ee0539b` |
| `20_SRC/app/moment_catalog.js` | 12,739 | 현행 소스 | `60d883b1146520ee73f3262a7f7aba402b94e1e0aa7471864db67d7a4ad309c0` |
| `20_SRC/app/pc_readiness.js` | 3,611 | 현행 소스 | `235632f7d7a41efd123743cedb951232b2cfebbb388948c5b213241061cf35f8` |
| `20_SRC/app/platform_evidence.py` | 12,378 | 현행 소스 | `3cb7187abe09a6d1118f40f38f5b0dd4dbf928d0d8651c269dfd7c9c0fe4be48` |
| `20_SRC/app/platform_support.js` | 5,308 | 현행 소스 | `d176e36d3b325fbed581345b70bdb0ff6629952d7c7d565ecbde2b867a486e42` |
| `20_SRC/app/preflight_evidence.py` | 2,117 | 현행 소스 | `0f8e84f13007ca27ed71e4faf96ebd5fffad37620dde54de857795bbfd3715e5` |
| `20_SRC/app/profile_reissue.py` | 11,330 | 현행 소스 | `40c6cd74f76729b2b94d7e1f49a81cc01c622031e3029ae6e929206b534bb01c` |
| `20_SRC/app/pwa_api_client.js` | 7,120 | 현행 소스 | `4c2dbf537aa18c80de265ef237f5b5028a0253bdbd0bd922aa012ed6d04bc874` |
| `20_SRC/app/pwa_runtime.js` | 46,963 | 현행 소스 | `23c43d29c4774cd01a970e1bcfcfb61fa86d9b1466a101d2411cb3769e12b77c` |
| `20_SRC/app/quota_ledger.py` | 6,602 | 현행 소스 | `423aa37a289c40a4fd388215228f4a1a12dd430421e0f1dcb3451136e9980794` |
| `20_SRC/app/r6_preflight.py` | 7,578 | 현행 소스 | `00759fdc8bde9f4d51ee2927a2b1b6a3bcc651ca55a6c76305645a46334e5948` |
| `20_SRC/app/referral_ledger.py` | 18,855 | 현행 소스 | `a108cf7a6538b36e90c1828237c0175cccda1010890da0bd824f02c2fbc2c086` |
| `20_SRC/app/release_95_gate.py` | 11,603 | 현행 소스 | `e24aad8d62e1c95d07f0ae6b47d32472c545db914244e403a2cf59d3fb87384e` |
| `20_SRC/app/runtime_acceptance.py` | 13,793 | 현행 소스 | `40d6ba2fbfe3d49fb563e287936d06e77f2ee6c58b4a342c9b25d29bf782a06d` |
| `20_SRC/app/runtime_evidence.py` | 10,790 | 현행 소스 | `4e46349bcbb77c1d4f583ea3242ea4edb10b2c099705be7ff95f92661d041eac` |
| `20_SRC/app/safety_contract.py` | 5,104 | 현행 소스 | `d991692b3ad5673948e05acefea773618a1f2b61c9d6a56d544def55d8b10f64` |
| `20_SRC/app/server_catalog.py` | 12,501 | 현행 소스 | `f4c13899a1209e63bbfd8b759d0430f8abdc3aa832b3ec2bc0491496092a27b5` |
| `20_SRC/app/ssh_node_adapter.py` | 15,418 | 현행 소스 | `51a71a2c6c86896ffc029422aa3fde6b88e371c0b97d3bee85081f60a804b7ad` |
| `20_SRC/app/TELEGRAM_FLOW.md` | 1,804 | 현행 소스 | `7d6e7b41e06ad13ccd1e413b0d1be57bfb30375ae4fc6ddc47d8dd8dff811896` |
| `20_SRC/app/telegram_flow.py` | 2,724 | 현행 소스 | `1d1c21a510d5d9e9390201acd06d0cf2ccb7b17773da9de7758cae70b0f2105c` |
| `20_SRC/app/telegram_onboarding.py` | 12,255 | 현행 소스 | `3c0d29d4458a20fda737439fc2c2307fb6054177661aaf2ef667e609a7319292` |
| `20_SRC/app/usage_meter.py` | 10,896 | 현행 소스 | `048db309ce5b48e1f8c9eb38eaaac1050c4f0d13e412e8eda58a7fffedad343c` |
| `20_SRC/app/wallet_ledger.py` | 15,230 | 현행 소스 | `34aa8f3171503434303f8b33f702d24c09e5e593e7c38b1221c6709bacd81009` |
| `20_SRC/build_app_v2.py` | 72,955 | 현행 소스 | `8a5984271d8fe413a77a78cb82926b4180d70dbb3f81a4aaeed30bf3c551f3c7` |
| `20_SRC/build_web_assets.py` | 8,228 | 현행 소스 | `749d54be583206523c1f8615eb783a91a349f44f5e02d0d928a1ba52377443d3` |
| `20_SRC/cost_model.py` | 23,110 | 현행 소스 | `82745837a89431c5f6670d3aba33ed6026f335d649859586a8732660c8a028d6` |
| `20_SRC/docgen/build_app_service_plan_v2.py` | 16,467 | 현행 소스 | `f7e83942ae3e4f1983d361447b4a09d0941bac6d17f2d13cd1843f688fde97cc` |
| `20_SRC/docgen/build_dev_execution_plan_v2.py` | 3,024 | 현행 소스 | `a43fbba1172c8e8b60e227bc41b50ec86b4e400a5003c2abc14ef52313aaee4f` |
| `20_SRC/docgen/build_freeflex_business_plan_v1.ps1` | 9,121 | 현행 소스 | `ccfc002e065d9ea6d057917d7c43de6a968b81e44d21b22b66886789dd2f44ba` |
| `20_SRC/docgen/build_freeflex_dev_plan.py` | 3,022 | 현행 소스 | `c141d279cb8ad8344325b89449d7d76f2352cdfffcfb6decc77e776574209716` |
| `20_SRC/docgen/doclib.js` | 9,061 | 현행 소스 | `3649a224dca3ec1bfb425a837b98003f7d286b70660dc311ca6a7d07a7078cc1` |
| `20_SRC/docgen/gen_dev.js` | 24,593 | 현행 소스 | `b039e0cd2460a48f65aa06d6ce78f7645cebd91f4b6aafd2c6443fb1bc9d95ff` |
| `20_SRC/docgen/gen_plan.js` | 28,303 | 현행 소스 | `86a5515ceaf6c0faddbf45f7377fb745e2318f9ab8b31e20032ad0c24e376214` |
| `20_SRC/github_pages/.gitignore` | 32 | 현행 소스 | `5252271e8c7c9d24b830d2de69c0ddd2fd6a436fb251a4168a1f5662cedca9b7` |
| `20_SRC/github_pages/app-qr-evidence.json` | 289 | 현행 소스 | `a82ddbc9cdac7d2547ca019dfaab7bffe8c015a34c3254f91fa1b09242163528` |
| `20_SRC/github_pages/app-qr.png` | 2,996 | 현행 소스 | `bcad7f407d0f636ec0fb34a996b97e2c7cda5a7805b0dc367186b0b0292f6b12` |
| `20_SRC/github_pages/icon-192.png` | 1,142 | 현행 소스 | `38ad89154e738dec4a896841faeb76dc77b57b9f5b6ae0a1f7ee70cb5e2d44dd` |
| `20_SRC/github_pages/icon-512.png` | 3,490 | 현행 소스 | `1711cae2a41aa2342e3fbb01f44d2e494382d859574848c5cc950824ab5aebc5` |
| `20_SRC/github_pages/pages.yml` | 7,207 | 현행 소스 | `488168871bfc2babbdead9ce7773720208d642616b0a87613933cf1f5b7998bd` |
| `20_SRC/github_pages/README.md` | 591 | 현행 소스 | `71ded1391e30cefaddbc06acf04a0fd78c420ff45d3784b35b244eee378977f5` |
| `20_SRC/github_pages/sw.js` | 1,336 | 현행 소스 | `8f68509af2358b86628c197df511795629488d42bd96f04bf895ac2243d28602` |
| `20_SRC/github_pages/tools/build_app_qr.py` | 1,646 | 현행 소스 | `25fd23b65e84e31533c8da1257da5324e057c2097630d2a0841ae35db61109bc` |
| `20_SRC/github_pages/tools/build_public_manifest.py` | 1,865 | 현행 소스 | `0ac5da151b1b733711a9f65b8f2c81a73e45e517ccb7d85fe5859e99614465f5` |
| `20_SRC/github_pages/tools/check_inline_js.mjs` | 430 | 현행 소스 | `31914421634965ac9040849403faedeb94d754432d34308909961fddf0954f7d` |
| `20_SRC/github_pages/tools/verify_app.py` | 6,440 | 현행 소스 | `70a567d1935574d463d9ed3afe0af6af876be89eb22edcc7834e477435c12cb8` |
| `20_SRC/html_templates/app_v1_1.html` | 54,972 | 현행 소스 | `d4d5c654f556593a074d565b6673f86c4fa1339e4382011536d6352746014d48` |
| `20_SRC/html_templates/app_v2.html` | 192,634 | 현행 소스 | `ab06f0b0b9f264b2a429ef329bcc2c7d94d7d0ac023faf03e85e968c47054de7` |
| `20_SRC/html_templates/collaboration-portal.js` | 5,776 | 현행 소스 | `af979c5ddfab78070b228e01efade57ad574cc4d870cd9b239d6f15189e791c7` |
| `20_SRC/html_templates/collaboration_portal.html` | 3,703 | 현행 소스 | `39cac1da05bea77ccdf4392130d757cb78557992b68b81653c51b1b2d56af40a` |
| `20_SRC/html_templates/country_tpl.html` | 13,787 | 현행 소스 | `30e02f15a09bc2d2888a07c46154963a0e5a65e256eb365aa68f905a9ab9109b` |
| `20_SRC/html_templates/d1_tpl.html` | 14,952 | 현행 소스 | `1886c869c3885b801d46f5d2c2208b3adab38c1cd8eee76b5938236424ef9258` |
| `20_SRC/html_templates/development_dashboard.html` | 8,355 | 현행 소스 | `4e252002afd8ddb3e046fbf22ade3852c95584381e25d2907c311a5731b38cdb` |
| `20_SRC/html_templates/gcp_billing_review_v2_13.html` | 19,548 | 현행 소스 | `64996497c1059957357aa4a6e50360c622ab94592e51b5fa80ae15849101bfdd` |
| `20_SRC/html_templates/landing.html` | 24,269 | 현행 소스 | `929fbc4d135f1caf2cb6a174298df92127cfc9af8544e3b213acee9bb5dca8b0` |
| `20_SRC/html_templates/opt_tpl.html` | 13,942 | 현행 소스 | `ce4d5b239c5e474b901d05d4515004a12767d0f90d25fb24316937717c22cd74` |
| `20_SRC/html_templates/price_tpl.html` | 25,967 | 현행 소스 | `db0c34c3d0f555ba84392af7782e209586b00f303057f6d015bc08b8ee87fe8d` |
| `20_SRC/html_templates/runtime_evidence_workbench_v2_17.html` | 11,074 | 현행 소스 | `5db311a1a8ef1097e66909272a297e91f2f203434504b2f1404e0b6bb7ce3f0e` |
| `20_SRC/html_templates/service_global.css` | 4,628 | 현행 소스 | `1ef6c6f5391c962c3e89fcce873d7935382946c3930e4badcf0247838d6892de` |
| `20_SRC/html_templates/service_shell.css` | 39,167 | 현행 소스 | `e6cd9ec99f987db5fcfe99c370a21a07ce9c260899a0b83baddc0991098f80dc` |
| `20_SRC/html_templates/service_shell.html` | 58,485 | 현행 소스 | `faea62a6ce23a52e822e1511e110cccdeba0ad705d26a0554afd2522f4fd33b2` |
| `20_SRC/html_templates/simple.html` | 15,881 | 현행 소스 | `bbdbcb9b5a32c866e09f0ba867af816e17a3317f6a6888f023912817fa4d5eb5` |
| `20_SRC/html_templates/template.html` | 59,524 | 현행 소스 | `07bddffe6e1b424ade2c00ede8af09e96543467bcf3355c9dee9709e40e031cc` |
| `20_SRC/icons.py` | 1,561 | 현행 소스 | `b3a87e9149f2428b257fdafbf0e802111692a17992b47848f578c28e8d5a8742` |
| `20_SRC/infra/__init__.py` | 58 | 현행 소스 | `92a7d5c6a6b882fe54d1efac554fc018907d3151dbcaf961444118f8eddc77d8` |
| `20_SRC/infra/cloud_init.py` | 12,865 | 현행 소스 | `d3ce77f0645fa865517d385525f18dd601fcc431361ca2276dc3408798a5aadb` |
| `20_SRC/infra/exit_admin.py` | 13,684 | 현행 소스 | `0782229826da1e0f8a0a2fc1d941992441d16ea54b22a5768a3d26668f3236c9` |
| `20_SRC/infra/gcp_cloud_shell_bundle.py` | 15,393 | 현행 소스 | `df6f4c14b19e0035d4b8019d6d2dd5eb6ebf235c1b290c6258bbf13941b12ed9` |
| `20_SRC/infra/gcp_cost_review.py` | 5,439 | 현행 소스 | `ec8c63514ad07f3c9ea034fc9f278f6890b98181a8f5c524614c5f8a473a6c78` |
| `20_SRC/infra/gcp_node_plan.py` | 5,460 | 현행 소스 | `6cab609f9de47526ae75b7c9e0bb3871fa27fe536ce0a4b7e827ecfce484e2f9` |
| `20_SRC/infra/gcp_provider_readback.py` | 9,901 | 현행 소스 | `6d9bca09e3938a775af3b861a2db633d0c62235888d5cefbe6f9983478b61fbe` |
| `20_SRC/infra/gcp_readback_access.py` | 7,343 | 현행 소스 | `78b751882dddc2cf36b77ae4bca05e631458f752e851324be8a65caa2399ba8f` |
| `20_SRC/infra/peer_bundle.py` | 9,582 | 현행 소스 | `9d568c2d3e88cc70f697b0e670d3a5ccba2f39a5d29f4b432aaf4f46c96ecbfb` |
| `20_SRC/infra/quota_agent.py` | 17,530 | 현행 소스 | `ecc17955535b941651c1fd1f103494f7c91174ffb17603b3aba7164850016ead` |
| `20_SRC/infra/README.md` | 13,085 | 현행 소스 | `1dd11746955fe20b7c7492f2d77e6f61cce89eb94a0f85963a1405aadccf646d` |
| `20_SRC/infra/requirements-peer.txt` | 57 | 현행 소스 | `fb468dcc3a4d16a3f1b5b54b23a4b3923a406846f6e504f22e4911f58e8c095e` |
| `20_SRC/infra/telegram_bot_config.py` | 1,632 | 현행 소스 | `24510fe9ad7df181079948b67e5866974935364f375ad46cd9aac1d7054b6733` |
| `30_DEPLOY/app-qr.png` | 2,996 | 공개용 결과물 | `bcad7f407d0f636ec0fb34a996b97e2c7cda5a7805b0dc367186b0b0292f6b12` |
| `30_DEPLOY/app.html` | 295,739 | 공개용 결과물 | `7bf68c899471f4e7d700399a77f62846c0897ee5d77d93a78959ac38eb819b11` |
| `30_DEPLOY/client_keygen.js` | 6,030 | 공개용 결과물 | `829abf635971782969044a1d6295937110b80bee8fa328fda822f26a269e17f5` |
| `30_DEPLOY/collaboration-gateway/Dockerfile` | 839 | 공개용 결과물 | `87b0168d86dd50235b9527a7615453bc061063b90a3402a237a493ba3ac781e3` |
| `30_DEPLOY/collaboration-gateway/README.md` | 2,822 | 공개용 결과물 | `2c9ebdb01618c264dea7d206fa80d8842d07079fb3def7d5d1be2e13d73e1216` |
| `30_DEPLOY/commercial_readiness.js` | 3,235 | 공개용 결과물 | `8471d1cc238317e6ee542c21f297cd5dd945a66dc9e9116fd8b5b76bcff8369d` |
| `30_DEPLOY/development-dashboard.html` | 18,620 | 공개용 결과물 | `15a9005b07e95a7a1b2fa6de030f79a18e2acbd77906c6e9f61ad632e5c95ce6` |
| `30_DEPLOY/FreeFlexVPN_1일오픈_체크리스트.html` | 37,953 | 공개용 결과물 | `8be9f9ae64bc908fa2b4dc1e893d5a42cadbc7820eb9d969660345a7176b2616` |
| `30_DEPLOY/FreeFlexVPN_비용계산서.html` | 38,866 | 공개용 결과물 | `b58e45eb62fa0a29000dfeff965dd5952549582e29d47792c03b4f2e8cc84af9` |
| `30_DEPLOY/index.html` | 34,526 | 공개용 결과물 | `d7f4f0a24c995a8687c3250f6d804338e09890aba3b2cfa7dbc5c4bd7ba35367` |
| `30_DEPLOY/mobile_readiness.js` | 3,192 | 공개용 결과물 | `d31598333a9fd3a2f026b4cd2f1d49fe04fee6d091929281330822459ee0539b` |
| `30_DEPLOY/moment_catalog.js` | 12,739 | 공개용 결과물 | `60d883b1146520ee73f3262a7f7aba402b94e1e0aa7471864db67d7a4ad309c0` |
| `30_DEPLOY/pc_readiness.js` | 3,611 | 공개용 결과물 | `235632f7d7a41efd123743cedb951232b2cfebbb388948c5b213241061cf35f8` |
| `30_DEPLOY/platform_support.js` | 5,308 | 공개용 결과물 | `d176e36d3b325fbed581345b70bdb0ff6629952d7c7d565ecbde2b867a486e42` |
| `30_DEPLOY/pwa_api_client.js` | 7,120 | 공개용 결과물 | `4c2dbf537aa18c80de265ef237f5b5028a0253bdbd0bd922aa012ed6d04bc874` |
| `30_DEPLOY/pwa_runtime.js` | 46,963 | 공개용 결과물 | `23c43d29c4774cd01a970e1bcfcfb61fa86d9b1466a101d2411cb3769e12b77c` |
| `30_DEPLOY/VPN_1000명_비용기간_대시보드.html` | 82,525 | 공개용 결과물 | `eb51afdca4cac3b263ff67cfe8873a2a50b6f1e7b7e2bc69ce01bea60b106fad` |
| `30_DEPLOY/VPN_20개국_분산_비용최적화.html` | 36,939 | 공개용 결과물 | `86090b991dd08d8b93404bfaf326bdfe056927106e3fce58a79690575ae03a91` |
| `30_DEPLOY/VPN_국가별_서버비용_50개국.html` | 36,780 | 공개용 결과물 | `9a2f2b0653433cc193d562b19422391c551f981ccb80906bc94c7dd5ad4ed47f` |
| `30_DEPLOY/종량제_VPN_가격패키지_설계.html` | 48,960 | 공개용 결과물 | `04b4966fe1a4ca64e9dc052c174dd68699d1695954e20e0f4cc8c8d02a5f2171` |
| `40_TESTS/negative_control.py` | 17,555 | 검사 | `9721cec77d0a6c985d16d58289b62532df3a1d44536b773f091623a15d41ad71` |
| `40_TESTS/render_check.py` | 5,104 | 검사 | `f74af7b32c4d80e1c91631083e4719182813af2cc9a37289cb17d7dbfe8fc9c3` |
| `40_TESTS/test_abuse_controls.py` | 5,696 | 검사 | `a0751eaa94abb640cdb7654024c467e16b4ae48febade0cd6ff1d1d9c2bff90d` |
| `40_TESTS/test_account_continuation.py` | 2,789 | 검사 | `7fe8871d0dd902708ecc4665d4c5d1356d083b9618665e1065d5d46a53cc34a6` |
| `40_TESTS/test_ai_handoff.py` | 4,656 | 검사 | `7e503c8b2a1f61bd22ae9cb2051d0788e5843adf9973ec7ccbd04f70a030f4cb` |
| `40_TESTS/test_app_v2_contract.py` | 5,187 | 검사 | `05a79a035ecfed3ec4b487b56c87ec8e6f6edbc6bf80dc0d38bacf54df622168` |
| `40_TESTS/test_client_keygen.py` | 5,359 | 검사 | `cad8719d9df668b3880e0edf4525b771bac12325f643440f9b82cd054baaa29c` |
| `40_TESTS/test_cloud_init.py` | 6,617 | 검사 | `9a9fff7ec329ceb5d788877eb1545dd6ce80d66e8036f3bc06438df8db9d5acb` |
| `40_TESTS/test_collaboration_ci.py` | 2,138 | 검사 | `3895ba104836a2f0ac8a848d4d7351869dd968bfbcc0808343b1ad9042132c16` |
| `40_TESTS/test_collaboration_gateway.py` | 12,013 | 검사 | `9d5faa27fa2927ce4ca66346464687f5e38ac958766910b15d03a1ef72e85b3e` |
| `40_TESTS/test_collaboration_http.py` | 12,144 | 검사 | `120760d772d2e2ec1347a083112bc1376f394042fafbe1d2f45e9c6128311116` |
| `40_TESTS/test_collaboration_portal_ui.py` | 7,025 | 검사 | `7333d8f2d732db285f93a83cce484437c17c5d4637ced9db00b91f02b4e8dca8` |
| `40_TESTS/test_collaboration_runtime.py` | 6,035 | 검사 | `aed452c35f626bf82d4924262ae8298a437eb4f07da1843eb827de94ea9096a2` |
| `40_TESTS/test_collaboration_workspace.py` | 4,627 | 검사 | `52255a14b75d50f460c00ffdf9805f35c57f078a387c4c3e1a41440ccd78f45f` |
| `40_TESTS/test_commercial_readiness.py` | 3,243 | 검사 | `b76d809ff8b8c509a02e59ab48716d00654e3a4e74d5757765462ea4e74816d6` |
| `40_TESTS/test_commercial_readiness_ui.py` | 3,382 | 검사 | `d794c2c7d755a34b5ba03050024f723dda6c6b4984f5de76768a67d8a383916d` |
| `40_TESTS/test_commercial_release_plan.py` | 782 | 검사 | `cb38c71b617e30b6cba2fc7eed902096c920553b081b9c358b2d13957a8ed597` |
| `40_TESTS/test_connection_check.py` | 4,119 | 검사 | `77eecf01476ce1450959c9c6c008f8f48a15690c2be17d0966975fdd06a4fc9e` |
| `40_TESTS/test_continuity_v520.py` | 6,438 | 검사 | `f53d5b1c77e0fb2ec015a7dcb65c926f26b37c2ca01a45ec2ebb7e3925c42106` |
| `40_TESTS/test_contracts.py` | 7,356 | 검사 | `e72ec25e820ac6380887cdf5fb831bfeb2e108a9a9e393b7b6785d00d84437ea` |
| `40_TESTS/test_contributor_access.py` | 2,028 | 검사 | `393e54393e79771f932f3d52200f960fab14ab9f3c685f89fae0c034e311a6b3` |
| `40_TESTS/test_control_api.py` | 15,575 | 검사 | `02007f8052cc536191c540b2652e7fd0480de7bb30b4991fde13892885ada673` |
| `40_TESTS/test_control_http.py` | 4,184 | 검사 | `78197064a5eb54e56f1b616f2adfb6bbb6023dff33088781992ccca25f4a3328` |
| `40_TESTS/test_control_runtime.py` | 5,460 | 검사 | `0952794b5418fb863eff2c13ef478d232413204ad9d0e8fe8cefa03ab03e031e` |
| `40_TESTS/test_cost_provider_contract.py` | 5,601 | 검사 | `76d710f52680791be92024fb70814f9f3118056ee4007160e84c6c5404a03127` |
| `40_TESTS/test_daily_safety_ui.py` | 1,400 | 검사 | `d8c145b5bf2736f4a87776415955b2c9b53a52c0e354d95d099fe79e15c4a944` |
| `40_TESTS/test_desktop_app_mode.py` | 4,795 | 검사 | `41953bd1b66f0f0ba488467854fe78292f65f77396e169d64523e0a0704744ab` |
| `40_TESTS/test_development_dashboard_contract.py` | 1,567 | 검사 | `8ea26fd69f71ca29f4f7c1b81a57d52014c6ae56f86b65c21716867bcdd295a4` |
| `40_TESTS/test_device_handoff_ui.py` | 1,747 | 검사 | `f9cc7654401ca24a12d34e569c0981526fec835d69270edb82ba86ce403cba70` |
| `40_TESTS/test_exit_admin.py` | 6,544 | 검사 | `3c89ae4b7204b521385bf128308fac1c7fd2cba4561b24d863da525fff389426` |
| `40_TESTS/test_first_use_recovery_ui.py` | 2,117 | 검사 | `045d2d69a66c8cb1384f42ff3c11a72ec16727f867ca9b58f852b214c0b8f639` |
| `40_TESTS/test_gcp_billing_review.py` | 4,191 | 검사 | `0220a1c93666693287b2ad07400c707249056940bca87506ff18bc57fcfa5e11` |
| `40_TESTS/test_gcp_cloud_shell_bundle.py` | 6,143 | 검사 | `145fe5b962fb4078898e8cd1ece44a291d1d3bb8af2c20002c8d9a6e697d7e7b` |
| `40_TESTS/test_gcp_cost_review.py` | 4,123 | 검사 | `ed1e0665b1bf744ada143665d809cb650cd522eb833138a6fcbf4b95aa85350d` |
| `40_TESTS/test_gcp_node_admission.py` | 5,159 | 검사 | `bf3f289c98249a2c827653505e9a61fc85fd77e41fa91f04dc1b4ba9398c996c` |
| `40_TESTS/test_gcp_node_admission_cli.py` | 5,269 | 검사 | `3d1fe9555d7b6524078db27c0f6a3356132fdace2b0c66c5ddeb11089640ccbc` |
| `40_TESTS/test_gcp_node_plan.py` | 5,850 | 검사 | `89c6164291c14a13c54c78ed5e0dc31cd75de679619e81d82590ec55c7cb8007` |
| `40_TESTS/test_gcp_provider_readback.py` | 7,345 | 검사 | `81b3039e1e434cb29efe9f2eb1a256c972c5101e5fe78c8fb79e9e84fccb01e0` |
| `40_TESTS/test_gcp_readback_access.py` | 5,578 | 검사 | `65f0aed383451787f4843ea3c6926a08ce0aeb57aa6fb818419a2cc469b2232c` |
| `40_TESTS/test_gcp_runtime_config.py` | 3,581 | 검사 | `9cdfe3c9606577d2364ba5be6f77c1172715727b6d8478bef027066f503d883a` |
| `40_TESTS/test_github_pages.py` | 6,212 | 검사 | `1f001c704034b6db4b9bce98ba293913e72d2b258d87aec7803031c03a04c302` |
| `40_TESTS/test_keyboard.py` | 4,019 | 검사 | `bd669c45f0e95cfd10bccc3fba609cb6c182fa78f3b24cdc3d019609a8717469` |
| `40_TESTS/test_mobile_readiness.py` | 3,587 | 검사 | `0d646649830469980fedd9465fb1d1c70dc5245f59199f53dfcf13cbc6f342ec` |
| `40_TESTS/test_mobile_readiness_ui.py` | 4,125 | 검사 | `f0d06739e9214384267b581b71203e638fd4c605e651074fcab3388f8dbb9abe` |
| `40_TESTS/test_moment_catalog.py` | 4,987 | 검사 | `bb930a12e2064b2e0c1353c3471f1a508e3ce6aa54b6c71c0f0113ffe3abefa7` |
| `40_TESTS/test_network_safety_ui.py` | 1,800 | 검사 | `0e27c3f1f7f29a36d42cde84534cb8ad33a24459f2cd6a6c2b1743e7cafc9a1f` |
| `40_TESTS/test_open_collaboration.py` | 2,541 | 검사 | `e417cc66e0f1a9bfe5b0295123bc050347b525248a4b9c42c5a6906056cdc0eb` |
| `40_TESTS/test_pc_handoff.py` | 3,281 | 검사 | `b7d6a5e8da19c829585d31827e158bf87c11b4cdaee3c8e700effabb8daa4a32` |
| `40_TESTS/test_pc_home.py` | 3,851 | 검사 | `debdad131a86ce290ab45cddcf4726f855d86ad96e99620171221cfe33037cd1` |
| `40_TESTS/test_pc_productivity_ui.py` | 5,808 | 검사 | `9b538dedf6077f7043b006b77cca4ee54cfd35c96c20b4864e09b3b49c233e3a` |
| `40_TESTS/test_pc_readiness.py` | 4,987 | 검사 | `0072ee72819eb52c02e846ec2b74a7d417dc23ed1622bca64685695b53e972dc` |
| `40_TESTS/test_pc_readiness_ui.py` | 5,665 | 검사 | `0a90b32e89d0af2f72b61db17abc699ddb3ddaabc5d9c497d5f3dc8a265d6952` |
| `40_TESTS/test_pc_viewport.py` | 4,429 | 검사 | `7909fbbcc110cf268f81ec646b51b28647282a54a2bde5582c0a29bf6c07e9fd` |
| `40_TESTS/test_pc_workbench_ui.py` | 1,433 | 검사 | `60a8fc3304e668b54861d718593866f353d3c6870766c935231bd7bc7b0115a6` |
| `40_TESTS/test_peer_bundle.py` | 6,473 | 검사 | `5fb7c7c1859fbb2295eda0ade6ad0bce8e1dc7b375510199d38546c9bdebc31b` |
| `40_TESTS/test_platform_release_evidence.py` | 15,298 | 검사 | `b34d7b9ce95f2809cde4d79348b862bce81cf9386719b4a225bf7f0c103edf48` |
| `40_TESTS/test_platform_support.py` | 4,426 | 검사 | `b5b4a37c0bb24685f116be6f17d637b9c5cc5b01bb055eb15c49eb5b5cb7902e` |
| `40_TESTS/test_policy_consistency.py` | 5,064 | 검사 | `5e3703eebdc6c95cfe6ba1ce5706a695c5bed7e54778d259ff0e154641f63440` |
| `40_TESTS/test_priority_100_planning_v3.py` | 2,392 | 검사 | `9c51630a36926c6047272dddb0fd5401de7235c066f2b1d34fbfe85e0816a49b` |
| `40_TESTS/test_priority_100_planning_v4.py` | 3,675 | 검사 | `4921052f2bc29981cf2ffb35b9374199b8a98655626d16e01ca22e85e3ad4124` |
| `40_TESTS/test_profile_reissue.py` | 9,370 | 검사 | `2fc8ef0855e962fe9bbbdd09f91d89974533cb96d45a812b42b50c08a2122862` |
| `40_TESTS/test_profile_replacement_guard.py` | 2,221 | 검사 | `3198c7a0734660068cc549a70779040b19690d8de16b4112f0de2ad40588a467` |
| `40_TESTS/test_progress_dashboard.py` | 5,688 | 검사 | `dbc82fa0b4723f85466afcb7a40f300e7c8176bc2b6b5ea10d46920c35bca2a9` |
| `40_TESTS/test_protection_evidence_ui.py` | 3,191 | 검사 | `a3ef90ac6ddc5368017e07b423ecc3f31b791e56132e08a7ce551ab127281eac` |
| `40_TESTS/test_protection_status_ui.py` | 2,754 | 검사 | `44675d374f99911e5cf9e85836a7b1ce9936e30d4f946ffd79345a294fb3742c` |
| `40_TESTS/test_public_qr.py` | 1,553 | 검사 | `69ed7344d4c2d14276c1d33ebfdd97b433dba07d78584249c796ea27753e9911` |
| `40_TESTS/test_public_verifier_contract.py` | 872 | 검사 | `8c302ef3457c1f7bd6bf3bc945ab650a3c4710762f9809e36fba77ef1df00cd3` |
| `40_TESTS/test_pwa_api_client.py` | 6,567 | 검사 | `efa3d15bc87e22bdf595fa310ab0525845726503f1e56583a556957949c5cbeb` |
| `40_TESTS/test_pwa_runtime_ui.py` | 16,432 | 검사 | `2cfcb80653f6971035e1fbd8981554d7b5049bcc2d1b6ff7d6534dac11cc426a` |
| `40_TESTS/test_quota_agent.py` | 10,013 | 검사 | `190442d544b65640143177ced219afbee8abdb14f819242aaa7d7542a58f4547` |
| `40_TESTS/test_quota_ledger.py` | 4,296 | 검사 | `ae6c677e372d4a2a1c5d06fcdd5aa9f2125689b1f89c2f1ee4698dab9c7a4f5d` |
| `40_TESTS/test_r6_preflight.py` | 6,283 | 검사 | `048589f7f2f82be543fd3189fa86ec12c7493eec546a298f061d8ca0df630185` |
| `40_TESTS/test_r6_preflight_cli.py` | 5,109 | 검사 | `fabffca2fa3f09c73de869e0d80ea44e3771620057a01134c3c9ce87cfe0903d` |
| `40_TESTS/test_referral_ledger.py` | 6,614 | 검사 | `17bdac25375fadf2409713aedb2f30581c0e1c1b8e4f715f6efc5b31f7ea1fdc` |
| `40_TESTS/test_release_diff.py` | 3,227 | 검사 | `afb93d0bf12a76357dfe7124621b426f8c4e5c0a37b8016bad71c6a8686b8fb3` |
| `40_TESTS/test_runtime_acceptance.py` | 7,851 | 검사 | `6c2dedb6fa1071bf096b09658365dcde21eeafd0b30f5c98290d44a767cf9026` |
| `40_TESTS/test_runtime_evidence.py` | 7,879 | 검사 | `1b5f67ddd6815beba0dbf0c0fe8d5b029c0bcb5867fa61e441b9ce79540fcf1d` |
| `40_TESTS/test_runtime_evidence_workbench.py` | 3,274 | 검사 | `f5c790b9140eecf2d9fcea3ca064809675aaf5cc606cb78ff664f643f912759f` |
| `40_TESTS/test_safety_contract.py` | 3,879 | 검사 | `ab9ea62aea6b423b50669f84a0109eee8ea52f5f6e0cb26cc9e8f970dfb1f0fe` |
| `40_TESTS/test_schema_migration.py` | 3,043 | 검사 | `91e8f663987c1c8526583040a5deb8f0a6e64fdcd979e253e87ea76302070dc6` |
| `40_TESTS/test_server_catalog.py` | 5,523 | 검사 | `35fc2f246ba90998cf5192d9a132e420734f8eb8e66844410ca217c5e0e24b77` |
| `40_TESTS/test_server_usage_empty_ui.py` | 4,021 | 검사 | `9238881129c0cf009a0852db1b7ce542e99abbc8936c2075824bc09e3da05829` |
| `40_TESTS/test_service_ui_v2_6.py` | 5,053 | 검사 | `eed458ced37fc4319f9526163d0b84772ef17b27e60545cc93ce5233164eaf57` |
| `40_TESTS/test_service_ui_v3.py` | 10,342 | 검사 | `0ddc642536e7adb538fdd78d00afd506fce82f0e02367cfed597573edb027fb8` |
| `40_TESTS/test_ssh_node_adapter.py` | 10,140 | 검사 | `9c4a8f6970c12f80f2f886c914608217b7d9012723ae9ff0d2b54f0726ddfc0c` |
| `40_TESTS/test_telegram_onboarding.py` | 8,639 | 검사 | `a04422e7f63c4c858a4b601e1e161e5f5af8b2bfd5c295674b6e8327b235067a` |
| `40_TESTS/test_test_runner.py` | 3,020 | 검사 | `b94a1ebb2563e60f991bd5e9e33fc9d3a3a4e4e9299d9283430b30b88207e6fb` |
| `40_TESTS/test_travel_safety_ui.py` | 1,696 | 검사 | `0484d9da4ae7dffc0b1772639e295fa1abdaa057a9b9f6fe213c491a866b527f` |
| `40_TESTS/test_ui_design_contract.py` | 3,680 | 검사 | `29842417f47a215775551a0c4b4fdb876518dbc52cacf2a8949419719b7d014e` |
| `40_TESTS/test_usability_simulation.py` | 2,601 | 검사 | `6df8d5ae1436494618fc5307ff2303a8f4b89671b9695c3fade3df3cd6adbecc` |
| `40_TESTS/test_usage_meter.py` | 6,814 | 검사 | `0ceb8085cda7d8f2b12a72b6cc3e8766c621f3ef007540ecba5b1c6f746cf90b` |
| `40_TESTS/test_wallet_ledger_v2.py` | 6,452 | 검사 | `21c6cc45d24b39cd4022e29722c0dd27068d42db6b15f2b2aecc29caf92242ab` |
| `40_TESTS/verify_app_service_plan_v2.py` | 6,642 | 검사 | `4fac43b4be61241673aae43781825a2c4969fbd8e6bb88d8dd4aac59d857e255` |
| `40_TESTS/verify_dev_execution_plan_v2.py` | 2,838 | 검사 | `93722c01ee7d4a960699461298dface0e1ab4a097d18d703e3f24c6c11cf6e66` |
| `40_TESTS/verify_freeflex_business_plan.py` | 3,293 | 검사 | `c96ca887ee576d0a7b78264956c950f1030e793433cc42789c588380ce1c3c4d` |
| `60_OUTPUTS/archive_2026-07-31/legacy_deploy/FreeKoreaVPN_1일오픈_체크리스트.html` | 39,933 | 생성 결과·참고 산출물 | `3fd555abefefa22a41c66a2a55f02cea06f797e7df46d6f19327fbaf5d2797e8` |
| `60_OUTPUTS/archive_2026-07-31/legacy_deploy/FreeKoreaVPN_비용계산서.html` | 40,890 | 생성 결과·참고 산출물 | `f61012d58cf41c61dc936a31b38d70f164acbc9ba98fedd09b0cb7556a35554e` |
| `60_OUTPUTS/archive_2026-07-31/legacy_docs/Free_Korea_VPN_개발실행계획서.docx` | 29,416 | 생성 결과·참고 산출물 | `5c2d1fa0c521adbb36176a88413d0eed631649ffbfaee2f25c7d94160674e721` |
| `60_OUTPUTS/archive_2026-07-31/legacy_docs/Free_Korea_VPN_사업기획서.docx` | 30,928 | 생성 결과·참고 산출물 | `a28f7de4942049c64e9e0116985f38db9ad78faf7c8acfc2c87570a1e4d4585b` |
| `60_OUTPUTS/archive_2026-07-31/legacy_docs/FreeFlexVPN_사업계획서_v1.0_2026-07-31_final.docx` | 31,238 | 생성 결과·참고 산출물 | `b09f0a5368f40b55fb838b6a02e1089bed3e24e6c980dcf66843e9642e647a6a` |
| `60_OUTPUTS/FreeFlexVPN_APP_QR_v1.1_2026-08-01.png` | 2,613 | 생성 결과·참고 산출물 | `ab7f68ca032628b037bb1e9dfdebdaa9c29738b35382a777ce71aa4e10366d4f` |
| `60_OUTPUTS/FreeFlexVPN_GCP_비용확인도우미_v2.13_2026-08-03.html` | 28,792 | 생성 결과·참고 산출물 | `72869dfb41737fa08aa0f3b3a5f611230289a30fa73482146321daf8ace44e6a` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.10_2026-08-03.html` | 14,776 | 생성 결과·참고 산출물 | `479b1b1a9db18cba32d21e7a3a9c6c9bbbc4ed9cf9d8333689d4c11e04f67a92` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.11_2026-08-03.html` | 14,892 | 생성 결과·참고 산출물 | `2eabe473e32c7074a5db77dc1550c6654f53b0e436a3001e33e35a424d390d3d` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.12_2026-08-03.html` | 14,978 | 생성 결과·참고 산출물 | `e8d6bbb07361770ac746eb16def2769f8787b15e1bdebb677aa387ad73ea18d7` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.13_2026-08-03.html` | 14,971 | 생성 결과·참고 산출물 | `861aa63f30cbdac36093057de4a9303502f07b5fd8b4393f87eaca546bca6b3e` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.14_2026-08-03.html` | 14,062 | 생성 결과·참고 산출물 | `16332f6567a1f4b786cc8aac86413dc789861bb499d89d589658197327935842` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.15-r2_2026-08-03.html` | 21,927 | 생성 결과·참고 산출물 | `fb68d32f711f3aa018cd88812490b40517c8e7852f76132d80fc8bfcec4c400d` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.15_2026-08-03.html` | 21,911 | 생성 결과·참고 산출물 | `241f630cef893cf284ca870cd54cd09a0b28444f618592ae6bc8b1ec1d70a0bd` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.3_2026-08-02.html` | 4,187 | 생성 결과·참고 산출물 | `966d910ba7482b13276178b04aaa045763adb9effd305664b6bf444eed2f0d76` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.4_2026-08-02.html` | 5,689 | 생성 결과·참고 산출물 | `f5e88799d609af173196aed965c59bfd7583e5aaf140aa111fa70f8654b108e3` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.5_2026-08-02.html` | 5,245 | 생성 결과·참고 산출물 | `6eaab1c8fd4911ba52b1b87dcae6ba6c80e7b68a845340bf32508f3eb41ee9d7` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.6_2026-08-02.html` | 5,471 | 생성 결과·참고 산출물 | `61ff3efa4700263fe6c97d5de83141053f0b3b180de679af0f6aa150baa8b8b4` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.7_2026-08-02.html` | 5,629 | 생성 결과·참고 산출물 | `35a34ce7d738477bd40b636c5b89c2e5f7a9374a7dae72174cada118169c09ba` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.8_2026-08-02.html` | 5,162 | 생성 결과·참고 산출물 | `d95b73a4e898859552c69877ec3bbe29cb1f8ce7eab092dce163fb2766f9f1dd` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.9-r2_2026-08-02.html` | 14,507 | 생성 결과·참고 산출물 | `c5f32f5d7c56ce887fed9b1b26ce262cb13baa3efdc9ac0723e637dc198ee00e` |
| `60_OUTPUTS/FreeFlexVPN_progress_dashboard_v2.9_2026-08-02.html` | 14,249 | 생성 결과·참고 산출물 | `d05db963ecb0bd17781aa2f3931fa996d8019617e01ff1f818a4bfb07aa67682` |
| `60_OUTPUTS/FreeFlexVPN_PUBLIC_QR_v1_2026-07-31.png` | 3,541 | 생성 결과·참고 산출물 | `384a6a6298b09d43ee41c6e76ebd4278dc26e6748368db1b674a01b27d39683b` |
| `60_OUTPUTS/FreeFlexVPN_runtime_evidence_workbench_v2.17_2026-08-03.html` | 11,121 | 생성 결과·참고 산출물 | `bfe2a25b1e051d0f439b8b135ae3a0bbfe0128880a916fb5772111702f16cac9` |
| `60_OUTPUTS/FreeFlexVPN_개발실행계획서_v1.0_2026-07-31.docx` | 29,168 | 생성 결과·참고 산출물 | `7e9f7204551f311faa4e859a24f12fb287daec525e7cbfb52aca51216f41d7a0` |
| `60_OUTPUTS/FreeFlexVPN_사업계획서_v1.0_2026-07-31.docx` | 31,044 | 생성 결과·참고 산출물 | `24422481881645f4f63dbcbb8043c2bc0ffe09254f70765a56578fb4b360857e` |
| `60_OUTPUTS/FreeFlexVPN_상세개발실행계획서_v2.0_2026-08-01.docx` | 56,060 | 생성 결과·참고 산출물 | `80c3de68a86bc8c6363f11fdfabc6e02b7d06dee3a5e2b7628bbdd9f2fcfb775` |
| `60_OUTPUTS/FreeFlexVPN_앱서비스기획서_v2.0_2026-08-01.docx` | 52,529 | 생성 결과·참고 산출물 | `04db48fb6faf30a72e84a9c237af834093ac34e717dd623aee9cad999fb35089` |
| `60_OUTPUTS/FreeFlexVPN_핵심제품질문_정밀검토_v1.0_2026-08-01.md` | 22,558 | 생성 결과·참고 산출물 | `993a637a7007b4cb5edebb3edcaf9a1fdc39e9f2dc65b52a712167d2c74afab4` |
| `60_OUTPUTS/infra/FreeFlexVPN_exit_node_cloud_init_v1_EXAMPLE.yaml` | 25,546 | 생성 결과·참고 산출물 | `2587bb291f0b28dffc311e6cf4467f4f3989fdd0ea93d5f3ab3566d036d68cce` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v1_EXAMPLE/01_preflight.sh` | 1,940 | 생성 결과·참고 산출물 | `a08b6ab6204b8b75c31fb0b13dbfe64057bf48b3b886b318cb615f7e5cb41295` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v1_EXAMPLE/02_deploy.sh` | 3,447 | 생성 결과·참고 산출물 | `ae3485d6ea1e7ef3102722e8bc0dc11a4c768a167ac8e26c4a915eba83934e18` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v1_EXAMPLE/03_provider_readback.sh` | 2,921 | 생성 결과·참고 산출물 | `63dc6ef547e077a0d64f66188892cb1377ddceaa779c1816cab9fe2cc8f5bec6` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v1_EXAMPLE/04_rollback.sh` | 2,179 | 생성 결과·참고 산출물 | `7e9a2528ea99ddb60e46bacfed63f3af8b440d7543648bf62ea5adf01e4783bd` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v1_EXAMPLE/bundle-manifest.json` | 1,016 | 생성 결과·참고 산출물 | `b719bf536514d32ae956bf6bf91827495e4b9836bf5d9f6e3e8c88b4267d4e66` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v1_EXAMPLE/cloud-init.yaml` | 40,312 | 생성 결과·참고 산출물 | `c415d18f3b0cf59ac8364d00f8b4c9def4cd7d4a28b7736fdf8c111d9fe027ea` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v1_EXAMPLE/README.md` | 1,290 | 생성 결과·참고 산출물 | `e5bf3891ea56a4defd9c9b43fe66ce9da01a707ce79be4de0f1157f9c5ab8470` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v2_EXAMPLE/01_preflight.sh` | 1,940 | 생성 결과·참고 산출물 | `a08b6ab6204b8b75c31fb0b13dbfe64057bf48b3b886b318cb615f7e5cb41295` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v2_EXAMPLE/02_deploy.sh` | 3,447 | 생성 결과·참고 산출물 | `ae3485d6ea1e7ef3102722e8bc0dc11a4c768a167ac8e26c4a915eba83934e18` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v2_EXAMPLE/03_provider_readback.sh` | 2,673 | 생성 결과·참고 산출물 | `408011566d94c4340f43dfe13579e68f44c9bfec4afc7e798dfd491cd186c07c` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v2_EXAMPLE/04_rollback.sh` | 2,179 | 생성 결과·참고 산출물 | `7e9a2528ea99ddb60e46bacfed63f3af8b440d7543648bf62ea5adf01e4783bd` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v2_EXAMPLE/bundle-manifest.json` | 1,119 | 생성 결과·참고 산출물 | `6bd2084d6a1fe325608b9a3aba9732b44a157bb515ce800382e2b481e60e293a` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v2_EXAMPLE/cloud-init.yaml` | 40,312 | 생성 결과·참고 산출물 | `c415d18f3b0cf59ac8364d00f8b4c9def4cd7d4a28b7736fdf8c111d9fe027ea` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v2_EXAMPLE/README.md` | 1,365 | 생성 결과·참고 산출물 | `466b6a903501c4307504a5d204953a15facb14f0ca99073ca3cefc8a9eee5cec` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v2_EXAMPLE/verify_provider_readback.py` | 9,901 | 생성 결과·참고 산출물 | `6d9bca09e3938a775af3b861a2db633d0c62235888d5cefbe6f9983478b61fbe` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_node_cloud_init_v1_EXAMPLE.yaml` | 40,312 | 생성 결과·참고 산출물 | `c415d18f3b0cf59ac8364d00f8b4c9def4cd7d4a28b7736fdf8c111d9fe027ea` |
| `60_OUTPUTS/infra/FreeFlexVPN_gcp_node_plan_v1_EXAMPLE.json` | 2,509 | 생성 결과·참고 산출물 | `6230a9816ba5e690433d03d897f037c8209f99feade44a70e1f86440066dcc91` |
| `60_OUTPUTS/infra/FreeFlexVPN_telegram_bot_config_v1_EXAMPLE.json` | 895 | 생성 결과·참고 산출물 | `a91191ac611c80a5b42b693261a3ef50f99947ce127e5a440c54c66831a86959` |
| `60_OUTPUTS/policy_drafts/FreeFlexVPN_약관_개인정보_국외이전_초안팩_v0.1_2026-08-03.md` | 14,603 | 생성 결과·참고 산출물 | `f8ff77a5feb07acb7f3343b3fb3ef52f98596c830261d67839f93ce1faf9916b` |
| `60_OUTPUTS/prototype/FreeFlexVPN_app_prototype_v1.1.html` | 50,433 | 생성 결과·참고 산출물 | `f9e7b568a750bd524d23cc669ff5463eda492b330ecf3ba1017e30101b72ff10` |
| `60_OUTPUTS/prototype/FreeFlexVPN_app_prototype_v1.html` | 50,441 | 생성 결과·참고 산출물 | `874f03de5381d2f2387deafa16c5cfae0080f82f9decad5322ed24bfea6b9d50` |
| `60_OUTPUTS/prototype/FreeFlexVPN_app_prototype_v1_home.png` | 75,477 | 생성 결과·참고 산출물 | `fd0b7b705a4342dd69de3de5947e80b5814de6fc4c3550dee94dd1a9cb6a0b9a` |
| `60_OUTPUTS/prototype/FreeFlexVPN_app_prototype_v1_topup.png` | 70,240 | 생성 결과·참고 산출물 | `de2e6460d4eb1b4b3c5eacc0b96f682565db848ed93d5866d1b350f8e401e6ca` |
| `60_OUTPUTS/prototype/FreeFlexVPN_app_prototype_v2.0.html` | 105,485 | 생성 결과·참고 산출물 | `2da621746654a51c675ee249b436c13462bfdd60c6178c508fa40b2e5d3186a3` |
| `60_OUTPUTS/prototype/FreeFlexVPN_app_prototype_v2.1.html` | 129,794 | 생성 결과·참고 산출물 | `d4cd682612af8813a75c94343958374700bb6493d436885ba1955a83f97b588e` |
| `60_OUTPUTS/prototype/FreeFlexVPN_app_prototype_v2.2.html` | 141,709 | 생성 결과·참고 산출물 | `63eb9710fc8e2b79bdae12024c4118d1207f8aa4582da375ab2c7298673c96c9` |
| `60_OUTPUTS/prototype/FreeFlexVPN_app_prototype_v2.3.html` | 146,845 | 생성 결과·참고 산출물 | `8a906f32dfa74b734f2630937339408a509f6c422a6e103122bd086509b4886a` |
| `60_OUTPUTS/prototype/FreeFlexVPN_app_prototype_v2.4_PC1.html` | 151,161 | 생성 결과·참고 산출물 | `3b62eb495c4299313d53dcb22ad1fd3f332a6267cbbc510227479de95fd574f6` |
| `60_OUTPUTS/prototype/FreeFlexVPN_app_prototype_v2.5_PC2_PC3.html` | 189,681 | 생성 결과·참고 산출물 | `d5c064b25d34f8441313c4d89aac41ddab4e6203b4fb785fcf1229a75675e23f` |
| `60_OUTPUTS/prototype/FreeFlexVPN_service_v2.6.html` | 295,739 | 생성 결과·참고 산출물 | `7bf68c899471f4e7d700399a77f62846c0897ee5d77d93a78959ac38eb819b11` |
| `60_OUTPUTS/usability/P1_REAL_STATUS_40_2026-08-10.json` | 55,895 | 생성 결과·참고 산출물 | `1dde648d3be6ac0b79eb0f96294bf6a81b9264bde51a401adb0e722890634243` |
| `60_OUTPUTS/usability/P1_REAL_STATUS_40_REPORT_2026-08-10.md` | 5,223 | 생성 결과·참고 산출물 | `11d017120ceb3546615e220b41962c5a0d713fd4cc510ac7cb7683b7b2bdb315` |
| `60_OUTPUTS/usability/PUBLIC_URL_40_2026-08-10.json` | 55,895 | 생성 결과·참고 산출물 | `1dde648d3be6ac0b79eb0f96294bf6a81b9264bde51a401adb0e722890634243` |
| `60_OUTPUTS/usability/PUBLIC_URL_40_REPORT_2026-08-10.md` | 5,223 | 생성 결과·참고 산출물 | `11d017120ceb3546615e220b41962c5a0d713fd4cc510ac7cb7683b7b2bdb315` |
| `60_OUTPUTS/usability/usability-1000-20260811.json` | 1,305,911 | 생성 결과·참고 산출물 | `e028d3d1afcd2bf40c407d115ed34136b45f237443c2ddeb34b5c7eff5094562` |
| `60_OUTPUTS/usability/usability-1000-20260811.md` | 5,258 | 생성 결과·참고 산출물 | `45c29d9f8f0341062de3a893aa8054f687d645f86cc4d51394c833800ab655d5` |
| `60_OUTPUTS/usability/USABILITY_SIMULATION_1000_2026-08-09.json` | 1,305,911 | 생성 결과·참고 산출물 | `3a2d2159d4dda5e81d014e7f40d7649c1bc8ffac17b50bcb5f859a508c0780d8` |
| `60_OUTPUTS/usability/USABILITY_SIMULATION_1000_REPORT_2026-08-09.md` | 5,258 | 생성 결과·참고 산출물 | `45c29d9f8f0341062de3a893aa8054f687d645f86cc4d51394c833800ab655d5` |
| `70_TOOLS/bootstrap_dev.ps1` | 2,404 | 생성·검증 도구 | `78b80cb8bea94de92bb82c83880c352a6207c280d75976c071a77188ddba0552` |
| `70_TOOLS/build_exit_node_cloud_init.py` | 2,345 | 생성·검증 도구 | `2078ec9c84fa4c6fa0d754bac7182df0541c7948f3a6a045f0df0800f076e312` |
| `70_TOOLS/build_gcp_billing_review.py` | 3,462 | 생성·검증 도구 | `69c5537d75c92123a352cf284a30814fa034d10f6648196544cb162b3b207545` |
| `70_TOOLS/build_gcp_cloud_shell_bundle.py` | 1,934 | 생성·검증 도구 | `b534c12121e5fa6fe54b5fb8419efb03ce20f32e0f2aa9c9b809cae77c7a9f48` |
| `70_TOOLS/build_gcp_node_plan.py` | 3,480 | 생성·검증 도구 | `845b9aaea42bfeea6f03275732e18b4366d793478d1761233fe7658f73350012` |
| `70_TOOLS/build_gcp_runtime_config.py` | 3,798 | 생성·검증 도구 | `ad171422fd5ad1c330fbf48fa08edb9a616762d133b27782ecb87735b53388ca` |
| `70_TOOLS/build_github_pages.py` | 2,658 | 생성·검증 도구 | `1c43114563af84ecf316757eec683cc70ae8139e8d6ffed7aca55764ba58405d` |
| `70_TOOLS/build_release_diff.py` | 6,277 | 생성·검증 도구 | `fc92a4d4b97b3371af4761ba60ae254937bc7d67bb6314f3e78a3ed444f88a52` |
| `70_TOOLS/build_runtime_evidence_workbench.py` | 2,291 | 생성·검증 도구 | `f81e5e45f566a9d9e1f1eac8cecb3f3ef76ae993e3d77760a9d2bc4a58a9dcc5` |
| `70_TOOLS/build_telegram_bot_config.py` | 1,752 | 생성·검증 도구 | `198b47002c075a58e11112ab721ca6e2589178187456ac9142353625fa063b3b` |
| `70_TOOLS/check_app_prototype.mjs` | 2,621 | 생성·검증 도구 | `0db4cecc7178f06aa74ca9d696c08ce9dc19557e92db215859034272a066ebd0` |
| `70_TOOLS/check_gcp_readback_access.py` | 1,198 | 생성·검증 도구 | `c6d9786895d895b80310dcfedb939d09dcf714cd728273313d4beb78ee272bc2` |
| `70_TOOLS/check_inline_html_js.mjs` | 945 | 생성·검증 도구 | `871bc56a2a74976265e4a31bb6edc9af2c3db8b791fce244cabde603cbf86580` |
| `70_TOOLS/compare_profile_reissue.py` | 2,318 | 생성·검증 도구 | `ebccb2ef2a010f5b802361b8bc9311d35a5680ba4035d3588f1fa302253aea08` |
| `70_TOOLS/create_ai_handoff.py` | 16,852 | 생성·검증 도구 | `634d33196a3296a077bf2e0bc9e7a9b8c9fd525aa1ab979d68809d83aaa882df` |
| `70_TOOLS/evaluate_platform_evidence.py` | 1,122 | 생성·검증 도구 | `51c7f4d2106f299dbc4d9b6d5324387748a4e7f281f23b7fb61792aec8aaaeff` |
| `70_TOOLS/evaluate_release_95.py` | 1,393 | 생성·검증 도구 | `519b66e3dd99b6e72d7cc23b8300c427fee2cf1cd586a36326c290cb78c7f9ce` |
| `70_TOOLS/evaluate_runtime_acceptance.py` | 1,446 | 생성·검증 도구 | `404b22ed19a561b9dd939c04ea3b61b31668c62ddac7812fc21310ab4339ac18` |
| `70_TOOLS/fkvpaths.py` | 1,710 | 생성·검증 도구 | `73014d2685a337fab53500c3e7792ace23096688b39d6309e55920ff3b364ec5` |
| `70_TOOLS/gen_contracts.py` | 472 | 생성·검증 도구 | `dd9d2345d70938e4989ccdf87bed619cdf6637a9a328833d1481580bb57466c1` |
| `70_TOOLS/gen_state.py` | 25,823 | 생성·검증 도구 | `6e5d6203fc4ecff6f947d78b466bffe11d901276d140cd88d938c8ab08187882` |
| `70_TOOLS/grant_contributor_access.ps1` | 2,467 | 생성·검증 도구 | `05de9d3e7e4059020024740d4a3ac79677e5c3267cf97d18657363b4e8c130e5` |
| `70_TOOLS/init_external_evidence_bundle.py` | 7,242 | 생성·검증 도구 | `2b24d5c16f71de05049e435e2932589137b874f32713602adb9d5b40cb725296` |
| `70_TOOLS/issue_peer_bundle.py` | 1,674 | 생성·검증 도구 | `82f9a0e843f2fcd65cc8ace23805e4bac16128fe91553310b3db9128111f6747` |
| `70_TOOLS/make_manifest.py` | 6,857 | 생성·검증 도구 | `5c315559c6513b40748fc89b758f068d03c1add557f71349c19eba9d8f44de26` |
| `70_TOOLS/make_public_qr.py` | 1,705 | 생성·검증 도구 | `0190d4beb4cdd7f2af5428829308091925b1b9cfa40521e274b2953798079113` |
| `70_TOOLS/progress_dashboard.py` | 36,098 | 생성·검증 도구 | `0b55f50c93daf1cdefbe16b4481e3ac2bdb248707d0daa0f666924a094f67619` |
| `70_TOOLS/reconcile_peer_bundle_address.py` | 3,217 | 생성·검증 도구 | `7413e37775a04e049c346e08c21df7057bd1516b11b3efbab65ce7f55624ed50` |
| `70_TOOLS/run_abuse_candidate_checks.py` | 1,377 | 생성·검증 도구 | `be422b4ad1499589430e9fd1aa28245afc6fc2c001a82b097ca71a285b18e824` |
| `70_TOOLS/run_all_tests.py` | 8,837 | 생성·검증 도구 | `59403c175156f07eac7629160077edcdb4f2a90cb8e7a2329e7e7cff09653aed` |
| `70_TOOLS/run_gcp_cost_review.py` | 1,382 | 생성·검증 도구 | `1788cc5a3a12579cac1aec8046010ba2355bc7839a3189d6b5b1ed4fe62d87d1` |
| `70_TOOLS/run_gcp_node_admission.py` | 4,559 | 생성·검증 도구 | `b3312de7022a967b5e9570538d7f10df7500b6a41212f5ea23e44ead8ffde0f4` |
| `70_TOOLS/run_r6_server_preflight.py` | 5,522 | 생성·검증 도구 | `f8ce98f6df5c699b9586648a8cdc83fd4e244fba4c051e8fe776f29779ff49f7` |
| `70_TOOLS/run_usability_simulation.py` | 15,582 | 생성·검증 도구 | `c70c455741a7379e26d5272ecacfdee4516a69caa365e4690409c361cd44582f` |
| `70_TOOLS/scan_secrets.py` | 3,153 | 생성·검증 도구 | `d1f9cbda71bc1fa29e9848b962aef6f27f30bc8c5166df8433387b8e2c7cce09` |
| `70_TOOLS/verify_account_continuation.py` | 7,972 | 생성·검증 도구 | `1cbdcce38fe94a64db78370598256a99f870c6c803610c5542eff7e61864e1b3` |
| `70_TOOLS/verify_public_pc_v2_5.py` | 7,390 | 생성·검증 도구 | `46f29267e3582bfeb43394ee98c316fd3a81027aca3b210aaa27cb919b00be5c` |
| `90_ARCHIVE/00_START_legacy/HANDOFF_V2_2026-08-01.md` | 2,352 | 분류 확인 필요 | `e82e027fed1efa452ec427cbdb3904f6b0d6570b64386d81b0867086281348b1` |
| `90_ARCHIVE/00_START_legacy/README.md` | 5,242 | 분류 확인 필요 | `9c27849eaa704e80a314fdf558db76699e29d5412bd3e1d4708f40cfddaef436` |
| `90_ARCHIVE/10_STATE_plans/APP_SERVICE_PLAN_v2.0_2026-08-01.md` | 24,251 | 분류 확인 필요 | `37fdd7895a3c9d6879eb273dc43ebd505d4da99829d4bfeb7cbd7015b9d035af` |
| `90_ARCHIVE/10_STATE_plans/APP_SERVICE_PLAN_v3.0_2026-08-05.md` | 8,313 | 분류 확인 필요 | `1fedb7df0ea8f2c6e534679ad3bd23504f7ab95b890a3f1b9466f30c748f41dc` |
| `90_ARCHIVE/10_STATE_plans/APP_SERVICE_PLAN_v4.0_2026-08-06.md` | 8,941 | 분류 확인 필요 | `27283eaf0ea6650bc99ddd11aca5c7048229bb1b036d301605c1016bfe96f7ec` |
| `90_ARCHIVE/10_STATE_plans/DEV_EXECUTION_PLAN_v2.0_2026-08-01.md` | 26,975 | 분류 확인 필요 | `e1424ac9f1e68e5d575d64c205186c8d0b37e33119f973242c4613f314f481d4` |
| `90_ARCHIVE/10_STATE_plans/DEV_EXECUTION_PLAN_v3.0_2026-08-05.md` | 11,921 | 분류 확인 필요 | `2ada1322c59674b8d12ea3481e11acdee1071ee0850f11cbef8b530715ef5071` |
| `90_ARCHIVE/10_STATE_plans/DEV_EXECUTION_PLAN_v4.0_2026-08-06.md` | 15,009 | 분류 확인 필요 | `f59e38943882ea0e5aaade4aee0db454986a0751b3be844008f5f56085d0c367` |
| `AGENTS.md` | 2,885 | 프로젝트 작업 규칙 | `1763bf38441f4f56fa0db129abbc684d7b029de56a153d58989731a228f9483a` |
| `CONTRIBUTING.md` | 1,594 | 분류 확인 필요 | `10af0afbc007ec022344eba9d71c07529f45740b821160dd5d08c6f78c8941b8` |
| `README.md` | 1,832 | 분류 확인 필요 | `5763d01f7cac58ea835f5f944b1c80c08bf97442330bf927f7c777ac8e655d94` |
| `requirements-dev.txt` | 176 | 분류 확인 필요 | `fbe3ca70753cfd98410986c7c8d6c284c743ead8904beaa62094d9abf8fd2c3c` |
