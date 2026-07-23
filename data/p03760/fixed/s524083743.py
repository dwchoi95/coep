O = input()
E = input()
ans = ""
for i in range(len(E)):
  ans+=O[i]
  ans+=E[i]
  
if len(O)>len(E):
  ans+=O[len(O)-1]

print(ans)