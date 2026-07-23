# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
F = float(input())
C = (F-32)*5/9
c1=round(C,2)
print('Fahrenheit temperature',F,'is same as',c1,'degree Celsius.')