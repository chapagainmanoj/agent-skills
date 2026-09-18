"""Check idea-critic outputs: length, structure, plain language."""
import json
import re
import sys
from pathlib import Path

JARGON = [
    "moat", "monetiz", "monetis", "b2b", "b2c", "churn", "tam", "wedge",
    "go-to-market", "gtm", "value proposition", "value prop", "leverage",
    "synergy", "scalab", "freemium", "unit economics", "cac", "ltv",
    "differentiator", "defensib", "stakeholder",
]

READING_WPM = 230


def syllables(word):
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    n = len(groups)
    if word.endswith("e") and n > 1 and not word.endswith(("le", "ee")):
        n -= 1
    return max(n, 1)


def check(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # keep link text, drop the URL
    plain = re.sub(r"[*_`#>|]", "", text)
    words = re.findall(r"[A-Za-z0-9$%'’-]+", plain)
    sentences = [s for s in re.split(r"[.!?]+[\s\"”]+|\n+", plain) if len(s.split()) > 2]
    wc = len(words)
    avg_sentence = wc / max(len(sentences), 1)
    syl = sum(syllables(w) for w in words if re.search(r"[A-Za-z]", w))
    grade = 0.39 * avg_sentence + 11.8 * (syl / max(wc, 1)) - 15.59

    people = re.findall(r"^\*\*[^*:\n]+\*\*\s*[—–-]", text, flags=re.M)
    worries = len(re.findall(r"\*Worry:\*|Worry:", text))
    fixes = len(re.findall(r"\*Fix:\*|Fix:", text))
    lower = text.lower()
    jargon_hits = sorted({j for j in JARGON if re.search(r"\b" + re.escape(j), lower)})

    results = [
        ("Reply is 400 to 900 words (a 2 to 4 minute read)", 400 <= wc <= 900,
         f"{wc} words, about {wc / READING_WPM:.1f} min"),
        ("Covers 3 to 5 people", 3 <= len(people) <= 5, f"{len(people)} people"),
        ("Every person has a worry", len(people) > 0 and worries >= len(people), f"{worries} worries / {len(people)} people"),
        ("Every person has a fix", len(people) > 0 and fixes >= len(people), f"{fixes} fixes / {len(people)} people"),
        ("Has what's strong, biggest risk, verdict and next steps",
         bool(re.search(r"what[’']s strong", lower))
         and all(k in lower for k in ("biggest risk", "verdict", "next step")), ""),
        ("Verdict is Go, Fix first or Rethink",
         bool(re.search(r"verdict:?\*{0,2}\s*\*{0,2}(go|fix first|rethink)", lower)), ""),
        ("No business jargon", not jargon_hits, ", ".join(jargon_hits) or "none found"),
        ("Average sentence is 16 words or fewer", avg_sentence <= 16, f"{avg_sentence:.1f} words"),
        ("Reading level is grade 8 or lower", grade <= 8, f"grade {grade:.1f}"),
    ]
    return [{"text": t, "passed": bool(p), "evidence": e} for t, p, e in results]


def main(iteration_dir):
    root = Path(iteration_dir)
    for resp in sorted(root.glob("*/*/outputs/response.md")):
        run_dir = resp.parent.parent
        exp = check(resp.read_text())
        passed = sum(e["passed"] for e in exp)
        grading = {
            "expectations": exp,
            "summary": {"passed": passed, "failed": len(exp) - passed, "total": len(exp),
                        "pass_rate": round(passed / len(exp), 2)},
        }
        (run_dir / "grading.json").write_text(json.dumps(grading, indent=2))
        print(f"\n{run_dir.parent.name} / {run_dir.name}: {passed}/{len(exp)}")
        for e in exp:
            print(f"  {'PASS' if e['passed'] else 'FAIL'}  {e['text']}  [{e['evidence']}]")


if __name__ == "__main__":
    main(sys.argv[1])
