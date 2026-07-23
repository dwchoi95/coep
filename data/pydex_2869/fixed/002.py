# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x=int(input())
s=str(x)
print("Reverse:", int(s[::-1]))
print("Sum:", ((x) + int(s[::-1])))