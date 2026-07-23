N = int(input())
teki = input().split()
yusya = input().split()
i = 0
taoshita = 0

while i < N :
  if int(teki[i]) >= int(yusya[i]):
    a = int(yusya[i]) 
    b = 0
  else:
    a = int(teki[i])
    yusya[i] = int(yusya[i]) - int(teki[i])
    if int(teki[i+1]) >= yusya[i]:
      b = yusya[i]
      teki[i+1] = int(teki[i+1]) - yusya[i]
    else:
      b = int(teki[i+1])
  taoshita += a + b
  i += 1

print(taoshita)