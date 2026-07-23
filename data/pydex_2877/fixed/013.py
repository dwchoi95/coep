# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
enter= input().split(",")
y=[x for x in enter]
output=0
for x in y:
    if len(x)>=2 and x[0]==x[len(x)-1:] :
        output=output+1
print (output)

