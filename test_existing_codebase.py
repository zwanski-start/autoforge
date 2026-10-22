"""
Existing Codebase Onboarding Tests
==================================

Tests for detecting code already present in a project folder and scaffolding
the existing-codebase mode (marker file + dedicated initializer prompt).

Run with: python -m pytest test_existing_codebase.py
"""

from pathlib import Path

import pytest

from prompts import (
    TEMPLATES_DIR,
    detect_existing_codebase,
    is_existing_codebase_project,
    scaffold_project_prompts,
)


def _write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestDetectExistingCodebase:
    def test_empty_directory(self, tmp_path):
        assert detect_existing_codebase(tmp_path) is False

    def test_missing_directory(self, tmp_path):
        assert detect_existing_codebase(tmp_path / "nope") is False

    @pytest.mark.parametrize("manifest", ["package.json", "pyproject.toml", "go.mod", "Cargo.toml"])
    def test_root_manifest(self, tmp_path, manifest):
        _write(tmp_path / manifest, "{}")
        assert detect_existing_codebase(tmp_path) is True

    def test_nested_manifest_alone_is_not_enough(self, tmp_path):
        _write(tmp_path / "docs" / "package.json", "{}")
        assert detect_existing_codebase(tmp_path) is False

    def test_source_files(self, tmp_path):
        for name in ("a.py", "b.py", "pkg/c.py"):
            _write(tmp_path / "src" / name)
        assert detect_existing_codebase(tmp_path) is True

    def test_too_few_source_files(self, tmp_path):
        _write(tmp_path / "script.sh")
        _write(tmp_path / "notes.md")
        assert detect_existing_codebase(tmp_path) is False

    def test_ignores_dependency_and_vcs_dirs(self, tmp_path):
        for i in range(5):
            _write(tmp_path / "node_modules" / "lib" / f"m{i}.js")
            _write(tmp_path / ".git" / "hooks" / f"h{i}.sh")
            _write(tmp_path / "venv" / "lib" / f"p{i}.py")
        assert detect_existing_codebase(tmp_path) is False

    def test_fresh_scaffold_is_not_existing_code(self, tmp_path):
        scaffold_project_prompts(tmp_path)
        assert detect_existing_codebase(tmp_path) is False


class TestScaffoldExistingCodebase:
    def _initializer(self, project_dir: Path) -> str:
        return (project_dir / ".autoforge" / "prompts" / "initializer_prompt.md").read_text(encoding="utf-8")

    def test_existing_template_exists(self):
        template = TEMPLATES_DIR / "initializer_prompt_existing.template.md"
        assert template.exists()
        assert "[FEATURE_COUNT]" in template.read_text(encoding="utf-8")

    def test_greenfield_scaffold(self, tmp_path):
        scaffold_project_prompts(tmp_path)
        assert not is_existing_codebase_project(tmp_path)
        expected = (TEMPLATES_DIR / "initializer_prompt.template.md").read_text(encoding="utf-8")
        assert self._initializer(tmp_path) == expected

    def test_existing_scaffold(self, tmp_path):
        _write(tmp_path / "package.json", "{}")
        scaffold_project_prompts(tmp_path, existing_codebase=True)
        assert is_existing_codebase_project(tmp_path)
        expected = (TEMPLATES_DIR / "initializer_prompt_existing.template.md").read_text(encoding="utf-8")
        assert self._initializer(tmp_path) == expected
        # The user's files are untouched
        assert (tmp_path / "package.json").read_text(encoding="utf-8") == "{}"

    def test_existing_scaffold_replaces_untouched_default_initializer(self, tmp_path):
        scaffold_project_prompts(tmp_path)
        scaffold_project_prompts(tmp_path, existing_codebase=True)
        assert "EXISTING CODEBASE" in self._initializer(tmp_path)

    def test_existing_scaffold_keeps_customized_initializer(self, tmp_path):
        scaffold_project_prompts(tmp_path)
        initializer = tmp_path / ".autoforge" / "prompts" / "initializer_prompt.md"
        initializer.write_text("my custom prompt", encoding="utf-8")
        scaffold_project_prompts(tmp_path, existing_codebase=True)
        assert self._initializer(tmp_path) == "my custom prompt"
