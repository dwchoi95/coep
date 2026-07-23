input()
n=[x for x in input().split()]
nb=n[::-1]
bs=n[::2]
if len(nb)%2==0:
    be=nb[::2]
else:
    be=nb[::2]
if len(n)==1:
    print(n[0])
else:
    print(" ".join(be+bs))