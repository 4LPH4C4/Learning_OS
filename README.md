# Learning OS

자격증과 실무 역량 학습을 로컬에서 이어가는 개인 학습 운영 도구다. 앱을 열고 오늘의 학습 또는 복습을 시작해, 완료·정확도·자신감·Note를 한곳에 누적한다.

## Setup / Run

Python 3.11 이상이 필요하다. Windows는 `start.bat`, macOS/Linux는 `./start.sh`를 실행한다. 스크립트가 프로젝트 root로 이동하고 `.venv`를 만들며 고정 dependency를 설치한 뒤 Streamlit을 실행한다. 두 번째 실행은 기존 환경을 재사용한다.

## Phase 2 기능

- Course 선택: Courses에서 학습 대상을 고르고 선택값을 로컬에 저장
- 오늘의 학습: 선택한 Course만 대상으로 날짜별 학습 범위 생성, 완료/다음 Lesson 구분
- Quiz/Practice: 단일 선택, 복수 선택, 단답형 문항과 정답·오답 근거
- 복습: 선택한 Course의 지난 풀이를 퀴즈로 제공하고 1/2/4/7/14/30일 간격으로 반복
- Mock Exam: Course별 문항 수, 제한 시간, 목표 점수 profile
- Placement: 단계별·누적 정답률로 권장 시작 등급을 정하고 이후 학습 경로를 자동 조정
- Fixed Mock Sets: 회차별 고정 문항, 제한 시간, 최근 점수 저장과 재응시
- Insights: 날짜별 Lesson·문제 풀이 캘린더, 학습 시간, topic별 정확도·자신감·취약도와 Skill mastery
- Notes: Lesson별 Markdown Note, URL, 전체 검색
- Glossary: Course별 핵심 용어와 Lesson 안의 개념 설명 팝업
- Settings: 기본 학습 시간, 한국어/영어 콘텐츠 선택
- Backup/Restore: checksum과 SQLite 무결성 검사를 포함한 로컬 ZIP 백업
- Course Import: URL, PDF, Markdown을 Manifest Course로 가져오기
- AI Tutor: optional `AIProvider` 경계. Provider나 API key가 없어도 Core 기능은 모두 동작

## 기본 Course

| Course | 상태 | Phase 2 학습 자료 |
|---|---|---|
| PSPO I | active | 7개 모듈·16개 Lesson, 독창 scenario 80문항, 80문항/60분 full mock |
| AICE Associate | active | 5개 모듈·17개 Lesson, 실행 가능한 Notebook 2개, 독창 문항 28개, 14문항/90분 mock |
| AI for Beginners | active | Microsoft 공식 원본 Lesson, 개념 점검 4개 |
| SQLD | active | 데이터 모델링 Lesson, Quiz 6개, 50문항/90분 profile |
| English — CEFR A1 to C2 | active | 36문항 진단, A1~C2 단계별 2개 Lesson, 용어 15개 |
| 중국어 — 입문부터 HSK 9까지 | active | 50문항 진단, 입문·HSK 1~9 단계별 2개 Lesson, 용어 31개 |
| NCS 직업공통능력 | active | 2026년 7개 영역 이론, 독창 종합 모의고사 10회×50문항, 용어 37개 |

PSPO는 Scrum.org가 공개한 12개 Focus Area를 모두 추적하고, Vision·Product Goal·가치 실험·Backlog ordering·forecast·이해관계자 협업 산출물을 직접 만든다. AICE는 공식 30/30/40 배점 구조에 맞춰 데이터 분석·전처리·AI 모델링을 배우고 synthetic tabular data로 전체 파이프라인을 실행한다. 영어는 Council of Europe CEFR, 중국어는 Chinese Test의 HSK 3.0, NCS는 2026년 공식 직업공통능력 체계를 기준으로 삼는다. 실제 비공개 시험 문항이나 공개 모의평가 원문은 복제하지 않고, 공식 가이드에 근거한 독창 문항과 해설을 제공한다.

## Architecture

`app.py`는 Streamlit UI, `src/learning_os/core`는 Manifest·Quiz·Review·Scheduler·Mastery 도메인, `src/learning_os/database`는 SQLite 저장소, `src/learning_os/integrations`는 Markdown·Notebook·GitHub·Backup·Import·AI provider 경계를 담당한다. `courses/`는 Manifest 기반 콘텐츠 카탈로그다.

## 새 Course와 문항 추가

`courses/<kebab-case-id>/course.yaml`에 schema version 1 Manifest를 만든다. Lesson은 Course root 상대경로 또는 HTTP(S) URL을 사용한다. `duration_minutes`는 읽기만이 아니라 이해 확인과 적용까지 포함한 총 학습 시간이다. 정확한 시간 구성이 필요하면 Lesson에 `study_steps`를 추가한다.

Course 용어사전은 `glossary_path: glossary.yaml`로 연결한다. 용어 파일은 `version`, `course_id`, `terms`를 가지며 각 용어에 `id`, `name`, `aliases`, `short_definition`, `explanation`, `example`, `related_terms`, 선택적 `source_url`을 선언한다. Lesson 본문에 등장한 이름과 별칭은 자동으로 감지되어 팝업으로 표시된다.

`questions.yaml`은 `id`, `skill_id`, `topic`, `difficulty`, `type`, `prompt`, `correct_answers`, `explanation`을 선언한다. 적응형 코스는 Lesson과 문항에 `level`, 진단·고정 모의고사는 문항에 `sets`를 추가한다. `quiz_settings.placement`의 순서화된 단계와 통과 기준 또는 `quiz_settings.mock_exam_sets`의 회차 profile을 선언하면 Course ID를 앱에 하드코딩하지 않고 같은 엔진을 재사용한다.

## Data / Backup

사용자 데이터는 `data/learning_os.db`, 백업은 `data/backups/`에 저장되며 Git에서 제외된다. Settings에서 백업을 생성하거나 복원할 수 있다. 복원 전 현재 DB를 safety backup하며, archive와 SQLite 무결성 검증에 실패하면 원본을 변경하지 않는다.

## 현재 제한

- 단일 사용자·로컬 실행을 기준으로 하며 클라우드 동기화는 없다.
- AI Tutor의 실제 Provider는 아직 연결하지 않았고 기본값은 disabled다.
- 전체 문항 은행은 704문항이다. 영어·중국어 진단은 읽기·어휘·문법·상황 판단 중심이므로 듣기·말하기까지 포함한 공인 등급 판정은 아니다. NCS 500문항은 공식 공개 문제의 복제가 아닌 학습용 독창 문항이다.
- PDF는 Course 안에 보관하고 열기/저장을 지원하지만 OCR·본문 검색은 아직 하지 않는다.

## 첫 학습

Courses에서 공부할 Course를 먼저 선택한다. `오늘의 학습`은 선택한 Course만 대상으로 오늘 계획을 만들고, `복습`은 같은 Course에서 이전에 푼 문항을 다시 보여준다. 영어·중국어는 첫 진단을 마치면 권장 단계부터 학습 경로가 열리고, NCS는 Course 화면에서 1~10회 중 한 회차를 골라 50문항을 푼다. 답을 제출할 때 자신감을 함께 기록하면 다음 복습 날짜와 Skill mastery가 자동으로 계산된다.
