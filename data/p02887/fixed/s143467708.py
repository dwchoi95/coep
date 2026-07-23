a = int(input().split()[0])
b = list(map(str, input().split()[0]))
k = 0
s = 1


while k<len(b) -1:
 t = b[k]
 u = b[k+1]
 
 if not t == u:
  s = s + 1
  
 k = k + 1
print(s)