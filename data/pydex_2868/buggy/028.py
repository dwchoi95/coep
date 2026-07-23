# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
F=float(input('Fahrenheit temperature '))
C=float((F - 32) * 5/9)
print(F,'is same as',,round(C,2),'degree Celsius.')