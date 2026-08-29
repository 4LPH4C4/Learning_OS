"""Safe, local-first synchronization of GitHub course sources."""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from learning_os.config import Settings
from learning_os.core.models import ContentSource, Course, SourceState


_GITHUB_URL = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")


class SourceError(RuntimeError):
    """Raised when a source cannot safely be inspected or synchronized."""


class GitHubSourceManager:
    def __init__(self, settings: Settings, *, timeout: float = 120.0) -> None:
        self.settings = settings
        self.timeout = timeout
        self._sync_times: dict[Path, str] = {}

    def source_path(self, course: Course | str, source: ContentSource) -> Path:
        course_id = course.id if isinstance(course, Course) else str(course)
        root = self.settings.external_dir.resolve()
        if source.local_path:
            candidate = Path(source.local_path)
            if not candidate.is_absolute():
                candidate = root / candidate
        else:
            candidate = root / course_id / source.id
        candidate = candidate.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise SourceError("source local_path가 external 디렉터리 밖을 가리킨다") from exc
        return candidate

    @staticmethod
    def validate_repository_url(url: str) -> str:
        match = _GITHUB_URL.fullmatch(url.strip())
        if not match:
            raise SourceError("HTTPS GitHub repository URL만 허용한다")
        return f"https://github.com/{match.group(1)}/{match.group(2)}.git"

    def _run(self, args: Sequence[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        command = list(args)
        if cwd is not None and command and command[0] == "git":
            # The repository path is already constrained to external/. Trust only
            # that exact checkout without changing the user's global Git config.
            command[1:1] = ["-c", f"safe.directory={cwd.resolve()}"]
        try:
            result = subprocess.run(
                command, cwd=str(cwd) if cwd else None, shell=False,
                check=False, capture_output=True, text=True, timeout=self.timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SourceError(f"git 실행에 실패했다: {exc}") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise SourceError(f"git 명령이 실패했다 ({result.returncode}): {detail}")
        return result

    def current_commit(self, path: Path) -> str | None:
        try:
            return self._run(["git", "rev-parse", "HEAD"], path).stdout.strip() or None
        except SourceError:
            return None

    def last_sync(self, path: Path) -> str | None:
        path = path.resolve()
        if path in self._sync_times:
            return self._sync_times[path]
        # A manager created after a restart can still provide a useful sync
        # indicator without inventing a database of its own.
        for marker in (path / ".git" / "FETCH_HEAD", path / ".git" / "logs" / "HEAD"):
            try:
                return datetime.fromtimestamp(marker.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
            except OSError:
                continue
        return None

    def inspect(self, course: Course | str, source: ContentSource) -> SourceState:
        path = self.source_path(course, source)
        if not path.is_dir() or not (path / ".git").exists():
            return SourceState(source.id, course.id if isinstance(course, Course) else str(course), "unavailable", path,
                               source.repository_url, error_message="로컬 Git checkout이 없다", available=False)
        commit = self.current_commit(path)
        if not commit:
            return SourceState(source.id, course.id if isinstance(course, Course) else str(course), "unavailable", path,
                               source.repository_url, error_message="Git commit을 읽을 수 없다", available=False)
        return SourceState(source.id, course.id if isinstance(course, Course) else str(course), "ready", path,
                           source.repository_url, commit, self.last_sync(path), available=True)

    status = inspect
    inspect_source = inspect

    def clone(self, course: Course | str, source: ContentSource) -> SourceState:
        path = self.source_path(course, source)
        if source.type != "github":
            raise SourceError("GitHubSourceManager에는 github source만 전달할 수 있다")
        if path.exists() and any(path.iterdir()):
            raise SourceError(f"clone 대상 디렉터리가 비어 있지 않다: {path}")
        if not source.repository_url:
            raise SourceError("GitHub repository URL이 없다")
        url = self.validate_repository_url(source.repository_url)
        if source.branch and source.branch.startswith("-"):
            raise SourceError("branch 이름이 유효하지 않다")
        for sparse_path in source.sparse_paths:
            sparse = Path(sparse_path)
            if sparse.is_absolute() or sparse_path.startswith("-") or ".." in sparse.parts:
                raise SourceError("sparse path가 유효하지 않다")
        path.parent.mkdir(parents=True, exist_ok=True)
        args = ["git", "clone", "--filter=blob:none", "--depth=1"]
        if source.branch:
            args += ["--branch", source.branch]
        if source.sparse_paths:
            args.append("--sparse")
        args += [url, str(path)]
        self._run(args)
        if source.sparse_paths:
            try:
                self._run(["git", "sparse-checkout", "init", "--cone"], path)
                self._run(["git", "sparse-checkout", "set", *source.sparse_paths], path)
            except SourceError as exc:
                raise SourceError(f"sparse checkout 구성에 실패했다: {exc}") from exc
        state = self.inspect(course, source)
        self._sync_times[path.resolve()] = self.now()
        return SourceState(state.source_id, state.course_id, state.status, state.local_path,
                           state.repository_url, state.commit_sha, self._sync_times[path.resolve()],
                           state.error_message, state.available)

    def update(self, course: Course | str, source: ContentSource) -> SourceState:
        path = self.source_path(course, source)
        if not path.is_dir() or not (path / ".git").exists():
            raise SourceError("update할 Git checkout이 없다")
        self._run(["git", "pull", "--ff-only"], path)
        state = self.inspect(course, source)
        self._sync_times[path.resolve()] = self.now()
        return SourceState(state.source_id, state.course_id, state.status, state.local_path,
                           state.repository_url, state.commit_sha, self._sync_times[path.resolve()],
                           state.error_message, state.available)

    def sync(self, course: Course | str, source: ContentSource) -> SourceState:
        path = self.source_path(course, source)
        return self.update(course, source) if (path / ".git").exists() else self.clone(course, source)

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
