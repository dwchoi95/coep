# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
temp=input()
Fahrenheit=float((temp))
Celsius=(Fahrenheit-32)*5/9
Celsius0=round(Celsius,2)
print('Fahrenheit temperature', Fahrenheit, 'is same as', Celsius0,'degree Celsius.')
