h, w = map(int, input().split())

mp = []
for _ in range(h):
  lst = list(map(int, input().split()))
  cum = []
  acc = 0
  for i in lst:
    if not i:
      acc += 1
    else:
      acc = 0
    cum.append(acc)
  mp.append(cum)
mp.append([-1] * w)
ans = 0


for i in range(w - 1, -1, -1):
  stack = []

  for j in range(h + 1):

    score = mp[j][i]
    if not stack:
      stack.append((score, j))
    else:
      last_score, last_ind = stack[-1][0], stack[-1][1]
      if score > last_score:
        stack.append((score, j))
      elif score == last_score:
        continue
      else:
        while stack and stack[-1][0] > score:
          last_score, last_ind = stack.pop()
          ans = max(ans, last_score * (j - last_ind))
        if not stack:
          stack.append((score, last_ind))
        elif stack[-1][0] == score:
          pass
        else:
          stack.append((score, last_ind))

print(ans)
