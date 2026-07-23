inp = list(map(int,input().split()))
ans = []
for i in range(4):
  for j in range(i+1,4):
    ans.append(inp[i] * inp[j])
    
print(max(ans))