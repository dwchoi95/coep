# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
temp=input()
    f_temp=float(temp)
celsius=(f_temp-32)*5/9
round(celsius, 2)
print('Fahrenheit temperature', temp,'is same as', celsius)