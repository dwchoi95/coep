A,B=map(int,input().split())
count = 0
total = 0
if B==1:
  print(0)
else:
  while True:
    total += A
    count += 1
    if total>=B:
      break
      total -= 1
  print(count)