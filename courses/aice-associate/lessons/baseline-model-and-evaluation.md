# 기준 모델 만들기와 성능 평가

복잡한 모델보다 재현 가능한 기준 모델을 먼저 만든다. 분류에서는 다수 클래스 예측과 의사결정나무·랜덤포레스트·KNN을 비교하고, 회귀에서는 평균 예측과 선형 모델을 기준으로 삼는다.

불균형 분류에서 정확도만 보면 소수 클래스 오류를 놓칠 수 있으므로 정밀도·재현율·F1과 혼동행렬을 함께 확인한다. 회귀에서는 MAE가 절대 오차를, RMSE가 큰 오차를 더 크게 반영한다.

```python
from sklearn.metrics import classification_report, confusion_matrix
pred = model.predict(X_test)
print(confusion_matrix(y_test, pred))
print(classification_report(y_test, pred, zero_division=0))
```

테스트 세트는 최종 확인에 사용하고 반복적인 선택은 교차검증으로 학습 데이터 안에서 수행한다. 성능과 함께 사용자 집단별 실패도 보고한다.
