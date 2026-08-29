# Learning OS

자격증과 실무 역량 학습을 로컬에서 이어가는 Phase 1 학습 운영 도구다. 목표는 앱을 켜고 오늘 Lesson을 시작해 완료 기록을 남기는 흐름을 짧게 만드는 것이다.

## Setup / Run

Python 3.11 이상이 필요하다. Windows는 `start.bat`, macOS/Linux는 `./start.sh`를 실행한다. 스크립트가 root로 이동하고 `.venv`를 만들며 `requirements.txt`를 설치한 뒤 Streamlit을 실행한다. 두 번째 실행은 기존 환경을 재사용하고 핵심 import가 실패할 때만 의존성을 다시 설치한다.

## Architecture

`app.py`는 Streamlit UI, `src/learning_os/core`는 manifest·추천·도메인 모델, `src/learning_os/database`는 SQLite 저장, `src/learning_os/integrations`는 Markdown·Notebook·GitHub 연동을 담당한다. `courses/`는 manifest 기반 콘텐츠 카탈로그다.

## 새 Course 추가

`courses/<kebab-case-id>/course.yaml`에 schema version 1 manifest를 만들고, `content_sources`에 `type: local`, `base_path: .`을 선언한다. Lesson의 `content_path` 또는 `notebook_path`는 Course root 상대경로로 작성한다. 앱 코드 수정 없이 재실행하면 카탈로그에 반영된다.

## GitHub Course 추가

manifest의 `content_sources`에 `type: github`, `repository_url`, 선택적으로 `branch`와 `sparse_paths`를 지정한다. Lesson은 해당 source를 참조하고, 앱의 source 준비 흐름에서 clone/sync한다. 네트워크가 없어도 다른 local Course는 계속 사용할 수 있다.

## Data / Backup

진도 DB는 `data/learning_os.db`에 저장된다. 앱을 종료한 뒤 이 파일을 다른 디스크에 복사하면 수동 백업이며, 복구할 때는 앱을 종료하고 백업 파일을 같은 경로에 되돌린다. Course 콘텐츠와 DB를 함께 백업해야 재현성이 유지된다.

## Phase 1 현재 기능과 제한

현재 Dashboard, 오늘의 학습 추천, Markdown Lesson, Jupyter Notebook 실행, 완료·학습 세션 저장, local/GitHub source 기본 흐름을 지원한다. Quiz·간격 반복·AI 튜터·다중 사용자·자동 클라우드 백업은 아직 지원하지 않는다.

## 오늘 첫 학습

Dashboard에서 목표일이 가까운 PSPO I의 `Scrum Theory와 경험주의`(30분)를 먼저 읽고, 투명성·검사·적응을 자신의 제품 사례에 적어본다. 다음으로 AICE Associate의 `pandas 첫걸음`(25분)을 시작하고 Notebook 실습을 이어간다.
