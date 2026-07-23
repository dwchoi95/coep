# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a = int(input())
b = str(a)
c = b[ ::-1]
d = int(a) + int(b)
print("Reverse:  "c)
print("Sum:  "d)