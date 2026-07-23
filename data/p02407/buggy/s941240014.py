n = int(input())
x = [int(i) for i in input().split()]
x.sort()
x.reverse()
for i in range(n-1):
    print(x[i]," ",sep="",end="")
print(x[n-1])

