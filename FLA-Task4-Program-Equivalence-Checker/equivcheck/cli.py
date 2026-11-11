"""
EquivCheck command line.

  python -m equivcheck.cli all                    everything below
  python -m equivcheck.cli theory                 the reduction from HALT, run against real checkers
  python -m equivcheck.cli regex                  regex benchmark (decidable case)
  python -m equivcheck.cli regex "(ab)*" "a*b*"   compare your own two regexes
  python -m equivcheck.cli programs               program benchmark (restricted cases)
"""
import sys

from . import reduction
from .benchmark import PROGRAM_PAIRS, REGEX_PAIRS
from .prog_equiv import EQUIVALENT, NOT_EQUIVALENT, check
from .regex_equiv import compare

TTY = sys.stdout.isatty() or "--color" in sys.argv
GRN, RED, YEL, BLD, DIM, RST = ("\033[32m", "\033[31m", "\033[33m", "\033[1m", "\033[2m", "\033[0m") if TTY else ("",) * 6


def paint(v):
    return {EQUIVALENT: GRN, NOT_EQUIVALENT: RED}.get(v, YEL) + v + RST


def title(t):
    print(f"\n{BLD}{t}{RST}\n{'-' * len(t)}")


def theory():
    title("1. Equivalence is undecidable: reduction from the halting problem")
    print("   For a program P build  Q_P(x) = { run P; return 0 }  and  Z(x) = 0.")
    print("   Q_P and Z are equivalent  <=>  P halts.  So an exact equivalence checker")
    print("   would decide HALT. Three real checkers, three programs P:\n")
    for row in reduction.demonstrate():
        print(f"   {BLD}{row['checker']}{RST}: {row['doc']}")
        for p, got, truth in row["answers"]:
            ok = got == truth
            mark = f"{GRN}right{RST}" if ok else f"{RED}WRONG{RST}"
            print(f"      P = {p:<20} says {got:<15} truth {truth:<15} {mark}")
    print(f"\n   {DIM}Every checker is wrong on some P. Any checker you design will be too.{RST}")


def regex_bench():
    title("2. Regular expressions: equivalence is decidable (product of DFAs)")
    print(f"   {'pair':<18}{'regex 1':<30}{'regex 2':<28}{'verdict':<16}{'shortest witness'}")
    right = 0
    for name, r1, r2, truth, _story in REGEX_PAIRS:
        r = compare(r1, r2)
        v = EQUIVALENT if r["equivalent"] else NOT_EQUIVALENT
        right += r["equivalent"] == truth
        w = "" if r["witness"] is None else (repr(r["witness"]) + (" (only 1st)" if r["in_first"] else " (only 2nd)"))
        print(f"   {name:<18}{r1:<30}{r2:<28}{paint(v):<{16 + len(GRN + RST)}}{w}")
    print(f"\n   {right}/{len(REGEX_PAIRS)} answers match the hand-checked truth. Every answer is exact.")


def regex_pair(r1, r2):
    r = compare(r1, r2)
    title(f"Comparing  {r1}  and  {r2}")
    print(f"   DFA states (subset construction): {r['dfa_sizes'][0]} and {r['dfa_sizes'][1]}")
    print(f"   product states explored: {r['explored']}")
    if r["equivalent"]:
        print(f"   verdict: {paint(EQUIVALENT)} (no reachable pair of states disagrees)")
    else:
        side = "first" if r["in_first"] else "second"
        print(f"   verdict: {paint(NOT_EQUIVALENT)}; shortest witness {r['witness']!r} is accepted only by the {side}")


def programs():
    title("3. Programs: restricted cases (finite domain, or a concrete witness)")
    print(f"   {'pair':<22}{'truth':<10}{'domain / method':<46}{'verdict':<16}{'witness / note'}")
    stats = {"right": 0, "unknown": 0, "wrong": 0}
    for name, f, g, dom, truth, _story in PROGRAM_PAIRS:
        r = check(f, g, dom)
        v = r["verdict"]
        t = {True: "equiv", False: "differ", None: "open"}[truth]
        if v not in (EQUIVALENT, NOT_EQUIVALENT):
            stats["unknown"] += 1
        elif (v == EQUIVALENT) == truth:
            stats["right"] += 1
        else:
            stats["wrong"] += 1
        note = str(r["witness"]) if r["witness"] else (f"{r['timeouts']} timeouts" if r["timeouts"] else "")
        print(f"   {name:<22}{t:<10}{r['mode'][:44]:<46}{paint(v):<{16 + len(GRN + RST)}}{note}")
    print(f"\n   {stats['right']} decided correctly, {stats['unknown']} UNKNOWN, {stats['wrong']} wrong.")
    print(f"   {DIM}EQUIVALENT is only claimed for the finite domain that was checked.{RST}")


def main(argv):
    args = [a for a in argv if a != "--color"] or ["all"]
    if args[0] == "theory":
        theory()
    elif args[0] == "regex" and len(args) == 3:
        regex_pair(args[1], args[2])
    elif args[0] == "regex":
        regex_bench()
    elif args[0] == "programs":
        programs()
    elif args[0] == "all":
        theory()
        regex_bench()
        programs()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
