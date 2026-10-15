#!/bin/sh
# Build the paper: ./build.sh  (IEEEtran.cls comes with TeX Live)
set -e
cd "$(dirname "$0")"
pdflatex -interaction=nonstopmode main.tex >/dev/null
bibtex main >/dev/null
pdflatex -interaction=nonstopmode main.tex >/dev/null
pdflatex -interaction=nonstopmode main.tex >/dev/null
grep -E "^!|undefined" main.log || true
pdfinfo main.pdf 2>/dev/null | grep Pages || true
