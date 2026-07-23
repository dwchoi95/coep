s=list(input())
n=len(s)
zenhan=s[0:int((n-1)/2)]
kouhan=s[int((n+3)/2-1):n]
if s==s[::-1] and zenhan==zenhan[::-1] and kouhan==kouhan[::-1]:
  print('Yes')
else:
  print('No')
