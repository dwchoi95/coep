# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
#Convert the Fahrenheit temperature to Celsius temperature.
f= float(input())
c= (f-32)*(5/9))
print("Farenheit temperature {} is same as {} degree Celsius".format(f,round(float(c),2)))