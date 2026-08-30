# Artifacts, Commitments, Definition of Done

## 학습 목표

- 세 Artifact와 각 Commitment를 정확히 연결한다.
- Done Increment가 가치 검증과 예측의 기반인 이유를 설명한다.

## 세 쌍

| Artifact | Commitment | 핵심 질문 |
|---|---|---|
| Product Backlog | Product Goal | 장기적으로 무엇을 향하는가? |
| Sprint Backlog | Sprint Goal | 이번 Sprint가 왜 가치 있는가? |
| Increment | Definition of Done | 무엇이 실제로 완료됐는가? |

Commitment는 focus와 투명성을 강화해 진척을 측정할 기준을 제공한다.

### Product Backlog와 Product Goal

Product Backlog는 제품 개선에 필요한 것의 emergent하고 정렬된 단일 목록이며 Scrum Team이 수행하는 일의 유일한 원천이다. Product Goal은 제품의 미래 상태를 나타내는 장기 목표다. Scrum Team은 한 번에 하나의 Product Goal을 추구하며 달성하거나 포기한 뒤 다음 목표로 이동한다.

### Sprint Backlog와 Sprint Goal

Sprint Backlog는 Sprint Goal, 선택한 Product Backlog Items, Increment를 전달할 실행 계획으로 구성된다. Developers가 만들고 소유하는 실시간 계획이다. Sprint Goal은 유연한 범위 안에서 하나의 목적과 coherence를 제공한다.

### Increment와 Definition of Done

Increment는 Product Goal을 향한 구체적 디딤돌이며 이전 Increment에 더해져 함께 작동하고 철저히 검증되어야 한다. Sprint 안에 여러 Increment를 만들고 Sprint Review 전에 전달할 수도 있다. Sprint Review가 가치 전달의 관문은 아니다.

Definition of Done은 Increment가 제품에 요구되는 품질 기준을 충족한 상태에 대한 공식 설명이다. 조직 표준이 있으면 최소 기준으로 따라야 하며, 없으면 Scrum Team이 제품에 적합한 DoD를 만든다. 여러 Scrum Team이 같은 제품을 함께 만들면 같은 DoD를 상호 정의하고 준수해야 한다.

Done이 아닌 Item은 Sprint Review에서 완료로 제시하거나 릴리스할 수 없으며 향후 고려를 위해 Product Backlog로 돌아간다. 마감 압박은 품질 기준을 낮출 이유가 아니다.

## 실무 연습 — Transparency Audit

현재 제품에서 다음을 확인한다.

1. Product Goal을 팀원이 같은 의미로 설명하는가?
2. Sprint Goal이 작업 목록이 아니라 결과의 목적을 말하는가?
3. DoD가 테스트·보안·운영·문서화 등 실제 releasability를 반영하는가?
4. `90% 완료` 항목이 Increment 성과로 보고되고 있지 않은가?
5. 기술 부채가 가치 예측을 왜곡하지 않도록 투명한가?

DoD 개선 후보를 하나 고르고 품질·속도·학습에 미칠 영향을 Developers와 논의한다. PO가 일방적으로 DoD를 정하지 않는다.

## 시험 함정

- Product Goal은 Product Backlog 안에 있다.
- PO가 Sprint Backlog를 관리하지 않는다.
- Increment는 Sprint Review에서만 릴리스할 수 있는 것이 아니다.
- Acceptance Criteria는 유용한 보조 관행일 수 있지만 Definition of Done과 동일하지 않다.

## 공식 자료

- [The Scrum Guide](https://scrumguides.org/scrum-guide.html)
