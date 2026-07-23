N = int(input())

ans = 1
for i in range(1,N+1):
    ans = ((ans%(1000000007)) * i) % 1000000007

print(ans)