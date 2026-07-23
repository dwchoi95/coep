# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n= int(input())
a= {}
for i in range(n):
    s=input().split(",")
    key = s[0].strip()+' # '+ s[1].strip()
    if key in a:
        a[key]+=int(s[2])
    else:
        a[key]=int(s[2])
li=[]
for key,value in a.items():
    b=str(key)+" # "+str(value)
    li.append(b)
li.sort()
for i in li:
    print(i)