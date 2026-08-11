"""Fail CI on obvious repository secret or arbitrary-code execution regressions."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = (ROOT / "apps", ROOT / "src")
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
}
FORBIDDEN_CALLS = {"eval", "exec"}
FORBIDDEN_MODULES = {"subprocess"}
FORBIDDEN_ATTRIBUTES = {("os", "popen"), ("os", "system")}


def _repository_files() -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return tuple(
        ROOT / raw.decode("utf-8")
        for raw in result.stdout.split(b"\0")
        if raw and (ROOT / raw.decode("utf-8")).is_file()
    )


def _secret_findings(files: tuple[Path, ...]) -> list[str]:
    findings: list[str] = []
    for path in files:
        relative = path.relative_to(ROOT)
        if relative.name == ".env" or (
            relative.name.startswith(".env.") and relative.name != ".env.example"
        ):
            findings.append(f"tracked_or_unignored_env:{relative}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{name}:{relative}")
    return findings


def _runtime_execution_findings() -> list[str]:
    findings: list[str] = []
    for runtime_root in RUNTIME_ROOTS:
        for path in runtime_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            relative = path.relative_to(ROOT)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".", maxsplit=1)[0] in FORBIDDEN_MODULES:
                            findings.append(f"forbidden_import:{relative}:{node.lineno}")
                elif isinstance(node, ast.ImportFrom):
                    if (node.module or "").split(".", maxsplit=1)[0] in FORBIDDEN_MODULES:
                        findings.append(f"forbidden_import:{relative}:{node.lineno}")
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                        findings.append(f"forbidden_call:{relative}:{node.lineno}")
                    if (
                        isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and (node.func.value.id, node.func.attr) in FORBIDDEN_ATTRIBUTES
                    ):
                        findings.append(f"forbidden_call:{relative}:{node.lineno}")
    return findings


def main() -> int:
    findings = [*_secret_findings(_repository_files()), *_runtime_execution_findings()]
    if findings:
        print("security_boundary_check_failed", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("security boundary checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
