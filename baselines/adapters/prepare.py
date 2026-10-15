"""Rebuild the BRAFAR and MENTORED inputs for the CoEP benchmark.

    git clone https://github.com/LinnaX7/brafar-python baselines/brafar
    git clone https://github.com/dwchoi95/MENTORED      baselines/mentored
    (cd baselines/brafar   && git apply ../adapters/brafar.patch   && unzip -q data.zip)
    (cd baselines/mentored && git apply ../adapters/mentored.patch && unzip -q data.zip -d /tmp/mentored)
    python3 baselines/adapters/prepare.py /tmp/mentored/data

BRAFAR, R1-R5: its own data.zip (the Refactory corpus, names match ours); the
authors' shipped run is kept as brafar_result_100.authors.csv. C1-C6: the
stdio export already built for Refactory (baselines/refactory/data_cf), with each
test input turned into the expression ``_run(stdin)`` BRAFAR's harness needs.

MENTORED, R1-R5: its own datasets (problem_11..15) and the authors' run
(feedbacks/mentored_authors). C1-C6: built from data/<pid> with raw stdin as
input. Directories are problem_1..11 in ORDER; mapping.json names them.
"""
import json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORDER = ["refactory_q1", "refactory_q2", "refactory_q3", "refactory_q4", "refactory_q5",
         "cf_110A", "cf_131A", "cf_1011B", "cf_125A", "cf_11B", "cf_10C"]
RUN = '''

def _run(s):
    """BRAFAR adapter: feed stdin, run main(), return whitespace-normalized stdout."""
    _feed(s)
    try:
        main()
    except _Exit:
        pass
    return " ".join("\\n".join(_OUT).split())
'''


def brafar():
    data = ROOT / "baselines/brafar/data"
    for q in range(1, 6):
        own = data / f"question_{q}" / "brafar_result_100.csv"
        if own.exists() and not own.with_suffix(".authors.csv").exists():
            own.rename(own.with_name("brafar_result_100.authors.csv"))
    for src in sorted((ROOT / "baselines/refactory/data_cf").iterdir()):
        out = ROOT / "baselines/brafar/data_cf" / src.name
        shutil.rmtree(out, ignore_errors=True)
        shutil.copytree(src, out, ignore=shutil.ignore_patterns("*.csv"))
        for f in (out / "ans").glob("input_*.txt"):
            m = re.match(r"_feed\((.*)\) ; main\(\) ; _flush\(\) #print\($", f.read_text().strip(), re.S)
            f.write_text(f"_run({m.group(1)})")
        g = out / "code" / "global.py"
        g.write_text(g.read_text() + RUN)


def mentored(authors_data: Path):
    out = ROOT / "baselines/mentored/data_coep"
    mapping = {}
    for i, pid in enumerate(ORDER, 1):
        d = out / f"problem_{i}"
        d.mkdir(parents=True, exist_ok=True)
        mapping[d.name] = pid
        if pid.startswith("refactory_q"):
            theirs = authors_data / f"problem_{10 + int(pid[-1])}"
            shutil.copy(theirs / "dataset.json", d / "dataset.json")
            fb = d / "feedbacks" / "mentored_authors"
            fb.mkdir(parents=True, exist_ok=True)
            shutil.copy(theirs / "feedbacks/mentored/with_correct.json", fb)
            continue
        src = ROOT / "data" / pid
        pj = json.loads((src / "problem.json").read_text())
        (d / "dataset.json").write_text(json.dumps({
            "problem": {"1": {"title": pid, "description": pj["description"]}},
            "testcases": {str(k + 1): {"no": k + 1, "input": t["stdin"],
                                       "output": str(t["expected"]).strip()}
                          for k, t in enumerate(pj["tests"])},
            "corrects": {"1": {p.stem: p.read_text() for p in sorted((src / "correct").glob("*.py"))}},
            "wrongs": {"1": {p.stem: p.read_text() for p in sorted((src / "buggy").glob("*.py"))}}}))
    (out / "mapping.json").write_text(json.dumps(mapping, indent=1))


if __name__ == "__main__":
    brafar()
    mentored(Path(sys.argv[1]))
