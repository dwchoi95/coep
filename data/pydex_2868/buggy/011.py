# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
F = float(input('temperature in fahrenheit '))
C = float((F - 32) * 5/9)
print('Fahrenheit temperature', F , 'is same as' , round(C,2) , 'degree Celsius. )