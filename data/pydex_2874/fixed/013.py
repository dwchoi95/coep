# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
#initial input in int
Initial_Num = int(input())

#nested loop for statement goes one number in range for each loop
for TempRange in range(1,(Initial_Num+1)):
    #tells excatly how can * to print on each line i,2*i i.e 1 to 2 =1 , 2 to 4 = 2 and so on
  for FRange in range(TempRange, 2 * TempRange):
    print('*', end='')
  print()