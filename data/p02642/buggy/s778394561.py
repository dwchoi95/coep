from collections import deque 
n = int(input())
a = list(map(int, input().split()))
a.sort()
a = deque(a)
y = [min(a)]
t = 0
while a:
    v = a.popleft()
    x = 0
    for j in y:
        if v % j == 0:
            break
        else:
            x += 1
        if v == j:
            t += 1
        if x == len(y):
            y.append(v)
print(len(y) - t)