# Learning OS Product Requirements Document

- 문서 상태: Phase 2 Implemented v1
- Product owner: 개인 사용자
- 기준일: 2026-08-30
- 초기 플랫폼: Windows
- 향후 플랫폼: macOS, Linux

## 1. Product Summary

Learning OS는 자격증, GitHub 과정, Markdown, Jupyter Notebook 등 서로 다른 학습 자료를 한곳에서 실행하고 매일의 학습과 진도를 누적하는 로컬 우선 개인 학습 플랫폼이다.

제품의 성공은 기능 수가 아니라 다음 행동이 반복되는지로 판단한다.

> 앱 실행 → 오늘 공부 시작 → 실제 학습 → 완료 기록 → 다음 날 이어서 학습

## 2. 배경과 문제

사용자는 Technical Product Manager, Product Owner, Technical Program Manager, AI/Data Product Manager로 성장하기 위해 Product, Data, AI, 개발 역량을 함께 쌓아야 한다. 현재 학습 대상은 AICE Associate, PSPO I, Microsoft AI-For-Beginners, SQLD이며 이후 자격증, 책, PDF, GitHub 과정, 외국어로 계속 확장된다.

자료 형식과 학습 방식이 분산되어 있으면 다음 문제가 생긴다.

- 오늘 무엇을 해야 하는지 정하는 데 시간이 든다.
- Course별 진도와 시험 일정을 한눈에 보기 어렵다.
- Markdown 학습과 Notebook 실습이 분리된다.
- 여러 Course에서 얻은 역량을 하나의 Skill로 연결하기 어렵다.
- 새 학습 대상을 추가할 때 앱 코드를 다시 작성하게 된다.
- 학습 도구 개발 자체가 실제 공부를 미룰 수 있다.

## 3. Product Vision과 목표

### 3.1 Vision

사용자가 장기간 유지할 수 있는 범용 개인 학습 운영체계를 만든다. 새 Course는 엔진 변경 없이 콘텐츠와 Manifest 중심으로 추가되고, 학습 결과는 지속 가능한 사용자 데이터로 축적된다.

### 3.2 Phase 1 목표

- 설치 후 10분 안에 첫 Lesson을 시작할 수 있다.
- 세 개 초기 Course를 한곳에서 확인할 수 있다.
- 오늘 공부할 Lesson을 즉시 선택할 수 있다.
- Markdown Lesson과 Jupyter Notebook을 학습 흐름 안에서 열 수 있다.
- Lesson 완료 상태가 앱 재시작 뒤에도 남는다.

### 3.3 Phase 2 목표

- Quiz, Review, Scheduler로 기억 유지와 시험 준비를 돕는다.
- Course 진도와 Skill mastery를 분리해 역량 변화를 보여준다.
- Notes와 optional AI Tutor로 학습 내용을 연결하고 확장한다.
- Local/GitHub 이후 PDF, URL, 책, 언어 학습까지 확장한다.

### 3.4 비목표

- 범용 LMS 또는 다중 사용자 교육 서비스
- Course marketplace와 결제
- 소셜 기능, 경쟁형 leaderboard
- Phase 1에서의 AI 기반 개인화
- 모든 초기 Course의 완전한 콘텐츠 제작
- 자격증 실제 시험 문제의 복제

## 4. 사용자와 핵심 Jobs

### 4.1 Primary user

Windows 노트북에서 매일 15~120분을 학습하는 단일 사용자다. SQL 실무 경험이 있고, Python 코드를 읽고 수정하는 수준에서 시작해 Product/Data/AI를 연결하는 실무 역량을 만들고자 한다.

### 4.2 Jobs to be done

- 학습 시간이 생겼을 때 오늘 할 일을 고민하지 않고 바로 시작하고 싶다.
- 시험일까지 여러 Course를 병행하면서 우선순위를 놓치고 싶지 않다.
- 개념을 읽은 직후 같은 흐름에서 Notebook 실습을 하고 싶다.
- 앱을 껐다 켜도 어디까지 했는지 정확히 이어가고 싶다.
- 새로운 Course를 추가해도 기존 진도와 앱 동작이 깨지지 않길 원한다.
- 나중에는 Course가 달라도 같은 Skill에서 쌓인 학습을 함께 보고 싶다.

## 5. Product Success Metrics

Phase 1은 instrumentation 자체를 늘리지 않고 SQLite 기록으로 계산 가능한 지표만 사용한다.

| 지표 | 초기 목표 | 의미 |
|---|---:|---|
| Time to first lesson | 최초 실행 후 10분 이내 | 설정 마찰이 낮음 |
| Weekly active study days | 주 4일 이상 | 지속 사용 |
| Study start conversion | 앱 실행일 중 Lesson 시작 80% 이상 | Dashboard가 행동으로 연결됨 |
| Scheduled completion | Today 제안 Lesson의 70% 이상 | 추천 분량이 현실적임 |
| Progress durability | 검증 시 100% | 재실행 후 진도 손실 없음 |
| P0 incident | 0건 유지 | 학습 흐름 신뢰성 |

North-star metric은 **주간 완료 학습 세션 수**다. 시험 합격과 실무 역량 향상은 장기 outcome으로 별도 회고한다.

## 6. 핵심 사용자 흐름

### 6.1 최초 실행

1. 사용자가 `start.bat`을 실행한다.
2. 앱이 환경과 DB를 초기화하고 브라우저를 연다.
3. Courses에서 학습할 Course를 선택한다.
4. `오늘의 학습`에 선택한 Course 기반 계획이 표시된다.
5. 외부 source가 준비되지 않았으면 해당 Course에만 준비 버튼을 보여준다.
6. 사용자가 첫 Lesson을 연다.

### 6.2 매일 학습

1. `오늘의 학습`에서 오늘 가능한 시간을 선택한다.
2. 선택한 Course의 미완료 Lesson을 시간 범위에 맞춰 보여준다.
3. 사용자가 `오늘 공부 시작`을 누른다.
4. Lesson을 읽고 필요하면 Notebook을 연다.
5. `완료`를 누르면 진도와 학습 세션이 저장된다.
6. `오늘의 학습`의 선택 Course 진도가 즉시 갱신된다.

### 6.3 복습

1. 사용자가 `복습`을 연다.
2. 선택한 Course에서 이전에 풀었고 복습일이 된 문항만 표시된다.
3. 사용자가 퀴즈를 풀고 확신 정도를 기록한다.
4. 결과에 따라 다음 복습일이 다시 계산된다.

### 6.4 외부 Course 학습

1. AI-For-Beginners Course를 연다.
2. source가 없으면 clone, 있으면 상태와 마지막 sync 시각을 확인한다.
3. 원본 Markdown 또는 Notebook을 연다.
4. source 갱신에 실패해도 다른 Course는 계속 사용한다.

### 6.5 재실행

1. 앱을 종료한다.
2. 다시 `start.bat`을 실행한다.
3. 직전 완료 상태와 Course progress가 동일하게 표시된다.

## 7. Phase 1 Functional Requirements

우선순위 표기는 P0가 MVP 필수, P1이 MVP 이후 우선 개선이다.

### FR-01 실행과 초기화 — P0

- Windows에서 `start.bat` 한 번으로 Streamlit 앱을 실행해야 한다.
- macOS/Linux용 `start.sh`를 함께 제공해야 한다.
- Python 3.11 이상이 설치된 환경에서 첫 실행 시 `.venv` 생성과 고정 dependency 설치를 자동화해야 한다.
- 두 번째 실행부터는 기존 `.venv`를 재사용해야 한다.
- 시작할 때 필요한 디렉터리와 SQLite DB를 안전하게 생성해야 한다.
- migration은 여러 번 실행해도 같은 결과를 내야 한다.
- 의존성 또는 실행 환경 문제가 있으면 해결 방법이 포함된 오류를 보여줘야 한다.

수용 기준: 새 데이터 디렉터리와 기존 데이터 디렉터리 모두에서 정상 시작한다.

### FR-02 Manifest 기반 Course Catalog — P0

- 앱은 `courses/*/course.yaml`을 자동 탐색해야 한다.
- Course ID를 기준으로 Core에 조건 분기를 추가하면 안 된다.
- 필수 metadata, module, lesson, source, completion criteria를 읽어야 한다.
- 잘못된 Manifest는 해당 Course만 비활성화해야 한다.
- 오류 메시지에 Course, 필드 또는 경로, 수정 힌트를 포함해야 한다.

수용 기준: 새 valid Course 디렉터리를 추가하고 앱을 재시작하면 Python 코드 변경 없이 목록에 나타난다.

### FR-03 Dashboard — P0

- 제품명, 오늘의 학습, `오늘 공부 시작`, 선택한 Course progress를 보여줘야 한다.
- AICE Associate, PSPO I, Microsoft AI-For-Beginners를 활성 Course로 표시해야 한다.
- SQLD skeleton은 planned 상태로 표시할 수 있다.
- Course progress는 required Lesson 중 완료 비율로 계산해야 한다.

수용 기준: 완료 버튼을 누르면 동일 세션 안에서 progress가 갱신된다.

### FR-04 오늘의 학습 — P0

- Courses에서 선택한 Course만 계획 후보로 사용해야 한다.
- 사용자는 15, 30, 45, 60, 90, 120분 중 가용 시간을 선택할 수 있어야 한다.
- 시스템은 활성 Course의 미완료 Lesson을 최대 3개 제안해야 한다.
- priority, target date, Lesson order를 안정적으로 반영해야 한다.
- 추천 결과에는 Course, Lesson, 예상 시간이 있어야 한다.
- 추천할 Lesson이 없으면 완료 상태 또는 다음 행동을 알려줘야 한다.

수용 기준: 동일한 상태와 설정에서는 동일한 추천이 나온다.

### FR-05 Course List와 Curriculum — P0

- 사용자는 학습할 Course를 복수 선택할 수 있어야 하며 선택값은 로컬에 저장돼야 한다.
- 선택 변경은 다음 `오늘의 학습` 계획과 `복습` 목록에 반영돼야 한다.
- Course별 제목, 설명, 상태, 일정, 예상 시간, 진도를 보여줘야 한다.
- Course를 열면 module과 lesson이 Manifest 순서대로 나타나야 한다.
- 완료/미완료 Lesson을 구분해야 한다.

수용 기준: 세 활성 Course를 각각 열고 첫 학습 항목으로 이동할 수 있다.

### FR-06 Lesson Viewer — P0

- Local Markdown 콘텐츠를 UTF-8로 표시해야 한다.
- code block, heading, list, link를 읽기 가능하게 렌더링해야 한다.
- Lesson metadata와 예상 시간을 표시해야 한다.
- 콘텐츠 파일이 없거나 읽을 수 없을 때 앱 전체가 종료되면 안 된다.

수용 기준: AICE와 PSPO의 첫 Markdown Lesson을 앱에서 읽을 수 있다.

### FR-07 Notebook 실행 — P0

- Notebook 경로를 Manifest에서 읽어야 한다.
- 현재 프로젝트 Python 환경의 Jupyter를 사용해 Notebook을 열어야 한다.
- 공백과 비ASCII 문자가 있는 경로를 안전하게 처리해야 한다.
- Jupyter 미설치나 파일 누락을 행동 가능한 오류로 보여줘야 한다.

수용 기준: AICE Pandas Notebook이 열리고 셀을 실행할 수 있다.

### FR-08 GitHub Source — P0

- AI-For-Beginners의 공식 repository URL을 Manifest로 설정해야 한다.
- source clone, update, current commit, last sync를 지원해야 한다.
- 가능한 범위에서 lessons/notebooks/labs 중심 sparse checkout을 사용해야 한다.
- source를 앱 코드나 Course 디렉터리에 복제해 하드코딩하면 안 된다.
- network 또는 Git 오류는 AI Course에만 표시해야 한다.

수용 기준: clone된 원본 Lesson 또는 Notebook에 Course 화면에서 접근할 수 있고 source unavailable test가 통과한다.

### FR-09 Progress Tracking — P0

- Lesson 열람 시 started/last opened 상태를 기록해야 한다.
- 완료 버튼은 idempotent해야 한다.
- `course_id`와 `lesson_id`로 완료 상태를 식별해야 한다.
- 앱 재실행 후 동일 완료 상태가 복원돼야 한다.
- 완료 이벤트로 Course progress를 다시 계산해야 한다.

수용 기준: Lesson 완료 → 앱 종료 → 재실행 뒤에도 완료 표시와 progress가 유지된다.

### FR-10 Study Session — P0

- 오늘의 학습에서 Lesson을 시작한 시각을 저장해야 한다.
- 완료 시 종료 시각과 실제 경과 시간을 저장해야 한다.
- 비정상 종료된 session이 다음 실행을 막으면 안 된다.

수용 기준: 최소한 시작과 완료 session이 DB에서 확인된다.

### FR-11 Settings — P1

- 기본 학습 시간과 콘텐츠 언어를 로컬 설정으로 저장할 수 있어야 한다.
- 설정이 없어도 60분과 English/Korean 허용이라는 안전한 default로 동작해야 한다.

### FR-12 Backup/Restore — P1

- DB와 사용자 Note를 timestamped archive로 백업할 수 있어야 한다.
- restore 전 현재 데이터를 자동 백업해야 한다.
- 잘못된 archive는 원본을 변경하지 않아야 한다.

## 8. Course/Skill 요구사항

### 8.1 Course Manifest 필드

| 그룹 | 필드 |
|---|---|
| Identity | `schema_version`, `id`, `title`, `description`, `category`, `status` |
| Source | `source_type`, `content_sources` |
| Schedule | `start_date`, `target_date`, `exam_date`, `estimated_hours`, `weekly_target_hours`, `priority` |
| Structure | `modules`, `lessons`, `prerequisites` |
| Learning | `skills`, `quiz_settings`, `completion_criteria` |

ID는 소문자 kebab-case를 기본으로 하고 공개 후 변경하지 않는다. 날짜는 ISO 8601, 시간은 분 단위 integer를 사용한다. 경로는 Course root 기준 상대 경로만 허용하고 root 밖 traversal은 거부한다.

### 8.2 공통 Lesson type

Phase 1은 `markdown`, `notebook`, `markdown_notebook`, `external_markdown`, `external_notebook`을 지원한다. Phase 2에서 quiz, practice, mock exam, vocabulary, listening 등을 추가한다.

### 8.3 Skill 분리

Skill은 Course ID와 독립된 stable ID를 가진다. 같은 `machine-learning` Skill을 AICE와 AI-For-Beginners Lesson이 함께 참조할 수 있어야 한다. Phase 1은 metadata를 읽고 표시할 준비만 하며 mastery 계산은 하지 않는다.

## 9. 초기 Course 요구사항

### 9.1 AICE Associate

- 목표: 시험 합격과 Python/Data/ML 실습 역량 강화
- 학습 패턴: Concept → Example → Guided Exercise → Independent Exercise → Answer Check → Quiz
- 공식 규격: 14문항, 90분, 80점 이상, Python 실기·제한적 오픈북
- 공식 배점: 데이터 분석 30점, 데이터 전처리 30점, AI 모델링 40점
- 구현 범위: 5개 모듈, 필수 Lesson 17개, 독창 문항 28개, 실행 가능한 Notebook 2개
- 실무 범위: 품질 점검, EDA, leakage 방지, 재현 가능한 pipeline, metric/threshold 선택, 결과 설명
- 공식 기준: `https://aice.study/info/aice/asso`

### 9.2 PSPO I

- 공식 Scrum Guide와 공개 Scrum.org Focus Area를 우선 source로 사용한다.
- scenario 문제는 정답, 정답 이유, 오답 이유, 관련 Scrum principle을 포함한다.
- 실제 시험 문제는 복제하지 않는다.
- 공식 규격: 80문항, 60분, 합격선 85%. Course 학습 목표는 90%다.
- 구현 범위: 7개 모듈, 필수 Lesson 16개, 독창 문항 80개와 full mock
- 공식 12개 Focus Area를 Lesson과 문항에 모두 연결한다.
- 실무 산출물: Vision, Product Goal, Value Experiment, Backlog ordering/slicing, Stakeholder map, 확률적 forecast, Sprint Review decision board, 통합 capstone
- 공식 기준: `https://www.scrum.org/resources/suggested-reading-professional-scrum-product-owner`

### 9.3 Microsoft AI-For-Beginners

- 공식 source는 `https://github.com/microsoft/AI-For-Beginners`다.
- repository와 license를 원형대로 유지한다.
- English와 Korean만 선택적으로 사용할 수 있게 준비한다.
- MVP: source 준비/동기화와 첫 원본 Lesson 또는 Notebook 접근

### 9.4 SQLD

- 사용자의 SQL 실무 경험을 전제로 기초 SQL을 길게 반복하지 않는다.
- Data Modeling, SQL 시험 edge case, Practice Exam, Weak Point Review 중심으로 설계한다.
- MVP는 Manifest skeleton만 제공한다.

## 10. Scheduling Requirements

초기 일정은 다음과 같다.

| Course | 시작 | 목표/시험 | 운영 원칙 |
|---|---|---|---|
| AICE Associate | 2026-08-30 | 2026-10-30~31 | PSPO와 병행, 10월 초 이후 비중 확대 |
| PSPO I | 2026-08-30 | 2026-10-03~04 | 가장 먼저 완료 |
| Microsoft AI-For-Beginners | AICE와 연계 | 시험 없음 | AICE 관련 topic과 교차 추천 |
| SQLD | AICE 이후 집중 | 2026-11-14 | 짧은 집중 Track |

Phase 1 Today v1은 priority와 target date만 사용한다. Phase 2 Scheduler는 남은 기간, 주간 가용 시간, 진도, weakness, review due를 함께 고려하되 사용자가 결과를 수동 조정할 수 있어야 한다.

## 11. Phase 2 Requirements

### 11.1 Quiz Engine

공통 question schema는 `question_id`, `course_id`, `skill_id`, `topic`, `difficulty`를 가진다. attempt는 answer, correctness, response time, confidence 1~5, timestamp를 저장한다.

### 11.2 Spaced Repetition

초기 규칙은 오답 1일, 정답+낮은 confidence 2일, 정답 4일, 연속 정답 7/14/30일이다. 알고리즘을 교체할 수 있도록 scheduling interface와 UI를 분리한다.

### 11.3 Practice와 Mock Exam

- PSPO: scenario 중심, 80문항/60분 profile, 목표 90% 이상
- AICE: 90분 data analysis pipeline과 coding exercise
- SQLD: 실제 시험 구조에 준하는 독창 연습
- 결과는 topic과 skill 단위로 분석한다.

### 11.4 Knowledge/Skill Map

Course completion과 Skill mastery를 별도로 계산한다. mastery는 Quiz, Practice, Review, Course completion, confidence를 입력으로 사용하며 계산 근거를 사용자에게 설명할 수 있어야 한다.

### 11.5 Notes와 AI Tutor

Lesson별 Markdown/code/URL Note와 전체 검색을 지원한다. AI Tutor는 `AIProvider` abstraction 뒤의 optional module이며 키가 없어도 Core 학습 기능은 모두 동작해야 한다.

### 11.6 적응형 외국어 Course와 NCS 종합 모의고사

- 영어 첫 Lesson은 CEFR A1~C2 진단, 중국어 첫 Lesson은 입문~HSK 9 진단이어야 한다.
- 단계별 정답률 60%와 누적 정답률 65%를 모두 충족할 때만 다음 단계로 배치한다. 처음 미달한 단계에서 멈춰 상위 문항의 추측 정답이 기초 결손을 가리지 않게 한다.
- 진단 후 권장 단계보다 낮은 Lesson은 현재 학습 경로·진도·Today 추천에서 제외하고, 재진단 결과에 따라 다시 계산한다.
- 진단은 읽기·어휘·문법·상황 판단 기반의 권장 시작점이며 공인 등급이나 듣기·말하기 수행평가로 표시하면 안 된다.
- NCS는 2026 직업공통능력 7개 영역을 회차마다 모두 포함한 50문항·60분 고정 모의고사 10회를 제공한다.
- NCS 회차별 최근 결과를 로컬에 저장하고, 공개 문제를 복제하지 않은 독창 문항임을 명시한다.

## 12. Non-functional Requirements

### NFR-01 신뢰성

- progress write는 transaction으로 처리한다.
- 같은 완료 요청을 반복해도 데이터가 중복되거나 감소하지 않는다.
- 시작 시 migration 실패는 DB 원본을 훼손하지 않고 명확히 중단한다.
- 외부 source 실패는 Course 단위로 격리한다.

### NFR-02 성능

- 일반 로컬 환경에서 앱 초기 화면은 5초 안에 usable 상태가 되는 것을 목표로 한다.
- Course 수십 개, Lesson 수천 개 수준에서 Catalog와 progress 표시가 체감 지연 없이 동작해야 한다.
- network sync는 UI 전체를 장시간 막지 않아야 한다.

### NFR-03 이식성

- 경로 조합에 `pathlib`을 사용한다.
- shell 전용 경로 또는 separator를 Core에 하드코딩하지 않는다.
- Windows를 우선 검증하고 `start.sh`와 cross-platform Python command를 유지한다.

### NFR-04 보안과 개인정보

- API key와 secret을 코드, Manifest, DB export, Git에 넣지 않는다.
- `.env` 또는 플랫폼 secret storage를 사용한다.
- 외부 명령에는 검증된 repository URL과 경로를 argument list로 넘기고 shell string 보간을 피한다.
- 로컬 파일 경로는 허용된 Course/external root 안인지 검증한다.

### NFR-05 접근성과 사용성

- 핵심 행동은 Dashboard에서 두 번 이내의 클릭으로 도달한다.
- 색만으로 완료 상태를 구분하지 않는다.
- 오류 메시지는 문제, 영향 범위, 다음 행동을 포함한다.
- 모바일 최적화보다 노트북 화면의 가독성을 우선한다.

### NFR-06 유지보수성

- Course별 하드코딩 분기를 금지한다.
- public interface와 schema 변경에는 migration과 regression test가 필요하다.
- domain logic은 Streamlit 호출과 분리해 unit test가 가능해야 한다.

## 13. Data, Backup, Retention

- 사용자 생성 데이터는 기본적으로 `data/` 아래에 모은다.
- Course 콘텐츠와 사용자 상태를 분리해 Course update가 progress를 덮지 않게 한다.
- timestamp는 UTC ISO 8601로 저장하고 UI에서 local timezone으로 표시한다.
- Phase 2 초기에 ZIP 또는 JSON export와 restore를 제공한다.
- Lesson ID가 삭제되면 progress를 즉시 삭제하지 않고 orphan 상태로 보존한다.

## 14. Error Handling

| 상황 | 기대 동작 |
|---|---|
| Manifest 문법/필드 오류 | 해당 Course disabled, 정확한 파일과 원인 표시 |
| Lesson 파일 누락 | 해당 Lesson unavailable, 다른 Lesson 정상 |
| Git 미설치 | 설치 안내와 local Course 정상 사용 |
| network/clone/sync 실패 | 마지막 상태와 retry 표시, 앱 정상 유지 |
| Jupyter 미설치 | 설치 명령 안내, Markdown 학습 정상 유지 |
| DB write 실패 | 완료로 표시하지 않고 재시도 안내 |
| DB migration 실패 | 원본 보호, startup 중단, 복구 안내 |

P0 오류는 앱 실행 불가, progress 손실, Course loading 불가, Lesson/Notebook 실행 불가다. 모든 P0는 Phase 2 신규 기능보다 먼저 처리한다.

## 15. Acceptance Test Matrix

| ID | MVP 완료 조건 | 검증 방법 | 예상 결과 |
|---|---|---|---|
| AT-01 | `start.bat` 실행 | 깨끗한 Windows shell에서 실행 | 프로세스와 브라우저 시작 |
| AT-02 | 브라우저 앱 표시 | health/startup smoke test | Learning OS Dashboard 표시 |
| AT-03 | 세 Course 표시 | Catalog UI 확인 | AICE, PSPO, AI-For-Beginners 표시 |
| AT-04 | 오늘의 학습 | Course 선택 후 기본 60분으로 확인 | 선택 Course의 1~3개 Lesson과 시간 표시 |
| AT-05 | Lesson 열람 | AICE/PSPO Markdown 열기 | 콘텐츠 정상 렌더링 |
| AT-06 | AICE Notebook | Notebook action 실행 | Jupyter에서 파일 열림 |
| AT-07 | AI 원본 콘텐츠 | source clone 후 첫 항목 열기 | 원본 Markdown/Notebook 접근 |
| AT-08 | Lesson 완료 | 완료 버튼 클릭 | 완료 표시와 progress 증가 |
| AT-09 | SQLite 저장 | DB query/integration test | progress row가 정확히 1개 존재 |
| AT-10 | 재실행 persistence | 종료 후 다시 실행 | 완료 상태와 progress 동일 |

AT-01~10이 모두 통과해야 MVP 완료다. 일부 통과나 우회 설명은 완료로 보지 않는다.

## 16. Release와 운영 정책

### Phase 1 Release Gate

- AT-01~10 전체 통과
- 핵심 automated test 전체 통과
- 알려진 P0 0개
- 실행법, 구현 범위, 제한사항 문서화
- 첫 AICE/PSPO Lesson 준비

### 완료 보고 형식

Phase 1 완료 시 다음만 명확히 보고한다.

- MVP 완료 여부
- `start.bat`/`start.sh` 실행 방법
- 구현된 기능
- 알려진 제한사항
- 오늘 바로 시작할 Lesson

보고 직후 사용자가 학습을 시작하게 하고, 추가 개발은 실제 사용 피드백 또는 Phase 2 우선순위에 따라 진행한다.

## 17. Open Decisions와 Default

별도 결정이 없으면 다음 default를 사용한다.

| 항목 | Default |
|---|---|
| 앱/콘텐츠 UI 언어 | 한국어 UI, 원문 콘텐츠 허용 |
| 기본 학습 시간 | 60분 |
| 날짜/timezone | Asia/Seoul 표시, UTC 저장 |
| DB | `data/learning_os.db` |
| Course discovery | `courses/*/course.yaml` |
| 외부 source | `external/<owner>/<repository>/` |
| SQLD 상태 | `planned` |
| Analytics/AI | Phase 1 제외 |

유료 API 사용, 외부 계정 생성, 중요한 사용자 데이터 삭제, 보안 위험, 제품 방향의 큰 변경만 사용자 확인을 받는다. 나머지 세부 구현은 이 PRD와 Study First Rule에 따라 합리적인 default로 진행한다.
