n = int(input())
a = list(map(int, input().split()))
num = [0 for i in range(max(a)+2)]
for i in a:
    num[i] += 1
temp = 0
ans = 0
for i in range(max(a)):
    temp = num[i] + num[i+1] + num[i+2]
    ans = max(temp, ans)
print(ans)