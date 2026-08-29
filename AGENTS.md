# Learning OS 작업 원칙

- 아키텍처는 로컬 우선이다. UI(`app.py`), 핵심 도메인(`src/learning_os/core`), 저장소(`src/learning_os/database`), 외부 연동(`src/learning_os/integrations`)의 경계를 유지한다.
- Course는 `courses/*/course.yaml`과 콘텐츠로 확장한다. 앱 코드에 Course ID나 Lesson을 하드코딩하지 않는다.
- 데이터 스키마를 바꿀 때는 migration을 추가하고, 기존 DB와 manifest의 backward compatibility를 보장한다.
- 변경 전후 관련 테스트를 실행하고, 실패 원인과 검증 결과를 기록한다.
- Study First Rule: 기능을 추가할 때도 사용자가 오늘의 Lesson을 즉시 시작하고 완료할 수 있는 흐름을 우선 보호한다.

## Ownership

Course 콘텐츠는 각 Course 디렉터리가 소유한다. 실행 스크립트와 프로젝트 문서는 root 소유다. 다른 영역을 수정해야 하면 먼저 범위를 합의한다.
