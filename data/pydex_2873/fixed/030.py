# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
#iniutla input in int
Initial_Number = int(input())

#length of the inital input
order = len(str(Initial_Number))

#value of Cubes initialized
Sum_of_Digits_Cube = 0

#temp inum to complete while loop
TempInitial_Number = Initial_Number


while TempInitial_Number > 0:
       digit = TempInitial_Number % 10
       Sum_of_Digits_Cube += digit ** 3
       TempInitial_Number //= 10



if(Sum_of_Digits_Cube == Initial_Number):
    print("Sum of Cubes is " + str(Sum_of_Digits_Cube) + ". It is the same as the number " + str(Initial_Number) +".")
else:
    print("Sum of Cubes is " + str(Sum_of_Digits_Cube) + ". It is NOT same as the number " + str(Initial_Number) +".")