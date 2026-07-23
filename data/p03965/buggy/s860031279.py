lis = list(input())
cou = 0
ans = 0
for i in range(len(lis)):
  if cou > 0 and lis[i] == "g":
    cou -= 1
    ans += 1
  else:
    cou += 1
    if lis[i] == "p":
      ans -= 1
print(ans)