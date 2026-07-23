S = list(input())

N = len(S)

ans = [0]*N

for _ in range(2):
    cnt = 0
    for i in  range(len(S)):
        if S[i] =='R':cnt +=1
        else:
            ans[i] += int(cnt/2)
            ans[i-1] += int((cnt+1)/2)
            cnt = 0

    S.reverse()
    ans.reverse()
    for i in range(len(S)):
        if S[i] == 'L':
            S[i] ='R'
        else:
            S[i] = 'L'

print(*ans)