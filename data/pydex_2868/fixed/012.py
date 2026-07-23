# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
fahrenheit=float(input())
celcius=(fahrenheit-32)*(5/9)
cel_round=round(celcius,2)
print("Fahrenheit temperature",fahrenheit,"is same as",cel_round,"degree Celsius.") 

    