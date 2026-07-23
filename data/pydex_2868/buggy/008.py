# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
fill input with Fahrenheit temperature
f = float(input())
c = float((f-32) * 5/9)
C = print('Fahrenheit temperature', f, 'is same as', round(c,2), 'degree Celsius.')