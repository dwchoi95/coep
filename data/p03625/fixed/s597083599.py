N = int(input())
A = list(map(int, input().split()))
S = sorted(A, reverse=True)
w, h = 0, 0

cnt = 0
tmp = S[0]
for i in range(N):
  if S[i] == tmp:
    cnt += 1
    if cnt == 2:
      if w == 0:
        w = tmp
        cnt = 0
      else:
        h = tmp
        break
  else:
    cnt = 1
    tmp = S[i]
        
ans = w * h
print(ans)
