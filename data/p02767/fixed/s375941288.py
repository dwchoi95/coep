N = int(input())
X = list(map(int, input().split()))
min_ans = +float('inf')

for i in range(1, 100):
    ans = 0
    for x in X:
        ans += (x - i)**2
    min_ans = min([min_ans, ans])

print(min_ans)