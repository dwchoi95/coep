# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #

f=input()

c=((float(f)-32)*(5/9))
round(int(c),2)

print("Fahrenheit temperature",float(f), "is same as",round(float(c),2),"degree Celsius.")