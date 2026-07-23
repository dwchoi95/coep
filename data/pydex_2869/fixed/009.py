# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
number=input()
n=int(number)
if n>10:
    rev= number[::-1]
else:
    rev=number
r=int(rev)
print("Reverse:",r)
if n>10:
    sum=n+r
else:
    sum=n+n
print("Sum:",sum)