# Scrum Theory와 경험주의

## 학습 목표

- Scrum이 복잡한 문제에 왜 적합한지 설명한다.
- 투명성, 검사, 적응을 제품 의사결정에 적용한다.
- Lean thinking과 반복적·점진적 접근을 구분한다.

## Scrum은 목적이 있는 최소 프레임워크

Scrum은 복잡한 문제를 다루며 적응형 해법으로 가치를 만드는 경량 프레임워크다. 상세한 절차나 직무별 지침을 모두 제공하지 않는다. 의도적으로 불완전하며 Scrum의 parts 안에서 다양한 process, technique, method를 사용할 수 있다. User Story, Story Point, Planning Poker 같은 관행은 쓸 수 있지만 Scrum 자체의 필수 요소는 아니다.

Scrum은 **경험주의**와 **Lean thinking**에 기반한다. 경험주의는 지식이 경험에서 나오고 관찰한 것에 따라 결정을 내린다고 본다. Lean thinking은 낭비를 줄이고 essential에 집중한다. 반복적·점진적 접근은 예측 가능성을 높이고 위험을 통제한다.

### 먼저 이해할 이론: 불확실성은 계획으로 제거되지 않는다

복잡한 제품에서는 원인과 결과를 미리 모두 알 수 없다. 따라서 처음 만든 계획의 준수율보다, 짧은 주기로 실제 결과를 보고 다음 결정을 바꾸는 능력이 중요하다. 반복적이라는 말은 같은 일을 되풀이한다는 뜻이 아니라, 학습 주기를 반복한다는 뜻이다. 점진적이라는 말은 매번 일부만 만든다는 뜻이 아니라, 사용할 수 있는 Done Increment를 쌓는다는 뜻이다.

예를 들어 “검색 필터를 만들면 구매 완료율이 오른다”는 가정이 있다면 필터 화면을 완성했다는 사실만으로 가정이 검증되지 않는다. 실제 사용자가 필터를 쓰고 구매 완료율이나 탐색 성공률이 변했는지 검사해야 한다. 결과가 나쁘면 Backlog 순서나 가정 자체를 적응한다.

## 경험주의의 세 기둥

### Transparency

일과 과정이 수행하는 사람과 결과를 받는 사람에게 보인다. 중요한 정보가 불명확하거나 서로 다른 정의를 사용하면 검사의 근거가 잘못된다. 공통 언어, 명확한 Product Goal, 하나의 Backlog, Definition of Done이 투명성을 돕는다.

### Inspection

Artifacts와 목표 진척을 자주, 성실하게 검사해 바람직하지 않은 편차나 문제를 찾는다. 검사는 목적이 아니라 적응을 가능하게 하는 수단이며, 과도하면 일을 방해할 수 있다. Scrum Events는 공식적인 검사와 적응의 cadence를 만든다.

### Adaptation

결과가 허용 범위를 벗어나거나 접근이 효과적이지 않다면 가능한 한 빨리 조정한다. 권한 없는 팀, 불투명한 데이터, 실패를 처벌하는 문화에서는 적응이 어려워진다.

세 기둥은 분리되지 않는다. 투명성 없는 검사는 잘못된 결론을 만들고, 검사 후 적응하지 않으면 회의만 늘어난다.

### 쉬운 구분 예시

- 투명성: “완료”의 의미를 팀마다 다르게 쓰지 않고 Definition of Done과 현재 상태를 공유한다.
- 검사: Sprint Review에서 Increment와 제품의 반응을 살핀다. 진행률 숫자만 보는 것은 충분한 검사가 아니다.
- 적응: 관찰 결과에 따라 Backlog 순서, Product Goal을 향한 접근, 또는 다음 실험을 바꾼다.

흔한 오해는 “경험주의면 계획이 필요 없다”는 것이다. 계획은 가설과 현재의 최선의 선택을 표현한다. 다만 새로운 evidence가 생겼을 때 계획을 수정할 수 있어야 하며, 기존 계획을 지키는 것이 목적이 되면 경험주의가 약해진다.

## Product Owner의 Empirical Decision Loop

1. Product Goal과 가치 가정을 명시한다.
2. 작은 Done Increment로 중요한 가정을 검증한다.
3. 사용 행동, 품질, 고객 feedback, 시장 변화가 예상과 다른지 검사한다.
4. Backlog ordering, forecast, 목표 또는 전략을 적응한다.
5. 무엇을 배웠고 왜 결정했는지 투명하게 공유한다.

실패한 실험을 숨기면 sunk cost가 커진다. 반대로 실패 evidence를 공개하고 작은 투자 후 방향을 바꾸면 그 학습 자체가 가치가 될 수 있다.

## 실무 연습 — Assumption-to-Evidence Board

상위 Product Backlog Item 5개에 대해 `가치 가정`, `현재 evidence`, `가정을 반증할 신호`, `가장 작은 검사`, `적응 결정`을 적는다. evidence가 전혀 없는 가장 큰 Item을 다음 Sprint의 작은 학습 조각으로 바꾼다.

마지막으로 동료나 녹음 파일에 60초 동안 다음을 설명한다. “왜 Done Increment가 단순한 개발 완료보다 강한 evidence인가?”, “검사했는데도 적응하지 않으면 어떤 비용이 생기는가?” 설명에 담당 주체와 관찰할 결과가 빠졌다면 해당 단락을 다시 읽는다.

## 시험 함정

- Scrum은 모든 프로젝트 절차를 정의하는 methodology가 아니다.
- 검사 주기가 짧다고 무조건 empirical한 것은 아니다. 투명성과 실제 적응이 필요하다.
- 계획 변경은 실패가 아니라 새로운 관찰에 대한 정상적 적응일 수 있다.
- Sprint 중에도 scope는 PO와 Developers가 Sprint Goal을 지키며 재협상할 수 있다.

## 공식 자료

- [The Scrum Guide](https://scrumguides.org/scrum-guide.html)
- [Professional Scrum Competencies](https://www.scrum.org/professional-scrum-competencies)
