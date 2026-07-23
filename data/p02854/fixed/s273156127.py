n = int(input())
a = [int(i) for i in input().split()]
l = sum(a)
l2 = l / 2
tmp = 0
err = [l,l]
errindex = [0,0]
ans = 0
for i in range(n):
    tmp += a[i]
    if err[0] > l2 - tmp and l2 - tmp >= 0:
        err[0] = l2 - tmp
    if err[1] > tmp - l2 and l2 - tmp <= 0:
        err[1] = tmp - l2

tmp2 = min(err)
tmp3 = int(tmp2)
ans = tmp3 * 2 
if tmp2 - tmp3 > 0:
    ans += 1
print(ans)
