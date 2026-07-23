N = int(input())
X = list(map(int, input().split()))
sum = []

for n in range(1,101):
    s = 0
    for x in X:
            s = s + ((x-n)*(x-n))
    sum.append(s)

print(min(sum))