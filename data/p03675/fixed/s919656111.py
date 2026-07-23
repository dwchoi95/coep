input()
n=[x for x in input().split()]
nb=n[::-1]
bs=n[::2]
if len(nb)%2==0:
    be=nb[::2]
else:
    be=nb[1::2]
if len(n)==1:
    print(n[0])
else:
    ans=be+bs
    if len(n)%2!=0:
        ans=ans[::-1]
    print(" ".join(ans))