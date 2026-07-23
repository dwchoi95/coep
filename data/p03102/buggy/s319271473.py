n ,m, c = map(int, input().split())
B = list(map(int, input().split()))
A = [list(map(int,input().split())) for i in range(n)] 
    

count = 0
for i in A:
  numberSum = c
  for a, b in zip(i, B):
    numberSum += (a * b)  
    if numberSum > 0:
      count += 1
print(count)
  