n = int(input())
a = list(map(int, input().split()))
d = [0] * (10**5 + 2)
neg_count = 0
for i in range(len(a)):
  d[a[i] - 1] += 1
  d[a[i]] += 1
  d[a[i] + 1] += 1
ans = max(d)