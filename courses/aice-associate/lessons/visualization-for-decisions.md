# 의사결정을 돕는 데이터 시각화

시각화는 비교와 이상 징후를 검사하는 도구다. 범주별 비교에는 막대 그래프, 시간 변화에는 선 그래프, 수치형 분포에는 히스토그램·박스플롯, 두 수치형 변수의 관계에는 산점도를 우선 검토한다.

```python
import matplotlib.pyplot as plt
import seaborn as sns
sns.boxplot(data=df, x="segment", y="monthly_spend")
plt.tight_layout()
```

축 단위와 표본 수를 명시하고 색상은 의미가 있을 때만 쓴다. 상관이 높아 보이는 산점도도 제3의 변수나 시간 추세가 만든 착시일 수 있다. 처리 전후 분포를 비교하고 관찰과 추가 검증을 함께 기록한다.
