import itertools
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from equivcheck import reduction  # noqa: E402
from equivcheck.benchmark import PROGRAM_PAIRS, REGEX_PAIRS  # noqa: E402
from equivcheck.prog_equiv import EQUIVALENT, NOT_EQUIVALENT, UNKNOWN, Timeout, check, run_bounded  # noqa: E402
from equivcheck.regex_equiv import RegexSyntaxError, compare, matcher  # noqa: E402


# ------------------------------------------------------------- regex
@pytest.mark.parametrize("name,r1,r2,truth,story", REGEX_PAIRS, ids=[p[0] for p in REGEX_PAIRS])
def test_regex_benchmark(name, r1, r2, truth, story):
    assert compare(r1, r2)["equivalent"] == truth


@pytest.mark.parametrize("name,r1,r2,truth,story", [p for p in REGEX_PAIRS if not p[3]], ids=lambda x: str(x)[:20])
def test_witness_really_separates(name, r1, r2, truth, story):
    w = compare(r1, r2)["witness"]
    assert matcher(r1)(w) != matcher(r2)(w)


def test_witness_is_shortest():
    # (ab)* vs a*b*: the empty string is in both, 'a' is in a*b* only
    assert compare("(ab)*", "a*b*")["witness"] == "a"


REGEXES = ["(a|b)*", "a(ba)*", "x?y", "[0-9]+(-[0-9]+)*", "(ab)*", "a*b*", "(0|1)*1(0|1)", "a+b?", "(a|bc)*d"]


@pytest.mark.parametrize("rx", REGEXES)
def test_matcher_agrees_with_python_re(rx):
    """Our Thompson NFA must accept exactly what Python's re accepts."""
    alphabet = sorted(set(re.sub(r"[^a-z0-9-]", "", rx)) | {"a", "z"})[:5]
    m = matcher(rx)
    py = re.compile(rx)
    for n in range(0, 6):
        for t in itertools.product(alphabet, repeat=n):
            s = "".join(t)
            assert m(s) == bool(py.fullmatch(s)), (rx, s)


def test_regex_equivalence_agrees_with_brute_force():
    """For random pairs from REGEXES, 'equivalent' must agree with brute force up to length 7."""
    alphabet = "ab01xyd-c"
    for r1, r2 in itertools.combinations(REGEXES, 2):
        res = compare(r1, r2)
        m1, m2 = matcher(r1), matcher(r2)
        brute_diff = None
        for n in range(0, 5):
            for t in itertools.product(alphabet, repeat=n):
                s = "".join(t)
                if m1(s) != m2(s):
                    brute_diff = s
                    break
            if brute_diff is not None:
                break
        if brute_diff is not None:
            assert not res["equivalent"]
            assert len(res["witness"]) <= len(brute_diff)
        if res["equivalent"]:
            assert brute_diff is None


def test_bad_regex():
    with pytest.raises(RegexSyntaxError):
        compare("(ab", "a")


# ----------------------------------------------------------- programs
@pytest.mark.parametrize("name,f,g,dom,truth,story", PROGRAM_PAIRS, ids=[p[0] for p in PROGRAM_PAIRS])
def test_program_benchmark_never_wrong(name, f, g, dom, truth, story):
    v = check(f, g, dom)["verdict"]
    if v == EQUIVALENT:
        assert truth is True
    elif v == NOT_EQUIVALENT:
        assert truth is False


def test_program_benchmark_decides_most():
    decided = sum(check(f, g, d)["verdict"] != UNKNOWN for _, f, g, d, _, _ in PROGRAM_PAIRS)
    assert decided >= 8


def test_witness_is_real():
    for _, f, g, d, truth, _ in PROGRAM_PAIRS:
        r = check(f, g, d)
        if r["verdict"] == NOT_EQUIVALENT:
            assert f(*r["witness"]) != g(*r["witness"])


def test_budget_stops_infinite_loop():
    def forever(x):
        while True:
            x += 1
    value, used = run_bounded(forever, (0,), 500)
    assert isinstance(value, Timeout) and used > 500


def test_timeouts_are_never_equal():
    assert Timeout() != Timeout()


# ----------------------------------------------------------- reduction
def test_every_candidate_checker_fails_somewhere():
    for row in reduction.demonstrate():
        assert row["wrong_on"], row["checker"]
