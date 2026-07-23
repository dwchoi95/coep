S = input()
w = int(input())
for i in range(len(S)):
  if w != 1 and (i + 1) % w == 1 :
    print(S[i], end = "")
  elif w == 1:
    print(S[i], end = "")