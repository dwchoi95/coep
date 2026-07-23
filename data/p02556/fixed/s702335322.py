n = int(input())
z = [0 for _ in range(n)]
w = [0 for _ in range(n)]

for i in range(n):
    x, y = map(int, input().split())
    z[i], w[i] = x+y, x-y

print(max(max(z)-min(z), max(w)-min(w)))