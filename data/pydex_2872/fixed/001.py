# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
i=str(input())
x=i.find("not")
y=i.find("bad")
z=x<y
if(z == True):
    snot=i.split("not")
    sbad=i.split("bad")
    s1=snot[0]
    s3=sbad[1]
    print(s1+"good"+s3)
else:
    print(i)
