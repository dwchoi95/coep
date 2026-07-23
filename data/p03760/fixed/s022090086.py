import sys

O = list(input())
E = list(input())
if len(O) - len(E) == 1:
    E.append('')
for o, e in zip(O, E):
    sys.stdout.write(o + e)
print()
