import sys
from collections import Counter
input = sys.stdin.readline

X, Y, A, B, C = map(int, input().split())
p = list(map(int, input().split()))
q = list(map(int, input().split()))
r = list(map(int, input().split()))

ans = []

ans.extend(sorted(p, reverse=True)[:X])
ans.extend(sorted(q, reverse=True)[:Y])
ans.extend(r)
ans.sort(reverse=True)

print(sum(ans[:X+Y]))