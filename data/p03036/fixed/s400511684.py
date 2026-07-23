r,D,x_2000 = map(int,input().split())


X=[x_2000]
for i in range(10):
    X.append(r*X[i] - D)


print(*X[1:],sep="\n")
    