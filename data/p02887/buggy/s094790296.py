N = int(input())
S = list(input().split())
 
ans = 1
for i in range(N - 1):
    if i != i + 1:
        ans = ans + 1
print(ans)