# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
f_temp= float(input())
c_temp=(f_temp - 32) * 5/9
print('Fahrenheit temperature {} is same as {} degree Celsius.'.format(f_temp,round(c_temp,2)))