r,D,x = [int(i) for i in input().split()]

print(r)


def calu(r,D,x):
    X =x
    for j in range(10):
       X = r*X-D
       print(X)

calu(r,D,x)