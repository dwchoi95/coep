import re
import sys

line = next(map(str.strip, sys.stdin))

count = 0
nb_bs = 0
for i, c in enumerate(line):
    if c == 'W' and nb_bs > 0:
        count += nb_bs
    elif c == 'B':
        nb_bs += 1

print(count)
