"""
Benchmark of equivalence questions whose true answer we worked out by hand.

Each entry is a realistic situation: a developer refactors a function or a
validation regex and wants to know whether the behaviour changed.
"""

# =========================================================== regex pairs
REGEX_PAIRS = [
    # (name, regex 1, regex 2, truly equivalent?, story)
    ("star_of_union", "(a|b)*", "(a*b*)*", True, "two ways to write 'any string of a and b'"),
    ("shifted_loop", "a(ba)*", "(ab)*a", True, "same alternating pattern, loop written from the other end"),
    ("optional_prefix", "x?y", "y|xy", True, "optional character vs explicit alternatives"),
    ("double_star", "a**", "a*", True, "redundant star"),
    ("phone_digits", "[0-9]+(-[0-9]+)*", "[0-9]([0-9]|-[0-9])*", True,
     "digit groups separated by single hyphens, refactored"),
    ("username_rule", "[a-z][a-z0-9_]*", "[a-z]([a-z]|[0-9]|_)*", True, "character class split into alternatives"),
    ("pairs_vs_blocks", "(ab)*", "a*b*", False, "looks similar, accepts different strings"),
    ("second_last_one", "(0|1)*1(0|1)", "(0|1)*1", False, "'second-to-last bit is 1' vs 'last bit is 1'"),
    ("pin_refactor_bug", "[0-9][0-9][0-9][0-9]", "[0-9][0-9][0-9][0-9]?", False,
     "a refactor that accidentally makes the 4th digit optional"),
    ("email_tld_bug", "[a-z]+@[a-z]+\\.[a-z][a-z]+", "[a-z]+@[a-z]+\\.[a-z]+", False,
     "refactor drops the 'TLD has at least two letters' rule"),
]


# ======================================================== program pairs
def sum_loop(n):
    total = 0
    i = 1
    while i <= n:
        total += i
        i += 1
    return total


def sum_formula(n):
    return n * (n + 1) // 2


def abs_branch(x):
    if x < 0:
        return -x
    return x


def abs_max(x):
    return max(x, -x)


def max3_ref(a, b, c):
    return max(a, b, c)


def max3_buggy(a, b, c):
    if a > b and a > c:
        return a
    if b > a and b > c:
        return b
    return c


def swap_temp(a, b):
    t = a
    a = b
    b = t
    return a, b


def swap_xor(a, b):
    a = a ^ b
    b = a ^ b
    a = a ^ b
    return a, b


def leap_ref(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def leap_buggy(y):
    return y % 4 == 0 and y % 100 != 0


def count_up_to_n(n):
    s = 0
    for i in range(n):
        s += i
    return s


def count_up_to_n_refactor(n):
    s = 0
    for i in range(1, n + 1):      # off-by-one: now includes n
        s += i
    return s


def power_loop(b, e):
    r = 1
    for _ in range(e):
        r *= b
    return r


def power_fast(b, e):
    r = 1
    while e > 0:
        if e % 2 == 1:
            r *= b
        b *= b
        e //= 2
    return r


def collatz_reaches_one(n):
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
    return True


def always_true(n):
    return True


def slow_identity(n):
    i = 0
    while i < 50_000:          # finishes, but after a very long time
        i += 1
    return n


def identity(n):
    return n


PROGRAM_PAIRS = [
    # (name, f, g, domain, truth, story)
    ("sum_loop_vs_formula", sum_loop, sum_formula, [range(0, 301)], True,
     "replacing a loop by Gauss's formula"),
    ("abs_two_ways", abs_branch, abs_max, [range(-500, 501)], True, "branch vs max"),
    ("swap_xor_trick", swap_temp, swap_xor, [range(0, 64), range(0, 64)], True, "XOR swap optimisation"),
    ("fast_power", power_loop, power_fast, [range(-6, 7), range(0, 12)], True, "square-and-multiply"),
    ("max3_refactor", max3_ref, max3_buggy, [range(-3, 4)] * 3, False, "hand-written max breaks on ties"),
    ("leap_year_bug", leap_ref, leap_buggy, [range(1900, 2101)], False, "forgot the 400-year rule"),
    ("off_by_one", count_up_to_n, count_up_to_n_refactor, [range(0, 50)], False, "range(n) vs range(1, n+1)"),
    ("collatz_small", collatz_reaches_one, always_true, [range(1, 2000)], True,
     "true for every n we can check; nobody can prove it for all n"),
    ("collatz_unbounded", collatz_reaches_one, always_true, [("int", 1, 10 ** 12)], None,
     "same pair, unbounded domain: an open problem in mathematics"),
    ("slow_vs_fast", slow_identity, identity, [range(0, 5)], True,
     "equivalent, but one side is slower than the step budget"),
]
