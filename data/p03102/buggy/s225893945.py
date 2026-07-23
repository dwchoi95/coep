n, m , c = map(int, input().split())
b_li = list(map(int, input().split()))
ans = 0
for i in range(n):
    a_li = list(map(int, input().split()))
    if (0 < a * b + c for a, b in zip(a_li, b_li)):
        ans += 1
print(ans)
