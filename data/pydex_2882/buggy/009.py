# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def prime(a):
    i=1
    t=0
    for i in range(1,a+1):
        if a%i==0:
            t=t+1
    if t==2:
        return 'true'

a=input()
x=a.replace(' ','')
x=x.split(',')
a1=x[0]
a2=[x[1]
#x=prime(a)
print (a1,a2)
if (x=='true'):
    print ("prime")
else:
    print ("not prime")