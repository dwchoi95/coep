h, w = map(int, input().split())

table = [list(map(int, input().split())) for _ in range(10)]

def wf(table):
    from itertools import product
    for k, i, j in product(range(len(table)), repeat=3):
        table[i][j] = min(table[i][j], table[i][k] + table[k][j])

    return table

table = wf(table)

ans = 0
for _ in range(h):
    for i in map(int, input().split()):
        if i != -1:
            ans += table[i][1]

print(ans)
