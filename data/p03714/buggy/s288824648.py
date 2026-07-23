import heapq
n = int(input())
a = list(map(int,input().split()))
aka = a[:n]
heapq.heapify(aka)
akasum = [0] * (n+1)
akasum[0] = sum(aka)
ao = a[2*n:]
heapq._heapify_max(ao)
aosum = [0] * (n+1)
aosum[-1] = sum(ao)
for i in range(n,2*n):
  b = heapq.heappop(aka)
  if b >= a[i]:
    heapq.heappush(aka, b)
  else:
    heapq.heappush(aka, a[i])
  akasum[i-n+1] = sum(aka)
  b = heapq.heappop(ao)
  if b <= a[-i-1]:
    heapq.heappush(ao, b)
  else:
    heapq.heappush(ao, a[-i-1])
  aosum[-i+n-2] = sum(ao)
ans = - float("inf")
for i in range(n+1):
  kota = akasum[i] - aosum[i]
  ans = max(kota,ans)
print(ans)