# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module defines repository contracts for packaging and Python files."""

import ast
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tomllib
from typing import Final

#: This path is the absolute repository root used by release contracts.
PROJECT_ROOT: Final[pathlib.Path] = pathlib.Path(__file__).resolve().parents[1]
#: These paths identify the Python surfaces governed by the style contract.
PYTHON_ROOTS: Final[tuple[pathlib.Path, ...]] = (
    PROJECT_ROOT / "src",
    PROJECT_ROOT / "tests",
    PROJECT_ROOT / "examples",
)
#: These standard-library modules must remain qualified module imports.
MODULE_IMPORT_ONLY_STDLIB_MODULES: Final[frozenset[str]] = frozenset({"math", "random"})
#: These conventional aliases preserve established third-party notation.
ALLOWED_MODULE_ALIASES: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("matplotlib", "mpl"),
        ("matplotlib.pyplot", "plt"),
        ("numpy", "np"),
        ("pandas", "pd"),
    }
)


def test_root_import_does_not_load_visualization_dependencies() -> None:
    """Keep the base import usable without the optional plotting extra."""
    code = (
        "import sys\n"
        "import athenspop\n"
        "prefixes = ('matplotlib', 'athenspop.visualization')\n"
        "loaded = any(name == prefix or name.startswith(prefix + '.') "
        "for name in sys.modules for prefix in prefixes)\n"
        "raise SystemExit(1 if loaded else 0)"
    )

    subprocess.run([sys.executable, "-c", code], check=True)


def test_matplotlib_is_an_optional_visualization_dependency() -> None:
    """Keep plotting out of the package's required dependency set."""
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


def test_sdist_contains_only_documented_release_surfaces(
    tmp_path: pathlib.Path,
) -> None:
    """Ship code, tests, examples, data, and documentation without local state."""
    uv_executable = shutil.which("uv")
    assert uv_executable is not None
    subprocess.run(
        [uv_executable, "build", "--sdist", "--out-dir", str(tmp_path)],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    archive_path = next(tmp_path.glob("*.tar.gz"))
    with tarfile.open(archive_path, "r:gz") as archive:
        archive_names = tuple(archive.getnames())

    allowed_roots = {
        ".gitattributes",
        ".gitignore",
        "CONTRIBUTING.md",
        "LICENSE",
        "PKG-INFO",
        "README.md",
        "data",
        "docs",
        "examples",
        "pyproject.toml",
        "src",
        "tests",
    }
    relative_paths = [
        pathlib.PurePosixPath(*pathlib.PurePosixPath(name).parts[1:])
        for name in archive_names
    ]
    unexpected = [
        str(path)
        for path in relative_paths
        if path.parts and path.parts[0] not in allowed_roots
    ]

    assert unexpected == []
    for required_root in ("src", "tests", "examples", "data", "docs"):
        assert any(
            path.parts and path.parts[0] == required_root for path in relative_paths
        )


def test_source_import_graph_preserves_dependency_boundaries() -> None:
    """Keep visualization dependencies behind the optional plotting boundary."""
    violations: list[str] = []
    for path in sorted((PROJECT_ROOT / "src").rglob("*.py")):
        module_name = _module_name(path)
        imported_modules = _imported_modules(path)
        if not module_name.startswith("athenspop.visualization"):
            violations.extend(
                f"{path.relative_to(PROJECT_ROOT)} imports {imported_module}"
                for imported_module in imported_modules
                if imported_module in {"athenspop.visualization", "matplotlib"}
                or imported_module.startswith(
                    ("athenspop.visualization.", "matplotlib.")
                )
            )

    assert violations == []


def test_python_files_use_exact_license_headers() -> None:
    """Require the approved software notice on every maintained Python file."""
    expected_header = (
        "# Copyright (c) 2022 Theodore Chatziioannou",
        "# Copyright (c) 2026 National Technical University of Athens",
        "# Licensed under the MIT License.",
    )
    violations: list[str] = []
    for path in _python_files():
        text = path.read_text(encoding="utf-8")
        if tuple(text.splitlines()[:3]) != expected_header:
            violations.append(
                f"{path.relative_to(PROJECT_ROOT)} has an invalid header."
            )

    assert violations == []


def test_python_files_use_qualified_module_imports() -> None:
    """Require qualified project and third-party module imports."""
    violations: list[str] = []
    for path in _python_files():
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if (
                        alias.asname is None
                        or (alias.name, alias.asname) in ALLOWED_MODULE_ALIASES
                    ):
                        continue
                    violations.append(
                        f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} aliases "
                        f"{alias.name} as {alias.asname}. Use its module name."
                    )
                continue
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level:
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} uses a "
                    "relative import."
                )
                continue
            if node.module is None:
                continue
            root_module = node.module.partition(".")[0]
            if (
                root_module in sys.stdlib_module_names
                and root_module not in MODULE_IMPORT_ONLY_STDLIB_MODULES
            ):
                continue
            violations.append(
                f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} imports symbols "
                f"from {node.module}. Import the module and qualify each use."
            )

    assert violations == []


def test_defined_python_scopes_and_module_values_have_documentation() -> None:
    """Require documentation on modules, named definitions, and module values."""
    violations: list[str] = []
    for path in _python_files():
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        tree = ast.parse(text)
        if ast.get_docstring(tree) is None:
            violations.append(
                f"{path.relative_to(PROJECT_ROOT)} has no module docstring."
            )
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
                and ast.get_docstring(node) is None
            ):
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} "
                    f"has no documentation for {node.name}."
                )
        for node in tree.body:
            if isinstance(node, ast.Assign | ast.AnnAssign | ast.TypeAlias) and (
                node.lineno < 2 or not lines[node.lineno - 2].lstrip().startswith("#:")
            ):
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} has an "
                    "undocumented module value."
                )

    assert violations == []


def _python_files() -> tuple[pathlib.Path, ...]:
    """Return every maintained Python file in deterministic order."""
    files = [
        path for root in PYTHON_ROOTS if root.exists() for path in root.rglob("*.py")
    ]
    files.append(PROJECT_ROOT / "docs" / "conf.py")
    return tuple(sorted(files))


def _module_name(path: pathlib.Path) -> str:
    """Return the importable module name for a source file."""
    relative = path.relative_to(PROJECT_ROOT / "src").with_suffix("")
    return ".".join(relative.parts)


def _imported_modules(path: pathlib.Path) -> set[str]:
    """Return absolute module names imported by one Python file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
    return imported_modules
