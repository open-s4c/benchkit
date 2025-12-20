# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchmark protocol validation utilities.

This module provides runtime validation for benchmark implementations to ensure
they comply with the benchkit protocol:

- run() method is required
- fetch/build/collect methods are optional
- All methods must accept a 'ctx' parameter (keyword-compatible)
- Structural typing (no inheritance required)

The validator provides clear error messages to help developers identify and fix
protocol violations before execution.

Design philosophy:
- Fail fast with clear errors rather than mysterious runtime failures
- Support both strict (all warnings are errors) and lenient modes
- Allow helper methods (don't require protocol-only methods)
"""

import inspect
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ValidationIssue:
    """
    A single validation issue (error or warning).

    Attributes:
        level: Severity level - "error" or "warning".
        message: Human-readable description of the issue.
    """

    level: str  # "error" or "warning"
    message: str


@dataclass(frozen=True)
class ValidationReport:
    """
    Report of all validation issues found in a benchmark.

    Attributes:
        errors: Tuple of critical issues that prevent benchmark execution.
        warnings: Tuple of non-critical issues that may indicate problems.
    """

    errors: tuple[ValidationIssue, ...]
    warnings: tuple[ValidationIssue, ...]

    @property
    def ok(self) -> bool:
        """
        Check if validation passed (no errors).

        Returns:
            True if there are no errors, False otherwise.
            Note: warnings don't affect this check.
        """
        return len(self.errors) == 0

    def raise_if_errors(self) -> None:
        """
        Raise TypeError if validation found any errors.

        Raises:
            TypeError: If errors were found, with a formatted message listing all errors.
        """
        if not self.ok:
            msgs = "\n".join(f"- {iss.message}" for iss in self.errors)
            raise TypeError(f"Invalid benchmark implementation:\n{msgs}")


def _iter_callable_names(obj: Any) -> set[str]:
    # Defensive helper: dir() plus getattr() may raise, so we isolate it.
    names: set[str] = set()
    for n in dir(obj):
        if n.startswith("_"):
            continue
        try:
            v = getattr(obj, n)
        except Exception:
            continue
        if callable(v):
            names.add(n)
    return names


def _signature_of(fn: Callable[..., Any]) -> inspect.Signature | None:
    try:
        return inspect.signature(fn)
    except (TypeError, ValueError):
        # Some callables (C-extensions, builtins) may not have a signature.
        return None


def _param_allows_kwarg(p: inspect.Parameter) -> bool:
    # ctx.call passes ctx=..., so ctx must not be positional-only.
    return p.kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    )


def _validate_step_callable(
    bench: Any,
    step_name: str,
    *,
    required: bool,
) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    if not hasattr(bench, step_name):
        if required:
            errors.append(
                ValidationIssue(
                    "error",
                    f"Missing required step '{step_name}()'. A benchmark must define run().",
                )
            )
        return errors, warnings

    fn = getattr(bench, step_name)
    if fn is None or not callable(fn):
        errors.append(
            ValidationIssue(
                "error",
                f"Attribute '{step_name}' exists but is not callable.",
            )
        )
        return errors, warnings

    sig = _signature_of(fn)
    if sig is None:
        warnings.append(
            ValidationIssue(
                "warning",
                f"Could not introspect signature of '{step_name}()'. "
                "This may break ctx.call filtering and ctx=... passing.",
            )
        )
        return errors, warnings

    params = sig.parameters

    # Enforce 'ctx' keyword compatibility (because ctx.call uses fn(ctx=self, **args)).
    if "ctx" not in params:
        errors.append(
            ValidationIssue(
                "error",
                f"Step '{step_name}()' must accept a 'ctx' parameter "
                "(e.g., def {step_name}(self, ctx: <StepContext>, ...): ...).",
            )
        )
        return errors, warnings

    ctx_param = params["ctx"]
    if not _param_allows_kwarg(ctx_param):
        errors.append(
            ValidationIssue(
                "error",
                f"In step '{step_name}()', parameter 'ctx' is positional-only. "
                "ctx.call passes ctx=..., so define it as positional-or-keyword or keyword-only.",
            )
        )

    # Optional: discourage ambiguous signatures that can make ctx.call awkward.
    # Example: def run(self, *args, **kwargs) -> ... (still works, but we cannot filter args).
    has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    if has_var_kw:
        warnings.append(
            ValidationIssue(
                "warning",
                f"Step '{step_name}()' accepts **kwargs. This is allowed, but it disables "
                "strict argument filtering and can hide typos in variable names.",
            )
        )

    return errors, warnings


def validate_benchmark(
    bench: Any,
    *,
    strict: bool = False,
    allow_extra_public_callables: bool = True,
) -> ValidationReport:
    """
    Validate that 'bench' implements the benchkit benchmark protocol shape.

    Args:
        bench: The benchmark object instance to validate.
        strict: If True, warnings are treated as errors.
        allow_extra_public_callables: If False, warn on extra public callables
            beyond the known protocol methods. Keep True by default to not
            penalize helper methods.

    Returns:
        ValidationReport with errors and warnings.

    Raises:
        TypeError: if strict=True and any issue exists, or if required errors exist.
    """
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    # Step presence rules:
    # - run is required
    # - fetch/build/collect are optional
    required_steps = ("run",)
    optional_steps = ("fetch", "build", "collect")

    for s in required_steps:
        e, w = _validate_step_callable(bench, s, required=True)
        errors.extend(e)
        warnings.extend(w)

    for s in optional_steps:
        e, w = _validate_step_callable(bench, s, required=False)
        errors.extend(e)
        warnings.extend(w)

    if not allow_extra_public_callables:
        known = set(required_steps) | set(optional_steps)
        extra = _iter_callable_names(bench) - known
        if extra:
            warnings.append(
                ValidationIssue(
                    "warning",
                    "Benchmark defines extra public callables not part of the protocol: "
                    + ", ".join(sorted(extra)),
                )
            )

    if strict and (errors or warnings):
        # Promote warnings to errors for strict mode.
        promoted = [ValidationIssue("error", w.message) for w in warnings]
        report = ValidationReport(errors=tuple(errors + promoted), warnings=tuple())
        report.raise_if_errors()
        return report

    report = ValidationReport(errors=tuple(errors), warnings=tuple(warnings))
    report.raise_if_errors()
    return report
