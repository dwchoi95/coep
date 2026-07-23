n = int(input())
a = str(input())
list = a.split()
for i in list[n:0:-1]:
    print(i, end = ' ')
print(list[0])

