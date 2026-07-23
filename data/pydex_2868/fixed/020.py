# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
temp_f = float(input())
temp_c = round((temp_f - 32)*(5/9),2)
print("Fahrenheit temperature", temp_f, "is same as", temp_c, "degree Celsius.")