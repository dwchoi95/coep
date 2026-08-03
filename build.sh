#!/bin/sh
# Build the paper and the two documents that go with it.
#
#   ./build.sh
#
# figures/, tables/ and references.bib are reached by relative path from the
# sources, and first/ holds its own copy of the AAAI style files, so latexmk,
# an editor or a bare pdflatex run from inside first/ all work the same way
# this script does. No search paths are set.
set -e
here=$(cd "$(dirname "$0")" && pwd)

build_one() {
    dir=$1; stem=$2
    cd "$here/$dir"
    pdflatex -interaction=nonstopmode "$stem.tex" >/dev/null 2>&1 || true
    if grep -q '\\citation' "$stem.aux" 2>/dev/null; then
        bibtex "$stem" >/dev/null 2>&1 || true
    fi
    pdflatex -interaction=nonstopmode "$stem.tex" >/dev/null 2>&1 || true
    pdflatex -interaction=nonstopmode "$stem.tex" >/dev/null 2>&1 || true
    err=$(grep -c '^!' "$stem.log" || true)
    und=$(pdftotext "$stem.pdf" - 2>/dev/null | grep -c '??' || true)
    pg=$(pdfinfo "$stem.pdf" 2>/dev/null | awk '/Pages/{print $2}')
    printf '  %-34s %s pages, %s errors, %s unresolved\n' "$dir/$stem.pdf" "$pg" "$err" "$und"
}

for stem in first supplementary ReproducibilityChecklist; do
    build_one first "$stem"
done
