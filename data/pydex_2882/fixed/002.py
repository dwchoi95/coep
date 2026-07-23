# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def isprime(num,i=2):
    if num <= 2:
        return True if num == 2 else False
    if num % i == 0:
        return False
    if (i * i > num): 
        return True 
    return isprime(num,i+1)
    
def numrev(num):
    numstr=str(num)
    reversed=int(numstr[::-1])
    return reversed
    
def result(num1, num2):
	if (isprime(num1) and isprime(num2)):
		print(num1 + num2)
	elif (isprime(num1) or isprime(num2)):
		print(numrev(num1) + numrev(num2))
	else:
		print(numrev(num1) * numrev(num2))
    
data = str(input())
numList = data.split(',')
num1 = numrev(int(numList[0].strip()))
num2 = numrev(int(numList[1].strip()))
result(num1, num2)