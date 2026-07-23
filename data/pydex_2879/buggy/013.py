# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n= int(input())
a= {}
for i in range(n):
    s=input().split(",")
    key = s[0].strip()+' # '+ s[1].strip()
        a[s[0]]+=int(s[2])
    else:
        a[s[0]]=int(s[2])
for key,value in a.items():
    print(str(key)+" # "+str(value))