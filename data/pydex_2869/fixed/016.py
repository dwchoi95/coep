# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
x=int(input())
y=str(x)
z=y[::-1]
a=int(z)
print("Reverse: {}".format(a))
Sum=x + a
print("Sum: {}".format(Sum))
