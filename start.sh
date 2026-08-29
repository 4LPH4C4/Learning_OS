#!/usr/bin/env bash
set -u
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || { echo "[Learning OS] 프로젝트 폴더로 이동하지 못했다." >&2; exit 1; }
cd "$ROOT_DIR" || { echo "[Learning OS] 프로젝트 폴더로 이동하지 못했다." >&2; exit 1; }

python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' || {
  echo "[Learning OS] Python 3.11 이상이 필요하다." >&2
  exit 1
}

INSTALL_DEPS=0
if [[ ! -x ".venv/bin/python" ]]; then
  echo "[Learning OS] 가상환경을 생성한다."
  python3 -m venv .venv || { echo "[Learning OS] 가상환경 생성에 실패했다." >&2; exit 1; }
  INSTALL_DEPS=1
fi

if [[ "$INSTALL_DEPS" -eq 0 ]] && ! .venv/bin/python -c 'import streamlit, yaml, pandas, jupyterlab'; then
  INSTALL_DEPS=1
fi
if [[ "$INSTALL_DEPS" -eq 1 ]]; then
  echo "[Learning OS] requirements.txt를 설치한다."
  .venv/bin/python -m pip install -r requirements.txt || { echo "[Learning OS] 의존성 설치에 실패했다." >&2; exit 1; }
fi

echo "[Learning OS] 앱을 시작한다."
.venv/bin/python -m streamlit run app.py || { echo "[Learning OS] Streamlit 실행에 실패했다." >&2; exit 1; }
