# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num=int(input())
ini=0
for (i) in str(num):
  cube=int(i)*int(i)*int(i)
  sum=ini+cube
if sum==num:
    print("Sum of Cubes is",sum, ".It is the same as the number", num)
else:
    print("Sum of Cubes is",sum, ".It is NOT same as the number", num))