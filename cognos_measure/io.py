"""I/O utilities — YAML/JSON loaders, CRD parsers, Git log readers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterator

import yaml


def load_yaml(path: Path | str) -> Any:
    """Load a YAML file, returning the parsed content."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_yaml(path: Path | str) -> list[Any]:
    """Load a multi-document YAML file."""
    with open(path, encoding="utf-8") as f:
        return list(yaml.safe_load_all(f))


def load_json(path: Path | str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_yaml_files(root: Path, pattern: str = "**/*.yaml") -> list[Path]:
    """Recursively find YAML files under root."""
    results = list(root.glob(pattern))
    results.extend(root.glob(pattern.replace(".yaml", ".yml")))
    return sorted(set(results))


def extract_crd_kinds(yaml_docs: list[dict[str, Any]]) -> list[str]:
    """Extract the 'kind' field from a list of parsed CRD documents."""
    kinds = []
    for doc in yaml_docs:
        if isinstance(doc, dict) and "kind" in doc:
            kinds.append(doc["kind"])
    return kinds


def parse_workload_bundle(bundle_dir: Path) -> dict[str, Any]:
    """Parse all YAML files in a workload bundle directory.

    Returns:
        Dict with keys: 'kinds' (list[str]), 'files' (list[Path]),
        'total_lines' (int), 'documents' (list[dict])
    """
    files = find_yaml_files(bundle_dir)
    all_docs: list[dict[str, Any]] = []
    total_lines = 0

    for f in files:
        text = f.read_text(encoding="utf-8")
        total_lines += text.count("\n") + 1
        docs = list(yaml.safe_load_all(text))
        all_docs.extend(d for d in docs if isinstance(d, dict))

    kinds = extract_crd_kinds(all_docs)
    return {
        "kinds": kinds,
        "unique_kinds": sorted(set(kinds)),
        "files": files,
        "total_lines": total_lines,
        "documents": all_docs,
    }


# --- Git log parsing ---

_GIT_LOG_PATTERN = re.compile(
    r"^(?P<hash>[a-f0-9]+)\|(?P<date>[^|]+)\|(?P<author>[^|]*)\|(?P<message>.*)$"
)


def parse_git_log_line(line: str) -> dict[str, str] | None:
    """Parse a single git log line in format: hash|date|author|message."""
    m = _GIT_LOG_PATTERN.match(line.strip())
    if m:
        return m.groupdict()
    return None


def read_git_log(log_path: Path | str) -> list[dict[str, str]]:
    """Read a pre-exported git log file (one commit per line)."""
    commits = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            parsed = parse_git_log_line(line)
            if parsed:
                commits.append(parsed)
    return commits


def iter_git_log(repo_path: Path | str, since: str = "", until: str = "") -> Iterator[dict[str, str]]:
    """Iterate over git log entries from a live repo using gitpython.

    Yields dicts with: hash, date (ISO), author, message.
    """
    from git import Repo

    repo = Repo(str(repo_path))
    kwargs: dict[str, Any] = {}
    if since:
        kwargs["since"] = since
    if until:
        kwargs["until"] = until

    for commit in repo.iter_commits("HEAD", **kwargs):
        yield {
            "hash": commit.hexsha[:12],
            "date": commit.committed_datetime.isoformat(),
            "author": str(commit.author),
            "message": commit.message.strip().split("\n")[0],
        }
