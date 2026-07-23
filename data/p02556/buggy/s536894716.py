N = int(input())
i = []
j = []
for k in range(N):
    x, y = map(int, input().split())
    i.append(x+y)
    j.append(-x-y)

print(max(abs(max(i)+max(j)), abs(min(i)+min(j))))
