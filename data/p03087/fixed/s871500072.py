N, Q = map(int,input().split())
S = input()
cnt = [0]
for i in range(len(S)-1):
    cnt.append(cnt[-1])
    if S[i] == 'A' and S[i+1] == 'C':
        cnt[-1] += 1
cnt = [0] + cnt

for _ in range(Q):
    l, r = map(int,input().split())
    ans = cnt[r] - cnt[l-1]
    if 2 <= l and (S[l-2] == 'A' and S[l-1] == 'C'):
        ans -= 1
    print(ans)