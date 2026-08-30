# 딥러닝 기초와 모델 시뮬레이션

신경망은 가중합·활성화·손실 계산을 반복해 파라미터를 학습한다. 작은 검증 세트에서 epoch별 손실과 성능을 그려 과적합을 확인하고, 복잡한 모델을 쓰기 전 동일 split의 기준 모델과 비교한다.

## 목표·시험 포인트
손실·epoch·검증 곡선을 해석하고 DL을 기준 모델과 비교한다. 학습 점수만으로 성공을 판단하지 않는다.
```python
history = model.fit(X_train, y_train, validation_split=.2, epochs=20, verbose=0)
plt.plot(history.history["loss"], label="train"); plt.plot(history.history["val_loss"], label="validation")
```
검증 손실 상승을 무시하거나 seed·batch 조건을 기록하지 않는 실수를 피한다. 곡선과 최적 epoch를 보고한다.

완료 체크: [ ] loss 설명 [ ] validation 비교 [ ] 과적합 판단.
