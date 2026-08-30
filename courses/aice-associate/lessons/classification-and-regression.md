# 분류와 회귀 모델링

분류는 클래스, 회귀는 연속값을 예측한다. 기준선과 트리·랜덤포레스트·KNN 또는 선형 모델을 비교하고, 불균형이면 stratify와 클래스별 지표를 사용한다. 모델 선택은 점수 하나가 아니라 오류 비용과 운영 목적을 따른다.

## 목표·시험 포인트
문제 유형과 오류 비용에 맞춰 모델·metric을 선택한다. 불균형이면 accuracy만 보지 않는다.
```python
from sklearn.ensemble import RandomForestClassifier
model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
```
흔한 실수는 회귀에 accuracy를 쓰거나 기준선 없이 복잡도를 높이는 것이다. 동일 split에서 baseline과 후보 모델을 비교한다.

완료 체크: [ ] 유형 판별 [ ] baseline 비교 [ ] 오류 비용 반영.
