# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x1= input()
x2= x1.strip()
x3= x2.split(',')
A= int(x3[0])
B= int(x3[1])
def reverse (c):
    d=len(c)-1
    e=''
    while d>=0:
        e=e+c[d]
        d=d-1
    return(e)
a=int(reverse(x3[0]))
b=int(reverse(x3[1]))
def prime(pr):
    n=int(pr)-1
    while n>1:
        if int(pr)%n==0:
            ans= False
            break
        else:
            ans= True
        n=n-1
    if int(pr)==2:
        ans= True
    if int(pr)==1:
        ans= False
    else:
        ans=ans
    return ans
if prime(a) or prime(b):
    if prime(a) and prime(b):
        sol=a+b
    else:
        sol=A+B
else:
    sol=A*B
if A<=10000 and B<=10000 and A>=1 and B>=1:
    print(sol)