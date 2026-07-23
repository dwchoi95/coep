X=int(input())
i=1
while True:
  X=X*i
  if X%360==0:
    print(i)
    break
  i+=1