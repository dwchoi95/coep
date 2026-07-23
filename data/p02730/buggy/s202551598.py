S = input()
N = len(S)
kai = []
kai2 = []
kai3 = []
rev = []
rev2 = []
rev3 = []

for i in range(N):
  kai.append(S[i])

for i in range(0, int((N - 1) / 2)):
  kai2.append(S[i])

for i in range(int((N + 3) / 2) - 1, N):
  kai3.append(S[i])

kai.reverse
kai2.reverse
kai3.reverse

for i in range(N):
  rev.append(S[i])

for i in range(0, int((N - 1) / 2)):
  rev2.append(S[i])

for i in range(int((N + 3) / 2) - 1, N):
  rev3.append(S[i])
  
if kai == rev:
  if kai2 == rev2:
    if kai3 == rev3:
      print('Yes')
    else:
      print('No')
  else:
    print('No')
else:
  print('No')
