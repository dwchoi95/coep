a =int(input())
list = []
b = 1
for i in range(2,44):
    list.append(b)
    b = b + i
n = 0
e = 0
k = 0
for i in range(2,1000000):
    if (a % i == 0):
        warikaisi = True
        while(warikaisi):
            if a % i == 0:
                list.append(i)
                a = a / i
                e = e + 1
                if (e == list[k]):
                    n = n + 1
                    k = k + 1
            else:
                e = 0
                k = 0
                warikaisi = False
if (n == 0 and a != 1):
    n = 1
if (a >= 1000000):
    n = 1
print(n)