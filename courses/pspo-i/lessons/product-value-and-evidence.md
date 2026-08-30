# 제품 가치와 증거 기반 의사결정

## 학습 목표

- output, outcome, impact를 구분한다.
- 가치 가정을 지표와 실험으로 검증한다.
- Product Backlog ordering에 evidence를 사용한다.

## 가치 극대화는 기능 최대화가 아니다

Product Owner의 핵심 accountability는 제품 가치를 극대화하는 것이다. 가치는 맥락적이며 매출만을 뜻하지 않는다. 고객 성과, 위험 감소, 학습, 비용 절감, 사회적 영향, 전략적 옵션도 포함할 수 있다. 중요한 것은 조직이 정의한 가치와 고객이 실제로 경험한 변화 사이에 증거가 있는가다.

- **Output**: 배포한 기능, 완료 Item 수
- **Outcome**: 사용자의 행동·상태 변화
- **Impact**: 조직이나 사회의 장기 결과

`검색 기능 5개 출시`는 output이다. `첫 성공 검색까지 걸리는 시간이 40% 감소`는 outcome이다. 전자는 노력의 증거이고 후자는 가치 가설을 검사하는 신호다.

## Evidence Loop

1. 고객 문제와 기대 가치를 명시한다.
2. 가장 위험한 가정을 찾는다.
3. 작은 Increment나 실험으로 evidence를 얻는다.
4. 사전에 정한 지표와 정성적 관찰을 함께 검사한다.
5. 계속 투자, 변경, 중단 중 하나를 결정한다.

지표는 목표를 대체하지 않는다. 단일 지표를 최적화하면 부작용을 숨길 수 있어 primary outcome, guardrail, health metric을 함께 둔다. 예를 들어 전환율을 높이면서 환불률과 고객 문의가 악화되지 않는지 본다.

## Evidence-Based Management와의 연결

PSPO I의 핵심은 Scrum과 제품 가치지만, 실무에서는 EBM 관점이 유용하다. Current Value, Unrealized Value, Ability to Innovate, Time to Market 같은 관점은 `현재 가치`, `미충족 기회`, `혁신을 막는 제약`, `학습 속도`를 함께 보게 한다. 특정 지표를 Scrum이 의무화하는 것은 아니다. 맥락에 맞는 Key Value Measures를 선택한다.

## 실무 산출물 — Value Experiment Card

- 고객/사용자와 관찰한 문제
- 가설: `만약 ... 하면 ... 때문에 ...가 변할 것이다`
- primary outcome metric과 baseline
- guardrail metric
- 가장 작은 검증 가능한 Increment
- 검사 날짜와 계속/변경/중단 기준

다음 Sprint Planning 전에 카드 한 장을 만들고 Sprint Review에서 실제 evidence로 갱신한다.

## 시험 함정

- Velocity는 가치가 아니며 팀 간 생산성 비교 지표도 아니다.
- PO가 가치를 책임진다고 고객·Developers의 입력을 무시하는 것은 아니다.
- 더 많은 Backlog Item을 완료했다고 가치가 자동으로 증가하지 않는다.
- 완벽한 예측을 기다리기보다 작은 Done Increment로 불확실성을 줄인다.

## 공식 자료

- [Managing Products with Agility](https://www.scrum.org/professional-scrum-competencies/managing-products-with-agility)
- [Scrum.org Product Owner Learning Path](https://www.scrum.org/pathway/product-owner-learning-path)
