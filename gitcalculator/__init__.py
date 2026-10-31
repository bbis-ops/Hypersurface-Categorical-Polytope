"""gitcalculator: the repository's central result as a calculator.

Every answer is computed by the repository's own backend, certified against
the theorem's hypotheses in exact arithmetic, attacked by the repository's
counter-arguments and an independent certified measurement, and pinned to the
git objects that produced it. See docs/GITCALCULATOR.md.
"""

__all__ = ["calculate"]


def calculate(request, **options):
    """Compute one receipt; see :func:`gitcalculator.receipt.calculate`."""
    from .receipt import calculate as _calculate

    return _calculate(request, **options)
