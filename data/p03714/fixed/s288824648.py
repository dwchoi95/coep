import heapq
n = int(input())
a = list(map(int,input().split()))
aka = a[:n]
heapq.heapify(aka)
akasum = [0] * (n+1)
akasum[0] = sum(aka)
ao = a[2*n:]
aosum = [0] * (n+1)
aosum[-1] = sum(ao)
for i in range(len(ao)):
  ao[i] = -ao[i]
heapq.heapify(ao)
for i in range(n,2*n):
  b = heapq.heappop(aka)
  if b >= a[i]:
    heapq.heappush(aka, b)
    akasum[i-n+1] = akasum[i-n] 
  else:
    heapq.heappush(aka, a[i])
    akasum[i-n+1] = akasum[i-n] + a[i] - b
  b = heapq.heappop(ao)
  if b >=  -a[-i-1]:
    heapq.heappush(ao, b)
    aosum[-i+n-2] = aosum[-i+n-1]
  else:
    heapq.heappush(ao, -a[-i-1])
    aosum[-i+n-2] = aosum[-i+n-1] + a[-i-1] + b
ans = - float("inf")
for i in range(n+1):
  kota = akasum[i] - aosum[i]
  ans = max(kota,ans)
print(ans)