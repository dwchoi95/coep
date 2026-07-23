N, Q = map(int, input().split())
S = input()

ans = [0]*N
for i in range(N-1):
    if S[i] == "A" and S[i+1] == "C":
        ans[i+1] += (ans[i]+1)
    else:
        ans[i+1] = ans[i] 

for i in range(Q):
    l, r = map(int, input().split())
    print(ans[r-1] - ans[l-1])