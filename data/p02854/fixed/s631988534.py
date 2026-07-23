N = int(input())
A = list(map(int, input().split()))

left_length = sum(A[:int(N/2)])
right_length = sum(A[int(N/2):])
if left_length > right_length :
  price = left_length - right_length
  for i in range(int(N/2)-1,0,-1) :
    var = abs(sum(A[:i]) - sum(A[i:]))
    if price > var :
      price = var
    else :
      break
else :
  price = right_length - left_length
  for i in range(int(N/2)+1,N) :
    var = abs(sum(A[i:]) - sum(A[:i]))
    if price > var :
      price = var
    else :
      break

print(price)