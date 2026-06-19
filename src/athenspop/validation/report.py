"""Validation diagnostics collected at dataframe/file boundaries."""

from dataclasses import dataclass, field
from typing import Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One validation diagnostic with enough context for a user to fix the input.

    Attributes:
        severity: Diagnostic severity, either `error` for hard failures or `warning` for methodological/data-quality concerns.
        code: Stable machine-readable diagnostic code.
        table: Input table associated with the diagnostic.
        message: Human-readable explanation written for non-expert users.
        row_identifier: Optional row label such as `trips[3]` when the issue is row-specific.
        column: Optional column or comma-separated column group associated with the issue.
        bad_value: Optional string representation of the problematic value.
    """

    severity: Severity
    code: str
    table: str
    message: str
    row_identifier: str | None = None
    column: str | None = None
    bad_value: str | None = None


class ValidationError(ValueError):
    """Raised by `ValidationReport.raise_if_invalid` when hard validation errors exist.

    Attributes:
        report: Complete validation report that triggered the exception.
    """

    def __init__(self, report: "ValidationReport") -> None:
        """Create an exception carrying the complete validation report.

        Args:
            report: Validation report containing at least one hard error.
        """
        super().__init__(report.summary)
        self.report = report


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Grouped validation diagnostics plus row and chain suppression state.

    Attributes:
        errors: Hard validation issues that prevent trusted model construction.
        warnings: Methodological or data-quality issues that do not prevent model construction.
        invalid_rows: Row identifiers that failed row-level validation.
        invalid_chains: Diary chain identifiers whose downstream chain checks were suppressed.
    """

    errors: tuple[ValidationIssue, ...] = ()
    warnings: tuple[ValidationIssue, ...] = ()
    invalid_rows: tuple[str, ...] = ()
    invalid_chains: tuple[str, ...] = ()

    @property
    def has_errors(self) -> bool:
        """Return whether the report contains hard errors.

        Returns:
            `True` when at least one hard validation issue was collected.
        """
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Return whether the report contains warnings.

        Returns:
            `True` when at least one warning was collected.
        """
        return len(self.warnings) > 0

    @property
    def summary(self) -> str:
        """Return a compact human-readable diagnostic summary.

        Returns:
            Summary string with counts for errors, warnings, invalid rows, and invalid chains.
        """
        return f"{len(self.errors)} error(s), {len(self.warnings)} warning(s), {len(self.invalid_rows)} invalid row(s), {len(self.invalid_chains)} invalid chain(s)"

    def raise_if_invalid(self) -> None:
        """Raise `ValidationError` if any hard errors were collected.

        Raises:
            ValidationError: If `has_errors` is true.
        """
        if self.has_errors:
            raise ValidationError(self)


@dataclass(slots=True)
class ValidationReportBuilder:
    """Mutable helper used internally so public reports stay immutable.

    Attributes:
        errors: Mutable list of hard validation issues collected so far.
        warnings: Mutable list of warning issues collected so far.
        invalid_rows: Row identifiers that have hard errors.
        blocked_rows: Row identifiers that should not receive noisy downstream diagnostics.
        invalid_chains: Diary chain identifiers whose downstream checks should be suppressed.
    """

    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    invalid_rows: set[str] = field(default_factory=set)
    blocked_rows: set[str] = field(default_factory=set)
    invalid_chains: set[str] = field(default_factory=set)

    def add_error(
        self,
        *,
        code: str,
        table: str,
        message: str,
        row_identifier: str | None = None,
        column: str | None = None,
        bad_value: str | None = None,
        suppress_row: bool = True,
    ) -> None:
        """Add a hard validation error and optionally block downstream row diagnostics.

        Args:
            code: Stable machine-readable diagnostic code.
            table: Input table associated with the error.
            message: Human-readable explanation.
            row_identifier: Optional row label associated with the error.
            column: Optional column or column group associated with the error.
            bad_value: Optional string representation of the problematic value.
            suppress_row: Whether later row-level validators should skip the row after this error.
        """
        self.errors.append(
            ValidationIssue(
                severity="error",
                code=code,
                table=table,
                message=message,
                row_identifier=row_identifier,
                column=column,
                bad_value=bad_value,
            )
        )
        if row_identifier is not None:
            self.invalid_rows.add(row_identifier)
            if suppress_row:
                self.blocked_rows.add(row_identifier)

    def add_warning(
        self,
        *,
        code: str,
        table: str,
        message: str,
        row_identifier: str | None = None,
        column: str | None = None,
        bad_value: str | None = None,
    ) -> None:
        """Add a methodological or data-quality warning.

        Args:
            code: Stable machine-readable diagnostic code.
            table: Input table associated with the warning.
            message: Human-readable explanation.
            row_identifier: Optional row label associated with the warning.
            column: Optional column or column group associated with the warning.
            bad_value: Optional string representation of the concerning value.
        """
        self.warnings.append(
            ValidationIssue(
                severity="warning",
                code=code,
                table=table,
                message=message,
                row_identifier=row_identifier,
                column=column,
                bad_value=bad_value,
            )
        )

    def mark_chain_invalid(self, chain_identifier: str) -> None:
        """Suppress downstream chain checks for a diary chain.

        Args:
            chain_identifier: Human-readable diary chain identifier.
        """
        self.invalid_chains.add(chain_identifier)

    def build(self) -> ValidationReport:
        """Build an immutable public report.

        Returns:
            Validation report containing sorted invalid row and chain identifiers.
        """
        return ValidationReport(
            errors=tuple(self.errors),
            warnings=tuple(self.warnings),
            invalid_rows=tuple(sorted(self.invalid_rows)),
            invalid_chains=tuple(sorted(self.invalid_chains)),
        )
