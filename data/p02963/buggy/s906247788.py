import math
S = int(input())
X1 = 0
Y1 = 0
X2 = 0
Y2 = 0
X3 = 0
Y3 = 0
if  S <= 10 ** 9:
    X2 = S
    Y3 = 1
else:
    X2 = int(math.sqrt(S) + 1)
    Y3 = X2
    s = X2 ** 2  - S 
    for i in range(1, int(math.sqrt(s) + 1)):
        if s%i == 0 and s%i <= 10 ** 8 and i <= 10 ** 8:
                X3 = i
                Y2 = s
                break

print (X1, Y1, X2, Y2, X3, Y3)
