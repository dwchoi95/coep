s = input()
t = input()


def pattern(inputv):
    if not inputv:
        return inputv

    nxt = [0]*len(inputv)
    for i in range(1, len(nxt)):
        k = nxt[i - 1]
        while True:
            if inputv[i] == inputv[k]:
                nxt[i] = k + 1
                break
            elif k == 0:
                nxt[i] = 0
                break
            else:
                k = nxt[k - 1]

    smallPieceLen = len(inputv) - nxt[-1]
    if len(inputv) % smallPieceLen != 0:
        return inputv

    return inputv[0:smallPieceLen]

if pattern(s) == pattern(t):
    print(-1)
    exit()

s = s + s
cnt = 0
ans = []

j = 0
i = 0
li = []
flag = True
while i< len(s):
    
    if s[i] == t[j]:
        flag = True
        if j == len(t) - 1:
            cnt += 1
            j = 0
            i += 1
        else:
            j += 1
            i += 1
    else:
        if cnt != 0:
            ans.append(cnt)
        cnt = 0
        j = 0
        if flag:
            i += 1
            flag = False
        else:
            flag = True
            continue
if cnt != 0:
    ans.append(cnt)
    cnt = 0

ans.append(0)
print(max(ans))