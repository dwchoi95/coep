S = input()
def check(s):
  return s[:int((len(s)-1)/2+1)]==s[int((len(s)-1)/2):][::-1]
if check(S) and check(S[:int((len(S)-1)/2+1)]) and check(S[int((len(S)+3)/2):]):
  print('Yes')
else:
  print('No')