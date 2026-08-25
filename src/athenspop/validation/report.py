# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module collects validation diagnostics at dataframe boundaries."""

import dataclasses
import typing

#: This type represents the severity of one structured validation issue.
type Severity = typing.Literal["error", "warning"]


@dataclasses.dataclass(frozen=True, slots=True)
class ValidationIssue:
    """This class provides one diagnostic with enough context to fix the input.

    Attributes:
        severity: This value is `error` for hard failures or `warning` for
            methodological and data-quality concerns.
        code: This value is the stable machine-readable diagnostic code.
        table: This value identifies the input table associated with the diagnostic.
        message:
            The message explains the detected condition in human-readable prose.
        row_identifier: This optional value is a row label such as `trips[3]` when
            the issue is row-specific.
        column: This optional value identifies a column or comma-separated column
            group associated with the issue.
        bad_value: This optional value is a string representation of the problematic
            value.
    """

    severity: Severity
    code: str
    table: str
    message: str
    row_identifier: str | None = None
    column: str | None = None
    bad_value: str | None = None


class ValidationError(ValueError):
    """This exception indicates that hard validation errors exist.

    Attributes:
        report: This value is the complete validation report that triggered the
            exception.
    """

    def __init__(self, report: "ValidationReport") -> None:
        """Create an exception carrying the complete validation report.

        Args:
            report: This validation report contains at least one hard error.
        """
        super().__init__(report.summary)
        self.report = report


@dataclasses.dataclass(frozen=True, slots=True)
class ValidationReport:
    """This class groups diagnostics with row and chain suppression state.

    Attributes:
        errors: These hard validation issues prevent trusted model construction.
        warnings: These methodological or data-quality issues do not prevent model
            construction.
        invalid_rows: These row identifiers failed row-level validation.
        invalid_chains: These diary chain identifiers had their downstream chain
            checks suppressed.
    """

    errors: tuple[ValidationIssue, ...] = ()
    warnings: tuple[ValidationIssue, ...] = ()
    invalid_rows: tuple[str, ...] = ()
    invalid_chains: tuple[str, ...] = ()

    @property
    def has_errors(self) -> bool:
        """Return whether the report contains hard errors.

        Returns:
            The property returns `True` when at least one hard validation issue was
            collected.
        """
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Return whether the report contains warnings.

        Returns:
            The property returns `True` when at least one warning was collected.
        """
        return len(self.warnings) > 0

    @property
    def summary(self) -> str:
        """Return a compact human-readable diagnostic summary.

        Returns:
            The property returns counts for errors, warnings, invalid rows, and
            invalid chains.
        """
        error_label = "error" if len(self.errors) == 1 else "errors"
        warning_label = "warning" if len(self.warnings) == 1 else "warnings"
        row_label = "invalid row" if len(self.invalid_rows) == 1 else "invalid rows"
        chain_label = (
            "invalid chain" if len(self.invalid_chains) == 1 else "invalid chains"
        )

        return (
            f"The report contains {len(self.errors)} {error_label}, "
            f"{len(self.warnings)} {warning_label}, "
            f"{len(self.invalid_rows)} {row_label}, and "
            f"{len(self.invalid_chains)} {chain_label}."
        )

    def raise_if_invalid(self) -> None:
        """Raise `ValidationError` if any hard errors were collected.

        Raises:
            ValidationError: The method raises this error if `has_errors` is true.
        """
        if self.has_errors:
            raise ValidationError(self)


@dataclasses.dataclass(slots=True)
class ValidationReportBuilder:
    """This mutable helper allows public reports to remain immutable.

    Attributes:
        errors: This mutable list contains the hard validation issues collected so
            far.
        warnings: This mutable list contains the warning issues collected so far.
        invalid_rows: These row identifiers have hard errors.
        blocked_rows: These row identifiers should not receive noisy downstream
            diagnostics.
        invalid_chains: These diary chain identifiers should have their downstream
            checks suppressed.
    """

    errors: list[ValidationIssue] = dataclasses.field(default_factory=list)
    warnings: list[ValidationIssue] = dataclasses.field(default_factory=list)
    invalid_rows: set[str] = dataclasses.field(default_factory=set)
    blocked_rows: set[str] = dataclasses.field(default_factory=set)
    invalid_chains: set[str] = dataclasses.field(default_factory=set)

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
            code: This value is the stable machine-readable diagnostic code.
            table: This value identifies the input table associated with the error.
            message: This text explains the error in human-readable prose.
            row_identifier: This optional value identifies the row associated with
                the error.
            column: This optional value identifies the column or column group
                associated with the error.
            bad_value: This optional value is a string representation of the
                problematic value.
            suppress_row: This value controls whether later row-level validators skip
                the row after this error.
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
            code: This value is the stable machine-readable diagnostic code.
            table: This value identifies the input table associated with the warning.
            message: This text explains the warning in human-readable prose.
            row_identifier: This optional value identifies the row associated with
                the warning.
            column: This optional value identifies the column or column group
                associated with the warning.
            bad_value: This optional value is a string representation of the
                concerning value.
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

    def build(self) -> ValidationReport:
        """Build an immutable public report.

        Returns:
            The method returns a validation report containing sorted invalid row and
            chain identifiers.
        """
        return ValidationReport(
            errors=tuple(self.errors),
            warnings=tuple(self.warnings),
            invalid_rows=tuple(sorted(self.invalid_rows)),
            invalid_chains=tuple(sorted(self.invalid_chains)),
        )
