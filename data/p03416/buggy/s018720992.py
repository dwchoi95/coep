a, b = map(int, input().split())

ans = 0
for i in range(a, b+1):
    s = str(i)
    sl = len(s) 
    
    if s[:sl] == s[-sl:]: ans += 1
print(ans)