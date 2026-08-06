export const MOMENT_CATALOG_VERSION = "2026-08-02.1";

export const TIER_LABELS = Object.freeze({
  free: "무료",
  paid: "유료 충전",
  premium_planned: "프리미엄 예정",
  none: "비지원",
});

const DEFAULT_COUNTRY_POLICY = Object.freeze({
  code: "OTHER",
  name: "기타 국가",
  level: "normal",
  policy: "standard",
  notice: "현지 법률과 이용하려는 서비스의 약관을 먼저 확인하세요.",
});

export const COUNTRY_PROFILES = Object.freeze({
  KR: Object.freeze({ code: "KR", name: "대한민국", level: "normal", policy: "standard", notice: "공공 와이파이 보호와 해외 체류 중 본국 서비스 확인에 적합합니다." }),
  JP: Object.freeze({ code: "JP", name: "일본", level: "normal", policy: "standard", notice: "공공 와이파이 보호와 공개 웹의 지역별 표시 확인에 적합합니다." }),
  US: Object.freeze({ code: "US", name: "미국", level: "normal", policy: "standard", notice: "서비스 약관과 조직 보안 정책 범위 안에서 이용하세요." }),
  GB: Object.freeze({ code: "GB", name: "영국", level: "normal", policy: "standard", notice: "서비스 약관과 콘텐츠 권리 범위를 확인하세요." }),
  DE: Object.freeze({ code: "DE", name: "독일", level: "normal", policy: "standard", notice: "서비스 약관과 개인정보 보호 기준을 확인하세요." }),
  SG: Object.freeze({ code: "SG", name: "싱가포르", level: "normal", policy: "standard", notice: "가까운 서버를 이용한 공공 네트워크 보호에 적합합니다." }),
  TH: Object.freeze({ code: "TH", name: "태국", level: "normal", policy: "standard", notice: "현지 법률과 이용 서비스 약관을 확인하세요." }),
  AR: Object.freeze({ code: "AR", name: "아르헨티나", level: "caution", policy: "research_only", notice: "공개 가격·현지화 조사는 가능하지만 거주지나 결제 국가를 속이는 구독 우회는 지원하지 않습니다." }),
  IN: Object.freeze({ code: "IN", name: "인도", level: "caution", policy: "provider_compliance", notice: "인도 소비자 VPN 제공자에는 가입자 정보와 로그 관련 규정이 적용될 수 있습니다. 인도 출구 서버는 규정 검토와 실제 제공 확인 후에만 노출합니다." }),
  AE: Object.freeze({ code: "AE", name: "아랍에미리트", level: "caution", policy: "legal_use_only", notice: "VPN 자체가 아니라 범죄 은폐·불법 목적의 사용이 처벌 대상이 될 수 있습니다. 합법적 목적에서만 이용하세요." }),
  CN: Object.freeze({ code: "CN", name: "중국", level: "restricted", policy: "specialized_required", notice: "일부 글로벌 서비스가 제한될 수 있지만 FreeFlexVPN 알파는 검열 우회·난독화 성공을 보장하지 않습니다. 현지 법률을 확인하고 전문 서비스를 이용하세요." }),
});

const entries = [
  [1,"cafe-wifi","safety","카페 공공 와이파이","공용 네트워크에서 계정·메시지 트래픽을 보호합니다.","nearest","free","supported","low"],
  [2,"airport-wifi","safety","공항 와이파이","공항의 개방형 네트워크에서 짧게 안전한 연결을 만듭니다.","nearest","free","supported","low"],
  [3,"hotel-wifi","safety","호텔 와이파이","호텔 공유망에서 개인 통신을 보호합니다.","nearest","free","supported","medium"],
  [4,"coworking-wifi","safety","공유 오피스 와이파이","여러 이용자가 함께 쓰는 네트워크에서 업무 연결을 보호합니다.","nearest","free","supported","medium"],
  [5,"mobile-route","diagnostic","모바일 통신사 경로 확인","통신사 경로 문제인지 비교 진단합니다.","nearest","free","conditional","low"],
  [6,"dns-route","diagnostic","DNS·라우팅 문제 비교","VPN 경로에서 접속이 달라지는지 확인합니다.","nearest","free","conditional","low"],
  [7,"ip-check","diagnostic","외부 IP·위치 표시 확인","웹사이트가 보는 출구 국가와 IP를 확인합니다.","target","free","supported","low"],
  [8,"bank-abroad","travel_home","해외에서 본인 은행 접속","본국 경로가 접속 안정성에 도움이 되는지 확인합니다. 은행이 VPN을 차단할 수 있습니다.","home","free","conditional","low"],
  [9,"government-abroad","travel_home","해외에서 본국 공공서비스 접속","본인 인증 전 본국 경로에서 접속 가능 여부를 확인합니다.","home","free","conditional","low"],
  [10,"account-recovery","travel_home","해외에서 본인 계정 복구","평소 사용 국가와 같은 경로가 보안 경고를 줄이는지 확인합니다.","home","free","conditional","low"],
  [11,"home-news","travel_home","해외에서 본국 뉴스·생활정보","본국에서 공개되는 지역 생활정보를 확인합니다.","home","free","supported","medium"],
  [12,"order-status","travel_home","해외에서 본국 쇼핑 주문 확인","본국 쇼핑몰의 본인 주문·배송 상태를 확인합니다.","home","free","conditional","low"],
  [13,"airline-account","travel_home","여행 중 항공사 계정 확인","익숙한 국가 경로에서 본인 예약을 확인합니다. 가격 조작 용도가 아닙니다.","home","free","conditional","low"],
  [14,"work-saas","work","회사 SaaS 접속","회사 정책이 허용한 국가·경로로 업무 도구에 접속합니다.","organization","paid","conditional","medium"],
  [15,"remote-admin","work","원격 관리 작업","고정 IP·전용 경로가 필요한 관리 작업을 준비합니다.","organization","premium_planned","premium_planned","low"],
  [16,"video-call","work","중요 화상회의 경로 안정화","가까운 서버로 경로를 바꿔 통화 품질을 비교합니다.","nearest","paid","conditional","high"],
  [17,"local-search-qa","research","국가별 검색 결과 조사","목적 국가에서 보이는 공개 검색 결과를 조사합니다.","target","paid","supported","medium"],
  [18,"website-localization","research","웹사이트 현지화 QA","목적 국가의 언어·통화·배너 표시를 검수합니다.","target","paid","supported","medium"],
  [19,"ad-landing-qa","research","광고 랜딩 페이지 QA","본인 또는 고객의 공개 광고 페이지가 국가별로 정상인지 확인합니다.","target","paid","supported","medium"],
  [20,"ecommerce-price-research","research","공개 쇼핑 가격 조사","로그인·결제 우회 없이 목적 국가의 공개 가격을 비교합니다.","target","paid","supported","medium"],
  [21,"travel-price-research","research","여행 공개 가격 비교","항공·숙박의 공개 표시를 연구하되 거주지 허위 표시나 결제 우회는 하지 않습니다.","target","paid","conditional","medium"],
  [22,"saas-availability","research","SaaS 국가별 제공 범위 확인","가입·결제 전 공개 기능과 제공 국가를 조사합니다.","target","paid","supported","medium"],
  [23,"public-policy-news","research","현지 공개 뉴스·정책 조사","목적 국가의 공개 자료가 어떻게 보이는지 확인합니다.","target","paid","supported","medium"],
  [24,"open-data","research","해외 공개 데이터·학술 자료 확인","합법적으로 공개된 자료의 지역별 접근 상태를 확인합니다.","target","paid","conditional","medium"],
  [25,"restricted-network","restricted","서비스 제한 국가에서 기본 인터넷 이용","중국 등 제한 환경에서는 일반 VPN보다 검열 대응 전문 서비스와 법률 확인이 필요합니다.","none","none","specialized_required","medium"],
  [26,"cdn-test","performance","CDN·웹 성능 국가별 테스트","목적 국가 경로에서 본인 서비스의 응답 성능을 측정합니다.","target","premium_planned","premium_planned","high"],
  [27,"game-route","performance","게임 경로·지연시간 테스트","게임 서버와 가까운 전용 경로의 지연시간을 비교합니다.","target","premium_planned","premium_planned","high"],
  [28,"own-streaming-travel","content","해외에서 본인 구독 스트리밍 확인","구독 국가와 서비스 여행 정책이 허용하는 범위에서만 이용합니다. 재생 성공은 보장하지 않습니다.","home","premium_planned","premium_planned","high"],
  [29,"iplayer-outside-uk","content","영국 밖에서 BBC iPlayer 시청","BBC 약관상 영국 밖에서 VPN으로 접근하는 용도는 지원하지 않습니다.","none","none","not_supported","high"],
  [30,"subscription-arbitrage","content","저가 국가 구독 우회 (인도·아르헨티나 등)","거주지·결제 국가를 속여 더 싼 구독을 구매하는 목적은 서비스 약관 위반과 취소 위험이 있어 지원하지 않습니다.","none","none","not_supported","low"],
];

export const MOMENTS = Object.freeze(entries.map(([rank,id,category,title,why,destinationMode,tier,support,dataIntensity]) => Object.freeze({
  rank, id, category, title, why, destinationMode, tier, support, dataIntensity,
})));

if (MOMENTS.length !== 30 || new Set(MOMENTS.map((item) => item.id)).size !== 30) {
  throw new Error("Moment catalog must contain 30 unique entries");
}

export function getCountryPolicy(code = "") {
  const normalized = String(code || "").trim().toUpperCase();
  return COUNTRY_PROFILES[normalized] || Object.freeze({ ...DEFAULT_COUNTRY_POLICY, code: normalized || "OTHER" });
}

export function resolveDestination(moment, destinationCountry = "") {
  const country = String(destinationCountry || "").trim().toUpperCase();
  if (moment.destinationMode === "nearest") return "AUTO_NEAREST";
  if (moment.destinationMode === "organization") return "ORG_DEFINED";
  if (moment.destinationMode === "target" || moment.destinationMode === "home") return country || null;
  return null;
}

export function recommendMoments(options = {}) {
  const currentCountry = String(options.currentCountry || "").trim().toUpperCase();
  const destinationCountry = String(options.destinationCountry || "").trim().toUpperCase();
  const category = String(options.category || "all");
  const tier = String(options.tier || "all");
  const query = String(options.query || "").trim().toLocaleLowerCase("ko");
  const available = new Set((options.availableCountryCodes || []).map((code) => String(code).toUpperCase()));
  const catalogKnown = options.catalogKnown === true;
  const countryPolicy = getCountryPolicy(currentCountry);

  const recommendations = MOMENTS.filter((moment) => category === "all" || moment.category === category)
    .filter((moment) => tier === "all" || moment.tier === tier)
    .filter((moment) => !query || `${moment.title} ${moment.why}`.toLocaleLowerCase("ko").includes(query))
    .map((moment) => {
      const destination = resolveDestination(moment, destinationCountry);
      const blockedByPolicy = moment.support === "not_supported" || moment.support === "specialized_required";
      const planned = moment.support === "premium_planned";
      const destinationRequired = (moment.destinationMode === "target" || moment.destinationMode === "home") && !destination;
      const serverAvailable = destination === "AUTO_NEAREST"
        ? available.size > 0
        : destination === "ORG_DEFINED"
          ? false
          : Boolean(destination && available.has(destination));
      const restrictedCurrentCountry = countryPolicy.policy === "specialized_required";
      const actionable = !blockedByPolicy && !planned && !destinationRequired && catalogKnown && serverAvailable && !restrictedCurrentCountry;
      let actionReason = "실제 서버를 선택할 수 있습니다.";
      if (blockedByPolicy) actionReason = moment.support === "not_supported" ? "FreeFlexVPN 비지원 목적입니다." : "전문 서비스와 현지 법률 확인이 필요합니다.";
      else if (planned) actionReason = "프리미엄 출시 예정 기능입니다.";
      else if (restrictedCurrentCountry) actionReason = "현재 국가에서는 검열 대응 호환성을 확인하지 못했습니다.";
      else if (destinationRequired) actionReason = "목적 국가 또는 본국을 선택하세요.";
      else if (!catalogKnown) actionReason = "실제 서버 목록을 불러온 뒤 연결 가능 여부를 확인합니다.";
      else if (!serverAvailable) actionReason = "현재 이용 가능한 서버 목록에 해당 목적지가 없습니다.";
      return Object.freeze({ ...moment, destination, actionable, actionReason });
    });

  return Object.freeze({
    catalogVersion: MOMENT_CATALOG_VERSION,
    currentCountry,
    destinationCountry,
    countryPolicy,
    total: recommendations.length,
    recommendations: Object.freeze(recommendations),
  });
}
