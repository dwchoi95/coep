n = int(input())
stack = [0]
queue = []
for i in range(n-1):
  c,s,f = (int(i) for i in input().split())
  queue.append((c,s,f))
for i in range(n):
 ans = 0
 for j in range(n-i-1):
   c,s,f = queue[i+j]
   
   if s >= ans:
    ans = s+c
   else:
     if ans%f == 0:
      ans +=c
     elif ans%f != 0:
      ans += ans%f+c
 if n-i-1 == 0:
  ans = 0
 print(ans)
