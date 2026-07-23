S = int(input())
X1 = 0
Y1 = 0
if S <= 10**9:
    X2 = S
    Y2 = 0
    X3 = 0
    Y3 = 1
elif 10**9 < S < 10**18:
    T = S % 10**9
    X2 = 10**9
    Y3 = (S 
    X3 = 10**9 - T 
    Y2 = 1
else:
  X2 = 0
  Y2 = 10**9
  X3 = 10**9
  Y3 = 0
print(X1,Y1,X2,Y2,X3,Y3)