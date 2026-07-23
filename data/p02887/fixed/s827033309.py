import sys
from itertools import accumulate
input = sys.stdin.readline
def inputs():return [int(x) for x in input().split()]
N = int(input())
S= list(input())
s = []
cnt= 1
for i in range(len(S)-2):
  if S[i]==S[i+1]:
    cnt+=1
  else:
    s.append(cnt)
    cnt=1
s.append(cnt)
print(len(s))