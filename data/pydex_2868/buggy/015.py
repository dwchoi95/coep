# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
F=float(())
C=(F-32)*5/9
print("temperature fahrenheit" F "is same as" round(C,2) "degree celsius")
