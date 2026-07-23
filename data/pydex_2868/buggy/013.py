# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
temp=0.555
Fahrenheit=float((temp))
celsius=(Fahrenheit temp-32)*5/9
celsius0=round(celsius,2)
print('Fahrenheit temperature', Fahrenheit, 'is same as', celsius0,'degree celsius.')