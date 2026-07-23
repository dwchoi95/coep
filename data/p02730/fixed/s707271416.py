S = input()

def check(s):
  return s==s[::-1]

if check(S) and check(S[:int((len(S)-1)/2)]) and check(S[int((len(S)+3)/2-1):]):
  print('Yes')
else:
  print('No')