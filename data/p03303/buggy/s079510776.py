S = input()
w = int(input())
for i in range(len(S)):
  if (i + 1) % w == 1:
    print(S[i], end = "")