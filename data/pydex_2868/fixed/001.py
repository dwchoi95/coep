# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
f = float(input())
c = (f-32)*(5/9)
print("Fahrenheit temperature {} is same as {} degree Celsius.".format(f,round(c,2)))