# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
inum = input()
Cube = 0
length = len(str(inum))
fnum = inum
while(n>0)
    digit = n%10
    Cube += digit **length
    inum = inum//10

if(Cube == fnum):
    print("Sum of Cubes is",Cube,". It is the same as the number",inum,".")
else:
    print("Sum of Cubes is",Cube,". It is NOT same as the number",inum,".")