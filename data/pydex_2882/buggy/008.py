# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def prime(x):
    if x>1:
        for i in range(2,x):
            if x%i ==0:
                return(False)
                break
        else:
            return(True)


num = input()
num = num.split(' ')
x, y = (num[0], num[1])
reverse = (int(x[::-1]), int(y[::-1]))
if prime(reverse[0]) and prime(reverse[1]) == True:
    print(num[0] + num[1])
elif prime(reverse[0]) or prime(reverse[1]) == True:
    print(int(x)+int(y))
else prime(reverse[0]) and prime(reverse[1]) == True:
    print(int(x)*int(y))
