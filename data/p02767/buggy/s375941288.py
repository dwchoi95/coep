N = int(input())
X = [int(n) for n in range(N)]

min_ans = +float('inf')

for i in range(N):
    ans = 0
    for x in X:
        ans += (x - i)**2
    min_ans = min([min_ans, ans])

print(min_ans)