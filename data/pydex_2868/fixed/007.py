# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
Fahrenheit = float(input())
Celsius = (Fahrenheit - 32) * 5/9
C1 = round(Celsius,2)
print('Fahrenheit temperature', Fahrenheit, 'is same as', C1, 'degree Celsius.')
