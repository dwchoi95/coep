# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
s=input()
s=int(s)
x=abs(s)
c=str(x)
v=c[::-1]
if (s>=0):
    print("Reverse:",int(v))
    print('Sum:',int(c)+int(v))
else:
    print('Reverse:',int(v)*(-1))
    print('Sum:',(int(c)+int(v))*-1)