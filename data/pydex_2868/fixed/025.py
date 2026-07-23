# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
# input in fahrenheit
Fahrenheit_temp = float(input())

# Coversion Formula & assigning Celcius 
Celsius_temp = ((Fahrenheit_temp - 32)*5)/9

# printing the full statement
print('Fahrenheit temperature', Fahrenheit_temp ,'is same as',round(Celsius_temp,2),'degree Celsius.')