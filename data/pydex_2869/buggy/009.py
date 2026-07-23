# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=int input()
number=str(n)
rev= number[::-1]
print("Reverse:",rev)
r=int(rev)
if n>10:
    sum=n+r
else:
    sum=n+n
