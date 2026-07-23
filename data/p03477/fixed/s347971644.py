a,b,c,d = map(int, input().split())
s = a+b
t = c+d

if s>t:
  print("Left")
elif s<t:
  print("Right")
else:
  print("Balanced")