a,b,c,d = map(int,input().split())
ans = []
for i in c,d:
    ans.append(a*i)
for j in c,d:
    ans.append(b*j)

print(max(ans))