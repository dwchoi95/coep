# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num=str(input())
sum=0
for i in range(0,len(num)):
    sum+=pow(int(num[i]),3)
if sum==int(num):
    print("Sum of Cubes is "+str(sum)+". It is the same as the number "+str(num)+".")
else:
    print("Sum of Cubes is "+str(sum)+". It is NOT same as the number "+str(num)+".")