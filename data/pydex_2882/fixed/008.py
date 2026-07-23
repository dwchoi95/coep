# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def prime(a):
    if a>1:
        for i in range(2,a): 
            if (a%i) == 0:
                return False
                break
        else:
            return True

num = input()
num = num.split(',')
x, y = (num[0], num[1])
num2 = (int(x[::-1]),int(y[::-1]))
if prime(num2[0]) and prime(num2[1]) == True:
    print(num2[0] + num2[1])
elif prime(num2[0]) == True or prime(num2[1]) == True:
    print(int(x) +int(y))
else:
    print(int(x)*int(y))