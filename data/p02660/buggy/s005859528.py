n = int(input())

def divGame(N=n):
  if N == 1:
    return 0
  if N == 2:
    return 1
  
  factors = []
  
  count = 0
  while N % 2 == 0:
    N /= 2
    count += 1
  if count != 0:
    factors.append(count)

  for i in range(3, int(N**0.5 + 1), 2):
    count = 0
    while N % i == 0:
      N /= i
      count += 1
    if count != 0:
      factors.append(count)
  if N != 1:
    factors.append(1)

  factors.sort()

  answer = 0
  accum = 1
  count = 1
  for i in range(len(factors)):
    while factors[i] > accum:
      count += 1
      accum += count
    answer += count

  return answer

print(divGame())