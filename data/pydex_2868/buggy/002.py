# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
#!/usr/bin/env python
Fahrenheit = int(raw_input("Enter a temperature in Fahrenheit: "))

Celsius = (Fahrenheit - 32) * 5.0/9.0

print "Temperature:", Fahrenheit, "Fahrenheit = ", Celsius, " C"