
import sys

S =  input()
l = len(S)
ans = [0] * l
cot = [0,0]
for i  in range(l):
    if S[i] == "R":
        cot[i%2] += 1
    else:
        ans[i] += cot[i %2 ]
        ans[i - 1 ] += cot[(i + 1)%2]
        cot[0] = cot[1] = 0

cot[0] = cot[1] = 0
for i  in range(l-1,0,-1):
    if S[i] == "L":
        cot[i%2] += 1
    else:
        ans[i] += cot[i %2 ]
        ans[i + 1 ]  += cot[(i + 1)%2]
        cot[0] = cot[1] = 0
print(" ".join(list(map(str,ans))))


