# pandas로 분포와 관계 탐색하기

AICE Associate의 데이터 분석 영역은 데이터 구성과 특성, 품질을 파악하는 데서 시작한다. 분석 질문을 먼저 관찰 가능한 결과로 정의하고 필요한 열과 행을 확인한다.

```python
df.shape
df.dtypes
df.describe(include="all")
df["segment"].value_counts(dropna=False)
```

수치형 변수는 평균뿐 아니라 중앙값, 사분위 범위, 최소·최대값을 확인하고 범주형 변수는 빈도와 결측 범주를 살핀다. `groupby`와 `agg`로 업무 단위 요약표를 만든다. 요약값에서 차이가 보여도 표본 수, 기간, 측정 정의를 확인한 뒤 다음 검증 질문을 기록한다.
