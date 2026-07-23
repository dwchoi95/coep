N=int(input())
d=list(map(int, input().split()))
a=(sum(d))**2

def square(list):
    return [i ** 2 for i in list]

b=sum(square(d))
result=a-b
print(result)