"""
Why no tool can decide program equivalence: the reduction from HALT.

Given any program P (no input) build two one-argument programs

    Q_P(x):  run P;  return 0
    Z(x):    return 0

Q_P and Z compute the same function  <=>  P halts.
So a decider for equivalence would give a decider for the halting problem,
which Turing proved cannot exist. The same construction shows EQ_TM is not
recognisable (it would make the complement of HALT recognisable).

Here we take several *real* candidate equivalence checkers and show each one
answering at least one such pair wrongly.
"""
import ast
import inspect
import textwrap

from .prog_equiv import EQUIVALENT, NOT_EQUIVALENT, Timeout, run_bounded


# --- programs P that take no input -----------------------------------------
def p_halts_now():
    return


def p_loops_forever():
    while True:
        pass


def make_p_halts_after(k):
    def p():
        i = 0
        while i < k:
            i += 1
    p.__name__ = f"p_halts_after_{k}"
    return p


def make_q(P):
    def q(x):
        P()
        return 0
    q.__name__ = f"Q_{P.__name__}"
    return q


def z(x):
    return 0


# --- candidate deciders for "are f and g equivalent?" -----------------------
def checker_syntax(f, g):
    """compares the source code of the two functions"""
    def norm(fn):
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        body = tree.body[0].body
        return ast.dump(ast.Module(body=body, type_ignores=[]))
    return EQUIVALENT if norm(f) == norm(g) else NOT_EQUIVALENT


def make_checker_testing(budget):
    def checker_testing(f, g):
        """runs both on a few inputs; a timeout counts as 'different'"""
        for x in (0, 1, 2, -1, 10):
            a, _ = run_bounded(f, (x,), budget)
            b, _ = run_bounded(g, (x,), budget)
            if isinstance(a, Timeout) or isinstance(b, Timeout) or a != b:
                return NOT_EQUIVALENT
        return EQUIVALENT
    checker_testing.__doc__ = f"runs both on 5 inputs with a {budget}-line budget; timeout counts as a difference"
    return checker_testing


def make_checker_lenient(budget):
    def checker_lenient(f, g):
        """runs both on a few inputs; ignores inputs that time out"""
        for x in (0, 1, 2, -1, 10):
            a, _ = run_bounded(f, (x,), budget)
            b, _ = run_bounded(g, (x,), budget)
            if isinstance(a, Timeout) or isinstance(b, Timeout):
                continue
            if a != b:
                return NOT_EQUIVALENT
        return EQUIVALENT
    checker_lenient.__doc__ = f"same, but inputs that pass the {budget}-line budget are skipped"
    return checker_lenient


BUDGET = 2_000
CANDIDATES = [checker_syntax, make_checker_testing(BUDGET), make_checker_lenient(BUDGET)]
PROGRAMS = [p_halts_now, make_p_halts_after(5_000), p_loops_forever]
HALTS = {"p_halts_now": True, "p_halts_after_5000": True, "p_loops_forever": False}


def demonstrate():
    """For every candidate and every P, compare checker(Q_P, Z) with the truth."""
    rows = []
    for checker in CANDIDATES:
        wrong_on = []
        answers = []
        for P in PROGRAMS:
            truth = EQUIVALENT if HALTS[P.__name__] else NOT_EQUIVALENT
            got = checker(make_q(P), z)
            answers.append((P.__name__, got, truth))
            if got != truth:
                wrong_on.append(P.__name__)
        rows.append({"checker": checker.__name__, "doc": (checker.__doc__ or "").strip(),
                     "answers": answers, "wrong_on": wrong_on})
    return rows
