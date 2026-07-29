#!/bin/sh
# Build one track's documents.
#
#   ./build.sh main     -> main/main.pdf, main/supplementary.pdf, main/Reproducibility...pdf
#   ./build.sh first    -> first/first.pdf, first/first_supplementary.pdf, ...
#   ./build.sh          -> both
#
# The two tracks are separate submissions that share this directory's
# figures/, references.bib and supp/. TEXINPUTS points at paper/ so the shared
# aaai2027.sty and .bst resolve from inside a track directory; BIBINPUTS does
# the same for the merged bibliography.
set -e
here=$(cd "$(dirname "$0")" && pwd)
# The track directory comes first: a stray copy of a source left in paper/
# would otherwise shadow the real one and compile silently against it.
export TEXINPUTS=".:$here:$TEXINPUTS"
export BIBINPUTS=".:$here:$BIBINPUTS"
export BSTINPUTS=".:$here:$BSTINPUTS"

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

case "${1:-both}" in
  main)  set -- main ;;
  first) set -- first ;;
  both)  set -- main first ;;
  *) echo "usage: $0 [main|first]" >&2; exit 2 ;;
esac

for track in "$@"; do
    echo "$track:"
    case $track in
      main)  build_one main main
             build_one main supplementary
             build_one main ReproducibilityChecklist ;;
      first) build_one first first
             build_one first supplementary
             build_one first ReproducibilityChecklist ;;
    esac
done
