s = list(input())

N = len(s)

RL = []
LR = [-1]
for i in range(N-1):
    if s[i] == 'R' and s[i+1] == 'L':
        RL.append(i)
    if s[i] == 'L' and s[i+1] == 'R':
        LR.append(i)

LR.append(N-1)

_num = []
for i in range(len(LR)-1):
    _num.append(LR[i+1] - LR[i])


ans = [0]*N

for i in range(len(_num)):
    if int(_num[i]/2) == _num[i]/2:
        ans[RL[i]] = int(_num[i]/2)
        ans[RL[i]+1] = int(_num[i]/2)
    else:
        if RL[i] - LR[i] > LR[i+1] - RL[i]:
            if int(RL[i] - LR[i]) == RL[i] - LR[i]:
                ans[RL[i]] = int(_num[i]/2) + 1
                ans[RL[i]+1] = int(_num[i]/2)
            else:
                ans[RL[i]] = int(_num[i]/2)
                ans[RL[i]+1] = int(_num[i]/2) + 1
        else:
            if int(LR[i+1] - RL[i]) == LR[i+1] - RL[i]:
                ans[RL[i]] = int(_num[i]/2) + 1
                ans[RL[i]+1] = int(_num[i]/2)
            else:
                ans[RL[i]] = int(_num[i]/2)
                ans[RL[i]+1] = int(_num[i]/2) + 1
                
print(ans)