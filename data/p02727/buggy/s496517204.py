x, y, a, b, c = map(int, input().split())
p =list(map(int, input().split()))
q = list(map(int, input().split()))
r = list(map(int, input().split()))
p = sorted(p)
p = sorted(p)

p = p[(len(p)-x):]
q = q[(len(q)-y):]
r=r+p
r=r+q
r = sorted(r)
print(sum(r[(len(r)-x-y):]))
