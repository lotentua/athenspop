"""Repository-level contracts that prevent architectural drift."""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]


def test_root_import_stays_clear_of_plotting_modules() -> None:
    """Importing the package root does not import plotting modules as a side effect."""
    code = (
        "import sys\n"
        "import athenspop\n"
        "loaded = ('matplotlib.pyplot' in sys.modules, "
        "'athenspop.visualization' in sys.modules)\n"
        "raise SystemExit(1 if any(loaded) else 0)"
    )

    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603


def test_matplotlib_is_a_visualization_extra_not_a_core_dependency() -> None:
    """Plotting stays optional while tests install it deliberately."""
    pyproject = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )

    core_dependencies = pyproject["project"]["dependencies"]
    visualization_dependencies = pyproject["project"]["optional-dependencies"][
        "visualization"
    ]
    dev_dependencies = pyproject["dependency-groups"]["dev"]

    assert all(
        not dependency.startswith("matplotlib") for dependency in core_dependencies
    )
    assert any(
        dependency.startswith("matplotlib") for dependency in visualization_dependencies
    )
    assert any(
        isinstance(dependency, str) and dependency.startswith("matplotlib")
        for dependency in dev_dependencies
    )


def test_sdist_excludes_private_generated_and_local_artifacts(
    tmp_path: Path,
) -> None:
    """The source distribution contains only the generic package surface."""
    uv_executable = shutil.which("uv")

    assert uv_executable is not None

    subprocess.run(  # noqa: S603
        [uv_executable, "build", "--sdist", "--out-dir", str(tmp_path)],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    archive_path = next(tmp_path.glob("*.tar.gz"))

    with tarfile.open(archive_path, "r:gz") as archive:
        archive_names = tuple(archive.getnames())

    forbidden_fragments = (
        "/.claude/",
        "/CSuM2026.pdf",
        "/CSuM2026.zip",
        "/docs/",
        "/examples/",
        "/tests/",
    )

    assert [
        name
        for name in archive_names
        for fragment in forbidden_fragments
        if fragment in name
    ] == []


def test_no_validation_schema_internal_imports() -> None:
    """Tests and examples use neutral schema contracts, not validation internals."""
    forbidden_imports: list[str] = []

    for path in _python_files_under("tests", "examples"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "athenspop.validation.schema"
            ):
                forbidden_imports.append(
                    f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}"
                )
            if isinstance(node, ast.Import):
                forbidden_imports.extend(
                    f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}"
                    for alias in node.names
                    if alias.name == "athenspop.validation.schema"
                )

    assert forbidden_imports == []


def test_source_import_graph_preserves_layer_boundaries() -> None:
    """Keep visualization optional and validation internals at the boundary."""
    violations: list[str] = []

    for path in _python_files_under("src"):
        module_name = _module_name(path)
        imported_modules = _imported_modules(path)
        if not module_name.startswith("athenspop.visualization"):
            violations.extend(
                f"{path.relative_to(PROJECT_ROOT)} imports {imported_module}"
                for imported_module in imported_modules
                if imported_module == "athenspop.visualization"
                or imported_module.startswith("athenspop.visualization.")
            )
        if module_name.startswith("athenspop.model"):
            violations.extend(
                f"{path.relative_to(PROJECT_ROOT)} imports {imported_module}"
                for imported_module in imported_modules
                if imported_module == "athenspop.validation.schema"
            )
        if not module_name.startswith("athenspop.visualization"):
            violations.extend(
                f"{path.relative_to(PROJECT_ROOT)} imports {imported_module}"
                for imported_module in imported_modules
                if imported_module == "matplotlib"
                or imported_module.startswith("matplotlib.")
            )

    assert violations == []


def _python_files_under(*root_names: str) -> tuple[Path, ...]:
    """Return maintained Python files below named project roots."""
    return tuple(
        sorted(
            path
            for root_name in root_names
            for path in (PROJECT_ROOT / root_name).rglob("*.py")
            if "__pycache__" not in path.parts
        )
    )


def _module_name(path: Path) -> str:
    """Return the importable module name for a Python source file."""
    relative = path.relative_to(PROJECT_ROOT / "src").with_suffix("")
    return ".".join(relative.parts)


def _imported_modules(path: Path) -> set[str]:
    """Return absolute module names imported by one Python file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)

    return imported_modules
