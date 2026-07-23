# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a=str(input())
x=a.split(",")
i=0 , count=0
while (i<len(x)):
    word=x[i]
    if(len(word)>=2 and word[0]==word[len(word)-1]):
        count=count+1
    i=i+1
print (count)