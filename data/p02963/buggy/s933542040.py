S = int(input())
X1 = 0
Y1 = 0
if S <= 10**9:
    X2 = S
    Y2 = 0
    X3 = 0
    Y3 = 1
else:
    S = 10**18 - S
    X2 = 10**9
    Y3 = 10**9
    X3 = S
    Y2 = 1
print(X1,Y1,X2,Y2,X3,Y3)
    