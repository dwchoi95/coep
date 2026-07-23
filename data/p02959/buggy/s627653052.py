n = int(input())
a = list(map(int, input().split()))
b = list(map(int, input().split()))
ans = 0

def cal(ans, n):
    ans += min(a[n], b[n])
    ans += b[n] - min(a[n], b[n])
    a[n+1] -= min(a[n], b[n])
        
for i in range(n):
    cal(ans,i)

print(ans)
