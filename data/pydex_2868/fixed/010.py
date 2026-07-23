# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
F = float(input())
C = (F-32)*5/9
C = round(C,2)
print("Fahrenheit temperature {} is same as {} degree Celsius.".format(F,C))