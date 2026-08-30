# 범주형·수치형 데이터 전처리

전처리는 모델 입력을 만드는 과정이다. 목표 변수와 입력 변수를 분리하고 수치형·범주형 열을 구분한다.

```python
from sklearn.model_selection import train_test_split
X = df.drop(columns="churn")
y = df["churn"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
```

결측치 대체, 스케일러 학습, 인코딩은 학습 데이터에만 `fit`한다. 테스트 정보가 섞이면 데이터 누수로 성능이 부풀려진다. 명목형에는 원-핫 인코딩, 순서가 있는 범주에는 순서 인코딩을 검토하고 새로운 범주 정책을 명시한다. 변환 근거를 기록한다.
