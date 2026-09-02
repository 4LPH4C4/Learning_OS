from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from learning_os.config import Settings
from learning_os.core.manifests import load_manifest
from learning_os.core.models import ContentSource
from learning_os.integrations import content_loader, github_source, notebook_launcher

ROOT = Path(__file__).parents[1]

def test_app_dashboard_smoke() -> None:
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    result = AppTest.from_file(str(ROOT / "app.py"), default_timeout=10).run()

    assert not result.exception
    assert "Learning OS" in result.title[0].value
    assert "오늘의 학습" in [header.value for header in result.header]
    page_text = "\n".join(markdown.value for markdown in result.markdown)
    assert "선택 Course" in page_text


def test_local_markdown_loader_reads_and_reports_missing() -> None:
    course = load_manifest(ROOT / "courses" / "pspo-i" / "course.yaml")
    lesson = course.lessons[0]

    assert content_loader.read_markdown(course, lesson, ROOT / "external").strip()
    missing = lesson.__class__(**{**lesson.__dict__, "content_path": "lessons/missing.md"})
    with pytest.raises(content_loader.ContentUnavailableError, match="파일을 찾을 수 없다"):
        content_loader.read_markdown(course, missing, ROOT / "external")


def test_notebook_launcher_uses_argument_list_and_shell_false(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    notebook = tmp_path / "공부 파일.ipynb"
    notebook.write_text("{}", encoding="utf-8")
    calls: list[tuple[list[str], dict]] = []

    def fake_popen(args: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((args, kwargs))
        return SimpleNamespace(pid=1234)

    monkeypatch.setattr(notebook_launcher.subprocess, "Popen", fake_popen)
    assert notebook_launcher.launch_notebook(notebook, tmp_path) == 1234
    assert calls[0][0][0] == notebook_launcher.sys.executable
    assert calls[0][0][1:5] == ["-m", "jupyter", "lab", str(notebook.resolve())]
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["cwd"] == tmp_path


def test_github_source_rejects_invalid_url_and_external_path(tmp_path: Path) -> None:
    settings = Settings(project_root=tmp_path, external_dir=tmp_path / "external")
    manager = github_source.GitHubSourceManager(settings)
    source = ContentSource(id="origin", type="github", repository_url="https://github.com/acme/repo")

    assert manager.validate_repository_url("https://github.com/acme/repo/") == "https://github.com/acme/repo.git"
    with pytest.raises(github_source.SourceError, match="HTTPS GitHub"):
        manager.validate_repository_url("https://evil.example/acme/repo")
    with pytest.raises(github_source.SourceError, match="밖"):
        manager.source_path("course", ContentSource(id="origin", type="github", local_path="../escape"))
    unavailable = manager.inspect("course", source)
    assert unavailable.available is False
    assert unavailable.status == "unavailable"


def test_github_clone_uses_safe_git_arguments_without_network(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings(project_root=tmp_path, external_dir=tmp_path / "external")
    manager = github_source.GitHubSourceManager(settings)
    source = ContentSource(
        id="origin", type="github", repository_url="https://github.com/acme/repo", branch="main",
        sparse_paths=("lessons",),
    )
    calls: list[tuple[list[str], dict]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        if "clone" in args:
            Path(args[-1], ".git").mkdir(parents=True)
        stdout = "abc123\n" if "rev-parse" in args else ""
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(github_source.subprocess, "run", fake_run)
    state = manager.clone("course", source)

    assert state.available
    assert calls[0][0][:5] == ["git", "clone", "--filter=blob:none", "--depth=1", "--branch"]
    assert calls[0][0][-2:] == ["https://github.com/acme/repo.git", str(settings.external_dir / "course" / "origin")]
    assert all(call[1]["shell"] is False for call in calls)
