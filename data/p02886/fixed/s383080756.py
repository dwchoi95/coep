

import sys
from itertools import combinations

s2nn = lambda s: [int(c) for c in s.split(' ')]
ss2nn = lambda ss: [int(s) for s in list(ss)]
ss2nnn = lambda ss: [s2nn(s) for s in list(ss)]
i2s = lambda: sys.stdin.readline().rstrip()
i2n = lambda: int(i2s())
i2nn = lambda: s2nn(i2s())
ii2ss = lambda n: [i2s() for _ in range(n)]
ii2nn = lambda n: ss2nn(ii2ss(n))
ii2nnn = lambda n: ss2nnn(ii2ss(n))

def main():
    N = i2n()
    d = i2nn()
    print(sum(a*b for a, b in combinations(d, 2)))
main()
