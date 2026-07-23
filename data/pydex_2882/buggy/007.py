# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def reverse(Z):
    numstr=str(Z)
    reversed=int(numstr[::-1])
    return reversed
def prime(P,i=2):
     if P <= 2:
        return True if P == 2 else False
     if P % i == 0:
        return False
     if (i * i > P): 
        return True 
     return prime(P,i+1)
def operation(X,Y):
    if (prime(X) and prime(Y)):
        print(X + Y)
	elif (prime(X) or prime(Y)):
	    print(reverse(X) + reverse(Y))
	else:
	    print(reverse(X) * reverse(Y))
dta=str(input())
lst=dta.split(',')
A=int(lst[0].strip())
B=int(lst[1].strip())
X=reverse(A)
Y=reverse(B)
operation(X,Y)