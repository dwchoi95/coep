N = int(input())
A = list(map(int, input().split()))
S = sorted(A, reverse=True)
w, h = 0, 0

cnt = 0
tmp = 0
l = S[0]
for i in range(N):
  if S[i] != l:
    if cnt == 0:
      if tmp > 3:
        w, h = l, l
        break
      elif tmp > 1:
        w = l
        tmp = 1
        l = S[i]
        cnt += 1
      else:
        tmp = 1
        l = S[i]
    else:
      h = l
      break
  else:
    tmp += 1
    if i == N-1:
      h = l
ans = w * h
print(ans)
