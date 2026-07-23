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
elif S == 1000000000000000000:
    X2 = int(math.sqrt(S))
    Y3 = X2
else:
    X2 = int(math.sqrt(S) + 1)
    Y3 = X2
    s = X2 ** 2  - S 
    for i in range(1, int(math.sqrt(s) + 1)):
        if s%i == 0 and s
            X3 = i
            Y2 = s
            break

print (X1, Y1, X2, Y2, X3, Y3)
