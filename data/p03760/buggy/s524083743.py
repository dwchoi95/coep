O = input()
E = input()
ans = ""
for i in range(len(E)):
  ans+=O[i]
  ans+=E[i]
  
if len(O)%2==1:
  ans+=O[len(O)-1]

print(ans)