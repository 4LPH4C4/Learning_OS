# 인코딩과 스케일링

명목형 변수는 원-핫, 순서형은 순서 인코딩을 검토한다. StandardScaler는 평균·표준편차를 학습 데이터에서만 구하고, MinMaxScaler는 범위를 맞춘다. 변환기를 Pipeline에 넣어 학습·검증 경계를 보존한다.

## 목표·시험 포인트
열 타입과 모델에 맞는 변환을 선택하고 train-only fit을 지킨다.
```python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
prep = ColumnTransformer([("num", StandardScaler(), ["age"]), ("cat", OneHotEncoder(handle_unknown="ignore"), ["region"])])
```
범주를 임의의 숫자로 바꾸거나 전체 데이터에 fit하는 실수를 피한다. 변환 전후 열 수와 unknown 정책을 확인한다.

완료 체크: [ ] 인코딩 근거 [ ] train-only fit [ ] unknown 정책.
