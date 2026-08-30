# 경험적 예측과 릴리스 계획

## 학습 목표

- forecast와 commitment를 구분한다.
- 실제 throughput과 불확실성으로 범위·날짜 확률을 설명한다.
- 릴리스를 Sprint 종료나 Sprint Review에 종속시키지 않는다.

## 계획은 약속이 아니라 현재 evidence의 해석

복잡한 제품 개발에서는 미래 작업과 발견을 완전히 예측할 수 없다. forecast는 현재 아는 범위, 과거 성과, 위험을 바탕으로 가능한 결과를 표현하고 새 evidence에 따라 갱신한다. 이해관계자에게 단일 날짜를 확정처럼 말하는 대신 범위, 가정, 신뢰 수준을 함께 제공한다.

사용 가능한 evidence에는 cycle time, throughput, work item age, 과거 Sprint에서 Done된 범위, 품질·운영 제약이 있다. Velocity는 한 팀의 계획 대화에 보조적으로 쓸 수 있지만 가치 지표가 아니고 팀 간 비교나 성과 평가에 쓰면 왜곡된다.

## 경험적 Forecast 흐름

1. release outcome과 최소 가치 범위를 정의한다.
2. Backlog의 불확실성과 dependency를 드러낸다.
3. 실제 delivery 데이터를 사용해 범위 또는 날짜의 분포를 만든다.
4. 작은 Done Increment를 자주 전달해 가정을 검사한다.
5. 매 Sprint Review에서 시장·가치·delivery evidence로 forecast를 갱신한다.

Monte Carlo 같은 기법은 필수가 아니지만 `11월 15일까지 85% 확률로 18~24개 Item`처럼 불확실성을 정직하게 보여줄 수 있다. 숫자보다 중요한 것은 Done의 일관된 의미와 데이터 품질이다.

## Release와 Sprint

Increment는 Sprint 안에 여러 번 만들어질 수 있고 Sprint Review 전에 전달할 수 있다. Sprint Review는 release gate가 아니다. 반대로 매 Sprint 반드시 외부 배포해야 한다는 규칙도 없다. 최소한 매 Sprint 하나의 usable하고 Done인 Increment를 만들어 선택 가능성을 유지해야 한다. 릴리스 결정은 가치, 위험, 운영·법적 맥락을 고려한다.

## 실무 산출물 — Forecast Brief

- 원하는 release outcome과 최소 범위
- 기준 날짜 또는 기준 범위
- 과거 8~12주 throughput/cycle time
- 50%, 85%, 95% 시나리오
- 상위 위험과 가정
- 다음 갱신 시점과 evidence owner

이해관계자에게 `무엇이 확실하고, 무엇이 불확실하며, 다음에 언제 더 알게 되는가`를 한 페이지로 설명한다.

## 시험 함정

- Sprint Backlog는 commitment가 아니라 forecast를 포함한 Developers의 계획이며 commitment는 Sprint Goal이다.
- PO가 Developers의 capacity나 작업량을 지정하지 않는다.
- release는 Sprint Review 승인 후에만 가능하지 않다.
- fixed scope와 fixed date를 동시에 확정하면 불확실성이 사라지는 것이 아니다.

## 공식 자료

- [Managing Products with Agility](https://www.scrum.org/professional-scrum-competencies/managing-products-with-agility)
- [The Scrum Guide](https://scrumguides.org/scrum-guide.html)
