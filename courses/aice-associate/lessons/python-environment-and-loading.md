# Python 환경과 데이터 로딩

Associate는 Python 실기와 제한적 오픈북 환경이다. 노트북의 라이브러리 버전과 난수 시드를 먼저 기록하고, CSV는 `pd.read_csv`, 엑셀은 `pd.read_excel`로 읽은 뒤 `head`, `shape`, `dtypes`를 확인한다. 경로·인코딩·구분자를 명시해 같은 입력을 재현한다.

## 목표·시험 포인트
입력 타입과 결측 표기를 통제하고 로딩 직후 구조를 확인한다. 시험에서는 경로·인코딩·날짜 파싱을 명시했는지 판단한다.
```python
import pandas as pd
df = pd.read_csv("customers.csv", na_values=["", "NA", "-"])
df["joined_at"] = pd.to_datetime(df["joined_at"], errors="coerce")
print(df.shape, df.dtypes, df.head(3))
```
흔한 실수는 실행 위치에 의존하는 상대 경로와 문자열 날짜다. synthetic CSV를 만들고 스키마 요약표를 저장한다.

완료 체크: [ ] 행 단위 정의 [ ] 타입·결측 확인 [ ] 재실행 경로 기록.
