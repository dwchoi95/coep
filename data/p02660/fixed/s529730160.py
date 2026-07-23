from collections import Counter
n = int(input())
ans = 0

dp = []
cl = []
n1 = n
if n == 1:
    ans = 0
else:
    for i in range(2, int(n**0.5)+1):
        if n%i == 0:
            cl.append(i)
            while n%i == 0:
                n = n/i
                dp.append(i)
        if n == 1:
            break
    if n != 1:
        ans = 1

c = Counter(dp)

for i in cl:
    cnt = 1
    while c[i] >= cnt:
        c[i] -= cnt
        ans += 1
        cnt += 1
        
print(ans)
