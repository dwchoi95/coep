# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
f=float(input())
c=(f-32)*5/9
c2=round(c,2)
print('Fahrenheit temperature', f ,'is same as' ,c2, 'degree Celsius'.)
