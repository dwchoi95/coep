# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
temp=input()
f_temp=float((temp))
celsius=(f_temp-32)*5/9
celsius1=round(celsius, 2)
print('Fahrenheit temperature', f_temp,'is same as', celsius1, 'degree Celsius.')