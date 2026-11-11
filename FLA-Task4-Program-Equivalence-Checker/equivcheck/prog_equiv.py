"""
Equivalence checking for ordinary Python functions.

For general programs equivalence is undecidable (EQ_TM is neither
recognisable nor co-recognisable), so this checker answers one of

    EQUIVALENT      - proved, but only for the stated finite input domain
    NOT EQUIVALENT  - with a concrete witness input (this is always a proof)
    UNKNOWN         - no difference found, but no proof either

Strategy
  1. Static look at both functions: do they contain loops or recursion?
  2. If the input domain is finite, run both on EVERY input with a step
     budget. If every run finishes and all outputs agree, the functions are
     equivalent on that domain (an exact answer, because the domain is finite).
  3. If the domain is unbounded, run a differential test on many inputs
     (boundary values + random values). A difference is a proof of
     non-equivalence. No difference is only evidence -> UNKNOWN.
A run that exceeds the step budget is recorded as TIMEOUT. Two TIMEOUTs are
NOT treated as equal, because we cannot tell "loops forever" from "slow".
"""
import ast
import inspect
import itertools
import random
import sys
import textwrap

EQUIVALENT, NOT_EQUIVALENT, UNKNOWN = "EQUIVALENT", "NOT EQUIVALENT", "UNKNOWN"


class _OutOfSteps(Exception):
    pass


class Timeout:
    def __repr__(self):
        return "TIMEOUT"

    def __eq__(self, other):
        return False      # never equal to anything, not even another Timeout

    __hash__ = object.__hash__


def run_bounded(fn, args, budget):
    """Call fn(*args) but stop after `budget` executed lines.
    Returns (value, lines_used). value is Timeout() if the budget ran out, or
    ('error', ExceptionName) if the function raised."""
    count = [0]

    def tracer(frame, event, arg):
        if event == "line":
            count[0] += 1
            if count[0] > budget:
                raise _OutOfSteps()
        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        value = fn(*args)
    except _OutOfSteps:
        value = Timeout()
    except Exception as exc:  # a crash is an observable behaviour too
        value = ("error", type(exc).__name__)
    finally:
        sys.settrace(old)
    return value, count[0]


def structure(fn):
    """Which control features does fn use? (loops, recursion)"""
    try:
        src = textwrap.dedent(inspect.getsource(fn))
    except (OSError, TypeError):
        return {"loops": True, "recursion": True, "source": None}
    tree = ast.parse(src)
    loops = any(isinstance(n, (ast.While, ast.For)) for n in ast.walk(tree))
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    return {"loops": loops, "recursion": fn.__name__ in calls, "source": src}


def _boundary_values(lo, hi):
    vals = {lo, hi, 0, 1, -1, 2, -2, lo + 1, hi - 1}
    return sorted(v for v in vals if lo <= v <= hi)


def check(f, g, domain, budget=20_000, samples=3_000, seed=7):
    """Compare f and g.

    domain: list of per-argument ranges, e.g. [range(0, 101)] for one int
            argument, or [range(-8, 8), range(-8, 8)] for two.
            Use ('int', lo, hi) instead of a range to mean 'unbounded in
            practice': the checker then samples instead of enumerating.
    """
    sf, sg = structure(f), structure(g)
    finite = all(isinstance(d, range) for d in domain)
    rnd = random.Random(seed)
    if finite:
        inputs = itertools.product(*domain)
        total = 1
        for d in domain:
            total *= len(d)
        mode = f"exhaustive over all {total} inputs"
    else:
        bounds = [(d[1], d[2]) if isinstance(d, tuple) else (d.start, d.stop - 1) for d in domain]
        edge = list(itertools.product(*[_boundary_values(lo, hi) for lo, hi in bounds]))
        rand = [tuple(rnd.randint(lo, hi) for lo, hi in bounds) for _ in range(samples)]
        inputs = edge + rand
        total = len(inputs)
        mode = f"differential test on {total} inputs (boundary + random)"
    tested, timeouts, max_steps = 0, 0, 0
    for args in inputs:
        a, sa = run_bounded(f, args, budget)
        b, sb = run_bounded(g, args, budget)
        tested += 1
        max_steps = max(max_steps, sa, sb)
        if isinstance(a, Timeout) or isinstance(b, Timeout):
            timeouts += 1
            continue
        if a != b:
            return {"verdict": NOT_EQUIVALENT, "witness": args, "outputs": (a, b), "mode": mode,
                    "tested": tested, "timeouts": timeouts, "structure": (sf, sg),
                    "reason": f"on input {args} the first returns {a!r} and the second {b!r}"}
    if finite and timeouts == 0:
        return {"verdict": EQUIVALENT, "witness": None, "outputs": None, "mode": mode, "tested": tested,
                "timeouts": 0, "structure": (sf, sg),
                "reason": "every input in the finite domain was run to completion and the outputs agree"}
    if timeouts:
        why = (f"{timeouts} input(s) ran past the {budget}-line budget; a timeout could be "
               "an infinite loop or just slow, so nothing is concluded for them")
    else:
        why = "no difference found, but the domain is unbounded, so this is evidence, not proof"
    return {"verdict": UNKNOWN, "witness": None, "outputs": None, "mode": mode, "tested": tested,
            "timeouts": timeouts, "structure": (sf, sg), "reason": why}
