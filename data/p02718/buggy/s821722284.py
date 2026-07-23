n, m = map(int, input().split())
arr = list(map(int, input().split()))
temp = sum(arr)
arr.sort()
arr = arr[::-1]
cnt = 0
for i in range(n):
    if arr[i] >= temp:
        cnt += 1
if cnt >= m:
    print("Yes")
    exit()
print("No")