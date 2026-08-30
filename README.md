# Learning OS

자격증과 실무 역량 학습을 로컬에서 이어가는 개인 학습 운영 도구다. 앱을 열고 오늘의 Lesson 또는 Review를 시작해, 완료·정확도·자신감·Note를 한곳에 누적한다.

## Setup / Run

Python 3.11 이상이 필요하다. Windows는 `start.bat`, macOS/Linux는 `./start.sh`를 실행한다. 스크립트가 프로젝트 root로 이동하고 `.venv`를 만들며 고정 dependency를 설치한 뒤 Streamlit을 실행한다. 두 번째 실행은 기존 환경을 재사용한다.

## Phase 2 기능

- Today: 학습 가능 시간, 시험일까지 남은 기간, Course 우선순위, 진도, 취약도를 반영한 Lesson 계획
- Quiz/Practice: 단일 선택, 복수 선택, 단답형 문항과 정답·오답 근거
- Review: 오답 1일, 낮은 자신감 정답 2일, 정답과 연속 정답 4/7/14/30일 간격
- Mock Exam: Course별 문항 수, 제한 시간, 목표 점수 profile
- Insights: topic별 정확도·자신감·응답 시간·취약도와 설명 가능한 Skill mastery
- Notes: Lesson별 Markdown Note, URL, 전체 검색
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

PSPO는 Scrum.org가 공개한 12개 Focus Area를 모두 추적하고, Vision·Product Goal·가치 실험·Backlog ordering·forecast·이해관계자 협업 산출물을 직접 만든다. AICE는 공식 30/30/40 배점 구조에 맞춰 데이터 분석·전처리·AI 모델링을 배우고 synthetic tabular data로 전체 파이프라인을 실행한다. 실제 비공개 시험 문항은 복제하지 않으며 모든 학습 문항에 공식 자료나 API 문서 출처를 연결한다.

## Architecture

`app.py`는 Streamlit UI, `src/learning_os/core`는 Manifest·Quiz·Review·Scheduler·Mastery 도메인, `src/learning_os/database`는 SQLite 저장소, `src/learning_os/integrations`는 Markdown·Notebook·GitHub·Backup·Import·AI provider 경계를 담당한다. `courses/`는 Manifest 기반 콘텐츠 카탈로그다.

## 새 Course와 문항 추가

`courses/<kebab-case-id>/course.yaml`에 schema version 1 Manifest를 만든다. Lesson은 Course root 상대경로 또는 HTTP(S) URL을 사용한다. `questions.yaml`은 `question_id`, `skill_id`, `topic`, `difficulty`, `type`, `prompt`, `correct_answers`, `explanation`을 선언한다. 앱 코드 수정 없이 재실행하면 카탈로그와 문항 은행에 반영된다.

## Data / Backup

사용자 데이터는 `data/learning_os.db`, 백업은 `data/backups/`에 저장되며 Git에서 제외된다. Settings에서 백업을 생성하거나 복원할 수 있다. 복원 전 현재 DB를 safety backup하며, archive와 SQLite 무결성 검증에 실패하면 원본을 변경하지 않는다.

## 현재 제한

- 단일 사용자·로컬 실행을 기준으로 하며 클라우드 동기화는 없다.
- AI Tutor의 실제 Provider는 아직 연결하지 않았고 기본값은 disabled다.
- 전체 문항 은행은 118문항이다. PSPO는 80문항 전체 모의고사를 지원하며 AICE는 공식 14문항 시험의 두 배 분량을 제공한다. AI for Beginners와 SQLD 문항은 아직 소규모다.
- PDF는 Course 안에 보관하고 열기/저장을 지원하지만 OCR·본문 검색은 아직 하지 않는다.

## 오늘 첫 학습

Dashboard에서 PSPO I의 `PSPO I 평가 구조와 합격 전략` 또는 AICE의 `Associate 시험 직전 체크리스트`부터 시작한다. 답을 제출할 때 자신감을 함께 기록하면 다음 Review 날짜와 Skill mastery가 자동으로 계산된다.
