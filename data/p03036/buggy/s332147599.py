x=input()
xx=x.split()
r=int(xx[0])
x2=int(xx[1])
D=int(xx[2])
y=[0]*10
for i in range(10):
  y[i]+=r*x2-D
  print(y[i])
  x2=y[i]