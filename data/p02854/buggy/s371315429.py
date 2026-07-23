N = int(input())
A = list(map(int, input().split()))

now_length = sum(A)
half = now_length / 2
low_price = now_length - sum(A[:int(N/2)])

if half > low_price :
  for i in range(int(N/2),0,-1) :
    var = now_length - sum(A[:i])
    if half == low_price :
      break
    elif low_price > var :
      low_price = var
    else :
      break
else :
  for i in range(int(N/2)+1,N) :
    var = now_length - sum(A[:i])
    if half == low_price :
      break
    elif low_price > var :
      low_price = var
    else :
      break

if low_price == half :
  print(0)
else :
  print(low_price)
