s=list(input())
n=len(s)
zenhan=s[0:int((n-1)/2)]
kouhan=s[int((n+3)/2-1):n]
print(zenhan)
print(kouhan)
print(zenhan[::-1])
print(kouhan[::-1])
if s==s[::-1] and zenhan==zenhan[::-1] and kouhan==kouhan[::-1]:
  print('Yes')
else:
  print('No')
