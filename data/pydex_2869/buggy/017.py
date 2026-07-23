# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
i=int(input())
s=str(i)
r=s[::-1]
sum=i+int(r)
print('Reverse:{}\nSum:{}.format(int(r),sum))
