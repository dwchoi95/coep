
def inpl(): return tuple(map(int, input().split()))
from bisect import bisect_left, insort
N = int(input())
A = inpl()

before = sorted(A[:N])
middle = sorted(A[N:-N])
after = sorted(A[-N:])

S_before = [sum(before)]
S_after = [sum(after)]

for m in middle:
    if before[0] < m:
        S_before.append(S_before[-1] + m - before[0])
        insort(before, m)
        before = before[1:]
    else:
        S_before.append(S_before[-1])

for m in middle[::-1]:
    if after[-1] > m:
        S_after.append(S_after[-1] - m + after[-1])
        insort(after, m)
        after = after[:-1]
    else:
        S_after.append(S_after[-1])    

print(max([b-a for b, a in zip(S_before, S_after[::-1])])) 
