import heapq
n = int(input())
a = list(map(int,input().split()))


left_seq = sorted(a[0:n])
right_seq =  sorted(a[2*n:3*n],reverse=True)
for i in range(n):
  right_seq[i]=-right_seq[i]






left_sum = [0]*(n+1)
right_sum = [0]*(n+1)
left_sum[0] =  sum(left_seq) 
right_sum[n] =  sum(right_seq) 


for i in range(n):
  if left_seq[0]<a[n+i]:
    left_sum[i+1] = left_sum[i] + a[n+i] - left_seq[0]
    heapq.heappop(left_seq)
    heapq.heappush(left_seq, a[n+i])
  else:
    left_sum[i+1] = left_sum[i]
  
  

for i in range(n)[::-1]:
  if right_seq[0]<-a[n+i]:
    right_sum[i] = right_sum[i+1] + (-a[n+i]) - right_seq[0]
    
    heapq.heappop(right_seq)
    heapq.heappush(right_seq, -a[n+i])
    
  else:
    right_sum[i] = right_sum[i+1]
  

ans = -float("inf")
for i in range(n+1):
  
  ans = max(ans,left_sum[i]+right_sum[i])
print(ans)