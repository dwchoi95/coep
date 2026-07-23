import sys

O = list(input())
E = list(input())
for o, e in zip(O, E):
    sys.stdout.write(o + e)
if len(O) - len(E) == 1:
    sys.stdout.write(E[-1])
print()
