# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=int(input())
temp=n
sum=0
while temp>0:
    d=temp%10
    sum +=d**3
    temp //=10
if n==sum:
    print("Sum of Cubes is",n". It is the same as the number",n".")
else:
    print("Sum of Cubes is",n". It is NOT the same as the number",n".")