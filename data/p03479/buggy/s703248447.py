def input_int():
    return map(int, input().split())

def one_int():
    return int(input())

def one_str():
    return input()

def many_int():
    return list(map(int, input().split()))

X,Y=input_int()
count=0
while X<Y:
    count+=1
    X*=2
print(count)