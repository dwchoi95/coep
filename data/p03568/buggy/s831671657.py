from sys import stdin
def readLine_int_list():return list(map(int, stdin.readline().split()))

n = int(input())
a = readLine_int_list()
even = [i for i in a if i%2 == 0]
e = len(even)
one = a.count(1)


if e == 0:
    if n == 1:
        print(2-one)
    else:
        print(n**3 - 1 - one)
else:
    print(3**n - (2**e) - one)