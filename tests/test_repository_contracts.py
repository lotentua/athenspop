"""Repository-level contracts that prevent architectural drift."""

from __future__ import annotations

import ast
import io
import shutil
import subprocess
import sys
import tarfile
import tokenize
import tomllib
from pathlib import Path
from typing import Final

STRUCTURAL_CODE_LINE_LIMIT: Final[int] = 80
PROSE_TOKEN_TYPES: Final[set[int]] = {
    tokenize.STRING,
    tokenize.COMMENT,
    getattr(tokenize, "FSTRING_START", -1),
    getattr(tokenize, "FSTRING_MIDDLE", -1),
    getattr(tokenize, "FSTRING_END", -1),
}
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
PYTHON_SOURCE_ROOTS: Final[tuple[Path, ...]] = (
    PROJECT_ROOT / "src",
    PROJECT_ROOT / "tests",
    PROJECT_ROOT / "examples",
)


def test_default_pytest_collection_includes_maintained_example_tests() -> None:
    """Default pytest collection covers generic tests and maintained Athens example tests."""
    pyproject = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )

    testpaths = pyproject["tool"]["pytest"]["ini_options"]["testpaths"]

    assert testpaths == ["tests", "examples/athens/tests"]


def test_root_package_does_not_import_visualization_module() -> None:
    """The root package stays independent from optional plotting imports."""
    tree = ast.parse(
        (PROJECT_ROOT / "src" / "athenspop" / "__init__.py").read_text(
            encoding="utf-8"
        )
    )

    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert "athenspop.visualization" not in imported_modules
    assert all(
        not module.startswith("athenspop.visualization.")
        for module in imported_modules
    )


def test_root_import_stays_clear_of_plotting_modules() -> None:
    """Importing the package root does not import plotting modules as a side effect."""
    code = (
        "import sys\n"
        "import athenspop\n"
        "loaded = ('matplotlib.pyplot' in sys.modules, 'athenspop.visualization' in sys.modules)\n"
        "raise SystemExit(1 if any(loaded) else 0)"
    )

    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603


def test_matplotlib_is_a_visualization_extra_not_a_core_dependency() -> None:
    """Plotting stays optional for non-visualization users while tests install it deliberately."""
    pyproject = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )

    core_dependencies = pyproject["project"]["dependencies"]
    visualization_dependencies = pyproject["project"]["optional-dependencies"][
        "visualization"
    ]
    dev_dependencies = pyproject["dependency-groups"]["dev"]

    assert all(
        not dependency.startswith("matplotlib")
        for dependency in core_dependencies
    )
    assert any(
        dependency.startswith("matplotlib")
        for dependency in visualization_dependencies
    )
    assert any(
        isinstance(dependency, str) and dependency.startswith("matplotlib")
        for dependency in dev_dependencies
    )


def test_tracked_repository_files_do_not_include_bytecode_artifacts() -> None:
    """Tracked source, test, and example files exclude generated Python bytecode."""
    git_executable = shutil.which("git")

    assert git_executable is not None

    result = subprocess.run(  # noqa: S603
        [git_executable, "ls-files", "src", "tests", "examples"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    tracked_paths = tuple(Path(path) for path in result.stdout.splitlines())

    assert not [
        path
        for path in tracked_paths
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}
    ]


def test_sdist_excludes_private_generated_and_local_artifacts(
    tmp_path: Path,
) -> None:
    """The source distribution omits private notes, generated docs, and local data."""
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
        "/docs/_build/",
        "/docs/design/",
        "/docs/plans/",
        "/examples/athens/data/",
        "/tests/example_data/",
    )

    assert [
        name
        for name in archive_names
        for fragment in forbidden_fragments
        if fragment in name
    ] == []


def test_no_validation_schema_internal_imports() -> None:
    """Tests and maintained examples use neutral schema contracts, not validation internals."""
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
    """Source modules keep visualization optional and validation internals at the boundary."""
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


def test_shared_type_aliases_are_defined_only_once() -> None:
    """Cross-module callable and matrix aliases have one neutral owner."""
    duplicate_aliases: list[str] = []

    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.TypeAlias)
                and isinstance(node.name, ast.Name)
                and node.name.id
                in {"DissimilarityMatrix", "TravelTimeFunction"}
                and path.name != "types.py"
            ):
                duplicate_aliases.extend(
                    [
                        f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:{node.name.id}"
                    ]
                )

    assert duplicate_aliases == []


def test_time_unit_constants_are_defined_only_in_time_units_module() -> None:
    """Common second-unit constants have one neutral owner."""
    duplicate_constants: list[str] = []

    for path in _python_files():
        if path == PROJECT_ROOT / "src" / "athenspop" / "time_units.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id
                in {"SECONDS_PER_DAY", "SECONDS_PER_HOUR", "SECONDS_PER_MINUTE"}
            ):
                duplicate_constants.extend(
                    [
                        f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:{node.target.id}"
                    ]
                )

    assert duplicate_constants == []


def test_final_annotations_are_explicitly_parameterized() -> None:
    """Every `Final` annotation includes a bracketed concrete type."""
    bare_final_locations: list[str] = []

    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign) and _is_bare_final(
                node.annotation
            ):
                bare_final_locations.extend(
                    [f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}"]
                )

    assert bare_final_locations == []


def test_structural_python_code_lines_fit_configured_width() -> None:
    """Structural Python code lines stay within the configured 80-character width."""
    pyproject = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    violations: list[str] = []

    assert pyproject["tool"]["ruff"]["line-length"] == STRUCTURAL_CODE_LINE_LIMIT

    for path in _python_files():
        text = path.read_text(encoding="utf-8")
        prose_lines = _string_or_comment_lines(text)
        for line_number, line in enumerate(text.splitlines(), start=1):
            if len(line) <= STRUCTURAL_CODE_LINE_LIMIT:
                continue
            if line_number in prose_lines or not line.strip():
                continue
            violations.append(
                f"{path.relative_to(PROJECT_ROOT)}:{line_number}:{len(line)}"
            )

    assert violations == []


def _python_files() -> tuple[Path, ...]:
    """Return maintained Python files, excluding generated caches."""
    return _python_files_under("src", "tests", "examples")


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


def _is_bare_final(annotation: ast.expr) -> bool:
    """Return whether an annotation uses `Final` without type arguments."""
    return isinstance(annotation, ast.Name) and annotation.id == "Final"


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


def _string_or_comment_lines(text: str) -> set[int]:
    """Return lines occupied by strings or comments, which may contain unwrapped prose."""
    prose_lines: set[int] = set()
    tokens = tokenize.generate_tokens(io.StringIO(text).readline)
    for token in tokens:
        if token.type in PROSE_TOKEN_TYPES:
            prose_lines.update(range(token.start[0], token.end[0] + 1))

    return prose_lines
