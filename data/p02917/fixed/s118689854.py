N = int(input())
B = list(map(int, input().split()))

ans = sum(B)*2

for i in range(N-2):
    ans -= max(B[i],B[i+1])


print(ans)