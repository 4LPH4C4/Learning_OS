# 모델 개선과 결과 그래프

개선 순서는 데이터 품질, 누수, 기준선, 특성, 하이퍼파라미터 순으로 점검한다. 학습·검증 곡선, 혼동행렬, ROC/PR 또는 잔차 그래프를 남기고, 집단별 성능과 선택한 임계값을 함께 보고한다. 그래프는 결론과 한계를 설명해야 한다.

## 목표·시험 포인트
개선 가설을 세우고 그래프로 오류와 과적합을 검증한다. 시험에서는 임계값과 metric trade-off를 설명한다.
```python
from sklearn.metrics import ConfusionMatrixDisplay
ConfusionMatrixDisplay.from_predictions(y_test, pred)
```
점수 하나만 최적화하거나 실패 집단을 숨기지 않는다. 임계값별 precision/recall 표와 개선 전후 그래프를 제출한다.

완료 체크: [ ] 가설 기록 [ ] 오류 그래프 [ ] 한계·다음 실험.
