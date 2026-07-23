n, m, c = map(int, input().split())
b_lists = list(map(int, input().split()))
a_lists = []
for _ in range(n):
    tmp = list(map(int, input().split()))
    a_lists.append(tmp)

cond = c
ans = 0
for i in a_lists:
    for j in range(m):
        cond = c
        cond += i[j]*b_lists[j]
    if cond > 0:
        ans += 1

print(ans)