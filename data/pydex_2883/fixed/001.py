# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def Ackermann(m,n):
    if m==0:
        return  n+1
    if n==0:
        return Ackermann(m-1,1)
    return Ackermann(m-1,Ackermann(m,n-1))
   
mn=input()
tempList=mn.split(',')
m=int(tempList[0])
n=int(tempList[1])
print(Ackermann(m,n))