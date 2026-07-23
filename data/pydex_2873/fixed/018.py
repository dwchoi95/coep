# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
digit= int(input())
sum=0
new= digit
while new>0 :
    x= new%10
    sum= sum + x**3
    new= new//10
if sum==digit :
    descript1='Sum of Cubes is ' + str(sum) +'. ' + 'It is the same as the number ' + str(digit) + '.'
    print(descript1)

    
else:
     descript2= 'Sum of Cubes is ' + str(sum) + '. ' + 'It is NOT same as the number ' + str(digit) + '.'
     print(descript2)
    