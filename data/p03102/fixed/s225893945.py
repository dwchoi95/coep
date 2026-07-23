n, m , c = map(int, input().split())
b_li = list(map(int, input().split()))
ans = 0
for i in range(n):
    a_li = list(map(int, input().split()))
    if sum(a * b for a, b in zip(a_li, b_li)) + c > 0:
        ans += 1
print(ans)
