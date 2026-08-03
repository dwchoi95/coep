#!/bin/sh
# Build the paper and the two documents that go with it.
#
#   ./build.sh
#
# Everything the sources reference -- figures/, tables/, references.bib and the
# AAAI style files -- sits beside them in this directory, so latexmk, an editor
# or a bare pdflatex all work the same way this script does. No search paths
# are set.
set -e
cd "$(dirname "$0")"

build_one() {
    stem=$1
    pdflatex -interaction=nonstopmode "$stem.tex" >/dev/null 2>&1 || true
    if grep -q '\\citation' "$stem.aux" 2>/dev/null; then
        bibtex "$stem" >/dev/null 2>&1 || true
    fi
    pdflatex -interaction=nonstopmode "$stem.tex" >/dev/null 2>&1 || true
    pdflatex -interaction=nonstopmode "$stem.tex" >/dev/null 2>&1 || true
    err=$(grep -c '^!' "$stem.log" || true)
    und=$(pdftotext "$stem.pdf" - 2>/dev/null | grep -c '??' || true)
    pg=$(pdfinfo "$stem.pdf" 2>/dev/null | awk '/Pages/{print $2}')
    printf '  %-28s %s pages, %s errors, %s unresolved\n' "$stem.pdf" "$pg" "$err" "$und"
}

for stem in main supplementary ReproducibilityChecklist; do
    build_one "$stem"
done
