# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
no=(input())
sum=0
for m in no:
    sum += int(m)**3
if sum == int(no):
    print("Sum of Cubes is {}. It is the same as the number {}.".format(sum,no))
else:
    print("Sum of Cubes is {}. It is NOT same as the number {}.".format(sum,no))