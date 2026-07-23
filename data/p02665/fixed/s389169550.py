n = int(input())
arr = list(map(int,input().split()))
ans = [0]*(n+1)
ans[0] = 1
c_sum = [0]*(n+1)
c_sum[0] = arr[0]
for i in range(1,n+1):
    c_sum[i] = c_sum[i-1] + arr[i]
root = [0]*(n+1)
for d in range(n+1):
    if d==0:
        ans[d] = min(1,c_sum[-1])
    else:
        ans[d] = min(root[d-1]*2,(c_sum[-1] - c_sum[d-1]))
    root[d] = ans[d] - arr[d]
    if root[d] < 0:
        print(-1)
        exit()
print(sum(ans))


