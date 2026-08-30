# Refinement, Ordering, Value Slicing

## 학습 목표

- refinement와 ordering의 목적을 설명한다.
- 큰 기능을 독립적으로 검증 가능한 가치 조각으로 나눈다.
- 가치·위험·학습·비용을 함께 고려해 Backlog를 정렬한다.

## Refinement는 지속 활동

Product Backlog refinement는 Item을 더 작고 정밀하게 나누고 정의하는 지속 활동이다. 설명, 순서, 크기 같은 세부 정보를 추가한다. 공식 Scrum Event나 고정 timebox가 아니며 Scrum Team이 필요에 맞게 수행한다. 가까운 Item이 Sprint Planning에서 선택될 만큼 투명해지는 것이 목적이지 문서를 완벽히 만드는 것이 목적은 아니다.

Developers는 일을 수행할 사람들이므로 sizing에 책임진다. PO는 가치와 trade-off를 이해시키고 선택에 영향을 줄 수 있지만 숫자를 지정하지 않는다.

## Ordering은 다차원 의사결정

단순히 business value 점수만 정렬하지 않는다.

- 예상 고객·사업 가치
- Product Goal과 전략 적합성
- 위험 감소와 학습 가치
- 시간 민감성, 규제, 시장 창
- 의존성과 가능하게 하는 일
- 크기와 opportunity cost
- 실제 사용·품질 evidence

가중 점수는 대화를 돕는 도구일 뿐 자동 의사결정 엔진이 아니다. PO가 ordering의 이유를 투명하게 설명하고 새로운 evidence가 생기면 적응한다.

## 가치 수직 분할

큰 Item을 기술 계층별로 `DB → API → UI`로 나누면 각 조각만으로 사용자 가치를 검사하기 어렵다. 가능한 한 작은 end-to-end 사용자 흐름, 한 세그먼트, 한 시나리오, 한 규칙으로 나눈다.

예: `전체 환불 시스템`을 다음처럼 나눌 수 있다.

1. 상담원이 단일 주문 전액 환불을 처리한다.
2. 고객이 배송 전 주문을 스스로 취소한다.
3. 부분 환불과 쿠폰 정산을 처리한다.

첫 조각만으로도 운영 시간과 오류율 evidence를 얻을 수 있다.

## 실무 산출물 — Ordering Decision Log

상위 10개 Item에 `Goal 연결`, `expected outcome`, `evidence`, `risk/learning`, `time criticality`, `size`, `선택하지 않을 경우 비용`을 적는다. 서로 다른 두 ordering 시나리오를 만들고 어떤 가정에서 순서가 바뀌는지 설명한다. 큰 Item 하나를 3개 이상의 end-to-end slice로 나눈다.

## 시험 함정

- `priority`보다 공식 Scrum Guide 용어는 `order`다. 하나의 요인만으로 정해지지 않는다.
- refinement는 PO만의 회의가 아니다.
- Definition of Ready는 Scrum의 필수 commitment가 아니다.
- Sprint Planning에서 Developers가 선택한 Item은 Sprint Backlog의 일부가 된다.

## 공식 자료

- [The Scrum Guide](https://scrumguides.org/scrum-guide.html)
- [Product Owner Learning Path](https://www.scrum.org/pathway/product-owner-learning-path)
