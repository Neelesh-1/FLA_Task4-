"""
Exact equivalence checking for regular expressions.

This is the *decidable* corner of the equivalence problem: two regular
expressions describe the same language iff the DFAs built from them agree on
every reachable pair of states. We never build the full DFAs up front.
Instead we walk the product of the two subset constructions breadth-first,
which also gives the *shortest* string on which the two expressions disagree.

Supported syntax:  a  .  [a-z0-9_]  ( )  |  *  +  ?  and \\ to escape.
"""
from collections import deque

OTHER = "∅"   # stands for "any character that appears in neither regex"


class RegexSyntaxError(ValueError):
    pass


# --------------------------------------------------------------------- parse
class _Parser:
    """Recursive descent:  alt := cat ('|' cat)* ; cat := rep* ;
    rep := atom ('*' | '+' | '?')* ; atom := char | '.' | '[..]' | '(' alt ')'"""

    def __init__(self, text):
        self.s = text
        self.i = 0

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else None

    def take(self):
        c = self.peek()
        self.i += 1
        return c

    def parse(self):
        node = self.alt()
        if self.peek() is not None:
            raise RegexSyntaxError(f"unexpected '{self.peek()}' at position {self.i}")
        return node

    def alt(self):
        parts = [self.cat()]
        while self.peek() == "|":
            self.take()
            parts.append(self.cat())
        return parts[0] if len(parts) == 1 else ("alt", parts)

    def cat(self):
        parts = []
        while self.peek() is not None and self.peek() not in "|)":
            parts.append(self.rep())
        if not parts:
            return ("eps",)
        return parts[0] if len(parts) == 1 else ("cat", parts)

    def rep(self):
        node = self.atom()
        while self.peek() in ("*", "+", "?"):
            node = ({"*": "star", "+": "plus", "?": "opt"}[self.take()], node)
        return node

    def atom(self):
        c = self.take()
        if c is None:
            raise RegexSyntaxError("unexpected end of expression")
        if c == "(":
            node = self.alt()
            if self.take() != ")":
                raise RegexSyntaxError("missing ')'")
            return node
        if c == "[":
            chars = set()
            while self.peek() not in ("]", None):
                a = self.take()
                if a == "\\":
                    a = self.take()
                if self.peek() == "-" and self.i + 1 < len(self.s) and self.s[self.i + 1] != "]":
                    self.take()
                    b = self.take()
                    chars |= {chr(x) for x in range(ord(a), ord(b) + 1)}
                else:
                    chars.add(a)
            if self.take() != "]":
                raise RegexSyntaxError("missing ']'")
            return ("set", frozenset(chars))
        if c == ".":
            return ("any",)
        if c == "\\":
            return ("set", frozenset(self.take()))
        if c in "*+?":
            raise RegexSyntaxError(f"'{c}' has nothing to repeat")
        return ("set", frozenset(c))


def parse(text):
    return _Parser(text).parse()


def letters(node):
    tag = node[0]
    if tag == "set":
        return set(node[1])
    if tag in ("alt", "cat"):
        return set().union(*(letters(p) for p in node[1]))
    if tag in ("star", "plus", "opt"):
        return letters(node[1])
    return set()


# --------------------------------------------------------- Thompson NFA
class NFA:
    """Thompson construction: one start, one accept, epsilon moves."""

    def __init__(self, tree, alphabet):
        self.eps = {}      # state -> set of states
        self.move = {}     # (state, symbol) -> set of states
        self.n = 0
        self.alphabet = alphabet
        self.start, self.accept = self._build(tree)

    def _new(self):
        self.n += 1
        return self.n - 1

    def _e(self, a, b):
        self.eps.setdefault(a, set()).add(b)

    def _build(self, node):
        tag = node[0]
        if tag == "eps":
            s, f = self._new(), self._new()
            self._e(s, f)
            return s, f
        if tag in ("set", "any"):
            s, f = self._new(), self._new()
            syms = self.alphabet if tag == "any" else node[1]
            for c in syms:
                self.move.setdefault((s, c), set()).add(f)
            return s, f
        if tag == "cat":
            s, f = self._build(node[1][0])
            for part in node[1][1:]:
                s2, f2 = self._build(part)
                self._e(f, s2)
                f = f2
            return s, f
        if tag == "alt":
            s, f = self._new(), self._new()
            for part in node[1]:
                s2, f2 = self._build(part)
                self._e(s, s2)
                self._e(f2, f)
            return s, f
        inner_s, inner_f = self._build(node[1])
        s, f = self._new(), self._new()
        self._e(s, inner_s)
        self._e(inner_f, f)
        if tag in ("star", "opt"):
            self._e(s, f)
        if tag in ("star", "plus"):
            self._e(inner_f, inner_s)
        return s, f

    def closure(self, states):
        stack, seen = list(states), set(states)
        while stack:
            q = stack.pop()
            for r in self.eps.get(q, ()):
                if r not in seen:
                    seen.add(r)
                    stack.append(r)
        return frozenset(seen)

    def step(self, S, c):
        out = set()
        for q in S:
            out |= self.move.get((q, c), set())
        return self.closure(out)

    def initial(self):
        return self.closure({self.start})

    def accepting(self, S):
        return self.accept in S

    def matches(self, text):
        S = self.initial()
        for c in text:
            S = self.step(S, c if c in self.alphabet else OTHER)
        return self.accepting(S)

    def dfa_size(self):
        """Number of reachable DFA states (subset construction), dead state included."""
        start = self.initial()
        seen, todo = {start}, deque([start])
        while todo:
            S = todo.popleft()
            for c in self.alphabet:
                T = self.step(S, c)
                if T not in seen:
                    seen.add(T)
                    todo.append(T)
        return len(seen)


# ----------------------------------------------------------- equivalence
def compare(r1, r2):
    """Decide L(r1) == L(r2).

    Returns dict(equivalent, witness, in_first, explored, dfa_sizes).
    witness is a shortest string accepted by exactly one of the two."""
    t1, t2 = parse(r1), parse(r2)
    alphabet = sorted(letters(t1) | letters(t2)) + [OTHER]
    n1, n2 = NFA(t1, alphabet), NFA(t2, alphabet)
    start = (n1.initial(), n2.initial())
    parent = {start: None}
    todo = deque([start])
    while todo:
        pair = todo.popleft()
        a1, a2 = n1.accepting(pair[0]), n2.accepting(pair[1])
        if a1 != a2:
            word = []
            p = pair
            while parent[p] is not None:
                p, c = parent[p]
                word.append(c)
            return {"equivalent": False, "witness": "".join(reversed(word)), "in_first": a1,
                    "explored": len(parent), "dfa_sizes": (n1.dfa_size(), n2.dfa_size())}
        for c in alphabet:
            nxt = (n1.step(pair[0], c), n2.step(pair[1], c))
            if nxt not in parent:
                parent[nxt] = (pair, c)
                todo.append(nxt)
    return {"equivalent": True, "witness": None, "in_first": None,
            "explored": len(parent), "dfa_sizes": (n1.dfa_size(), n2.dfa_size())}


def matcher(regex):
    t = parse(regex)
    alphabet = sorted(letters(t)) + [OTHER]
    return NFA(t, alphabet).matches
