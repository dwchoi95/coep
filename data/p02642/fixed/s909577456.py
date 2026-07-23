n = int(input())
a = list(map(int, input().split()))
a.sort()
MAX = int(1e6) + 10
sieve = [0] * int(MAX)
for i in a:
    sieve[i] += 1
ans = 0
for idx, val in enumerate(sieve):
    if val == 0:
        continue
    elif val > 1:
        sieve[idx] = 0
    else:
        ans += 1
    for i in range(idx * 2, MAX, idx):
        sieve[i] = 0
print(ans)