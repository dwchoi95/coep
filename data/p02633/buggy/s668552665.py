X = int(input())

K = 1
dire = X
while True:
  if (dire % 180) == 0:
    break
  K+=1
  dire+=X

  
print(K)