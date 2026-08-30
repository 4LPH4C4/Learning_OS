# Product Owner 시나리오 워크숍

## 목표

시험형 짧은 상황을 실제 제품 decision으로 확장한다. 모든 사례에서 다음 네 질문을 사용한다.

1. 누구의 accountability인가?
2. 어떤 목표·Artifact·evidence가 투명해야 하는가?
3. 자기관리를 해치지 않는 선택은 무엇인가?
4. 가장 빠른 가치 학습은 무엇인가?

## 사례 1 — VIP 기능 요청

Sprint 중 가장 큰 고객이 새 기능을 즉시 요구한다. 요청을 무조건 거절하거나 바로 Sprint Backlog에 넣지 않는다. PO는 문제, 긴급성, 고객·사업 영향 evidence를 확인하고 Product Goal 및 Sprint Goal과 비교한다. Sprint Goal을 보호하면서 Developers와 scope를 재협상할 수 있다. Sprint Goal 자체가 쓸모없어졌다면 PO만 Sprint를 취소할 권한이 있다. 단순히 예상보다 일이 어렵거나 요청자가 강하다는 이유로 취소하지 않는다.

**실무 산출물:** 한 페이지 change decision log를 작성한다. 요청, evidence, Goal 영향, 선택지, decision, 재검사 날짜를 기록한다.

## 사례 2 — 90% 완료된 기능

핵심 기능이 테스트와 보안 기준을 통과하지 못했다. 마감 때문에 `거의 완료`로 Review에서 성과에 포함시키면 Increment transparency가 무너진다. Done이 아닌 Item은 Increment 일부가 아니며 Backlog로 돌아간다. 팀은 Increment와 시장 evidence를 Review하고 Retrospective에서 품질·협업 개선을 다룬다. PO가 DoD를 일방적으로 낮추지 않는다.

**실무 산출물:** 현재 DoD에서 release risk를 막는 기준과 불필요한 bureaucracy를 구분해 Developers와 개선 후보를 만든다.

## 사례 3 — 약속한 출시일

영업이 3개월 뒤 전체 범위를 확정해 판매했다. PO는 `팀이 더 열심히 하면 된다`고 압박하지 않는다. 최소 가치 outcome, 실제 throughput, 범위 불확실성, risk를 공개해 여러 confidence 시나리오를 제공한다. 작은 Done Increment를 일찍 전달해 forecast와 가치 가정을 갱신한다.

**실무 산출물:** 50/85/95% forecast와 scope trade-off를 작성한다.

## 사례 4 — 이해관계자 투표

부서장들이 각자 자기 요청을 1순위로 주장한다. 다수결은 PO의 accountability를 대체하지 않는다. Product Goal, 고객 impact, evidence, risk, opportunity cost를 공통 기준으로 만들고 의견을 듣는다. PO는 최종 ordering을 결정해 이유를 투명하게 공유한다.

**실무 산출물:** 상위 5개 Item의 ordering decision log를 만든다.

## 사례 5 — 해결책을 지시하는 PO

PO가 database schema와 API 구현 방식을 승인하려 한다. PO는 중요한 규제·사용자 제약과 expected outcome을 제공하고 Developers와 trade-off를 탐색한다. 구현 방법, Sprint 계획, sizing은 Developers의 전문성과 자기관리 영역이다. 기술 선택이 가치·위험에 미칠 결과는 Scrum Team이 함께 투명하게 다룬다.

**실무 산출물:** problem, constraints, outcome, non-goals로 구성한 solution-neutral brief를 쓴다.

## 사례 6 — 성공처럼 보이는 지표

가입 전환율은 올랐지만 7일 이내 해지와 지원 문의가 크게 늘었다. PO는 output이나 primary metric 하나만 보고 확장을 결정하지 않는다. guardrail과 정성 evidence를 함께 검사해 실제 customer outcome을 판단한다. 작은 실험으로 어느 세그먼트에 가치가 있었는지 확인한다.

**실무 산출물:** primary outcome, guardrail 2개, 세그먼트, 계속/중단 기준을 담은 experiment card를 만든다.

## 답변 Review Rubric

- Scrum Guide의 accountability를 정확히 지켰는가?
- `회사에서 보통 한다`와 Scrum 필수 규칙을 구분했는가?
- Goal과 Done을 보호하면서 scope 적응 여지를 남겼는가?
- 고객·시장·품질 evidence를 사용했는가?
- PO 독단이나 위원회 책임 회피 대신 명확한 협업과 결정을 설계했는가?

각 사례를 3분 안에 말로 설명한다. 상대가 `왜 다른 선택지는 아닌가`를 물으면 경험주의, accountability, value 관점에서 답한다. 이 능력이 제한 시간 시험과 실제 이해관계자 대화 모두에 도움이 된다.

## 공식 자료

- [The Scrum Guide](https://scrumguides.org/scrum-guide.html)
- [Suggested Reading for PSPO I](https://www.scrum.org/resources/suggested-reading-professional-scrum-product-owner)
