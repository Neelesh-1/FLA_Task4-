"""Regenerate docs/diagrams/*.png and *.svg (needs Graphviz 'dot' on PATH)."""
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

STYLE = ('node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=11 fillcolor="#f3eefb" color="#6b4fa0"];'
         ' edge [fontname="Helvetica" fontsize=10 color="#555555"];')

GRAPHS = {
"problem_mapping": f'''digraph M {{ rankdir=TB; nodesep=0.25; ranksep=0.45; newrank=true; {STYLE}
  subgraph cluster_r {{ label="Real-world question"; fontname="Helvetica-Bold"; color="#bbbbbb";
    r1 [label="Original code / regex"]; r2 [label="Refactored code / regex"]; r3 [label="'Did the behaviour change?'"]; }}
  subgraph cluster_f {{ label="Computational formulation"; fontname="Helvetica-Bold"; color="#bbbbbb";
    f1 [label="Machine M1"]; f2 [label="Machine M2"]; f3 [label="EQ = {{ <M1, M2> : L(M1) = L(M2) }}"]; }}
  subgraph cluster_a {{ label="What theory says"; fontname="Helvetica-Bold"; color="#bbbbbb";
    a1 [label="M1, M2 are DFAs / regexes:\\nDECIDABLE" fillcolor="#e6f4ea" color="#3a7d44"];
    a2 [label="M1, M2 are CFGs:\\nundecidable" fillcolor="#fff4d6" color="#b08900"];
    a3 [label="M1, M2 are Turing machines:\\nnot even recognisable" fillcolor="#fbe9e7" color="#b3412f"]; }}
  subgraph cluster_e {{ label="Engineering answer"; fontname="Helvetica-Bold"; color="#bbbbbb";
    e1 [label="Exact check\\n(product of DFAs)"]; e2 [label="Restrict the domain\\n(finite: test every input)"];
    e3 [label="Search for a witness\\n(differential testing)"]; }}
  v [label="EQUIVALENT / NOT EQUIVALENT (with witness) / UNKNOWN" fillcolor="#fff4d6" color="#b08900" width=5];
  {{ rank=same; r1; r2; r3; }} {{ rank=same; f1; f2; f3; }} {{ rank=same; a1; a2; a3; }} {{ rank=same; e1; e2; e3; }}
  r1 -> r2 -> r3 [style=invis]; f1 -> f2 -> f3 [style=invis]; a1 -> a2 -> a3 [style=invis]; e1 -> e2 -> e3 [style=invis];
  r1 -> f1; r2 -> f2; r3 -> f3; f3 -> a1; f3 -> a2; f3 -> a3; a1 -> e1; a3 -> e2; a3 -> e3; a2 -> e3 [style=dashed label=" search"]; e1 -> v; e2 -> v; e3 -> v;
}}''',
"decidability_ladder": f'''digraph L {{ rankdir=LR; nodesep=0.3; {STYLE}
  d [label="EQ_DFA\\ndecidable\\n(DFA product + reachability)" fillcolor="#e6f4ea" color="#3a7d44"];
  c [label="EQ_CFG\\nundecidable, but co-recognisable\\n(a difference can be found by search)" fillcolor="#fff4d6" color="#b08900"];
  t [label="EQ_TM\\nneither recognisable\\nnor co-recognisable" fillcolor="#fbe9e7" color="#b3412f"];
  d -> c [label="more memory"]; c -> t [label="more memory"];
}}''',
"pipeline": f'''digraph P {{ rankdir=TB; {STYLE}
  in [label="Two regexes   or   two functions + input domain" shape=note fillcolor="#ffffff"];
  q [label="Regex?" shape=diamond fillcolor="#ffffff"];
  rx [label="Thompson NFA for each regex\\nwalk the product of the two subset\\nconstructions breadth-first"];
  dm [label="Finite domain?" shape=diamond fillcolor="#ffffff"];
  ex [label="Run both on EVERY input\\n(line budget per run)"];
  dt [label="Differential testing\\nboundary values + random inputs"];
  E [label="EQUIVALENT\\n(exact / exact on domain)" fillcolor="#e6f4ea" color="#3a7d44"];
  N [label="NOT EQUIVALENT\\n+ witness input" fillcolor="#fbe9e7" color="#b3412f"];
  U [label="UNKNOWN" fillcolor="#fff4d6" color="#b08900"];
  in -> q; q -> rx [label="yes"]; q -> dm [label="no"]; rx -> E; rx -> N [label="mismatch\\n(shortest)"];
  dm -> ex [label="yes"]; dm -> dt [label="no"]; ex -> E [label="all agree"]; ex -> N [label="differ"]; ex -> U [label="timeouts"];
  dt -> N [label="differ"]; dt -> U [label="no difference"];
}}''',
"dfa_pair_example": '''digraph D { rankdir=LR; node [shape=circle fontname="Helvetica" fontsize=11]; edge [fontname="Helvetica" fontsize=10];
  subgraph cluster1 { label="(ab)*"; fontname="Helvetica-Bold"; color="#bbbbbb";
    s1 [shape=point]; p0 [shape=doublecircle label="p0"]; p1 [label="p1"];
    s1 -> p0; p0 -> p1 [label="a"]; p1 -> p0 [label="b"]; }
  subgraph cluster2 { label="a*b*"; fontname="Helvetica-Bold"; color="#bbbbbb";
    s2 [shape=point]; q0 [shape=doublecircle label="q0"]; q1 [shape=doublecircle label="q1"];
    s2 -> q0; q0 -> q0 [label="a"]; q0 -> q1 [label="b"]; q1 -> q1 [label="b"]; }
  note [shape=note fontname="Helvetica" fontsize=10 label="Product start (p0, q0): both accept.\\nRead 'a' -> (p1, q0): p1 rejects, q0 accepts.\\nShortest witness = \\"a\\""];
}''',
}

for name, dot in GRAPHS.items():
    (OUT / f"{name}.dot").write_text(dot)
    subprocess.run(["dot", "-Gdpi=170", "-Tpng", "-o", str(OUT / f"{name}.png")], input=dot.encode(), check=True)
    subprocess.run(["dot", "-Tsvg", "-o", str(OUT / f"{name}.svg")], input=dot.encode(), check=True)
    print("wrote", name)
