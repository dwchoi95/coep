# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=input()
l=[]
for i in range(97,123):
    l.append(i)
j=[]
for i in l:
    x=chr(i)
    y=chr(i-32)
    if x not in n and y not in n:
        j.append(i)
k=[]
str1="
for i in j:
    str1=str1+chr(i)+','
str1=str1[:len(st)-2]
str1=str1+'.'
if j==k:
    print("Yes, the string is a pangram.")
else:
    print("No, the string is NOT a pangram. Missing letter(s) is(are)",str1)
    