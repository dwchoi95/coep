k = int(input())
if k%2 == 0:
    a = (k/2)**2
    print(int(a))
else:
    a = ((k-1)/2)*((k-1)/2 + 1)
    print(int(a))
