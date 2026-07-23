# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
inp=input()
letters=[]
for i in range(97,123):
    letters.append(i)
miss=[]
for i in letters:
    t=chr(i)
    q=chr(i-32)
    #print(t,q)
    if t not in inp and q not in inp:
        miss.append(i)
empt=[]
str1=''
for i in miss:
    str1=str1+chr(i)+', '
str1=str1[:len(str1)-2]
str1=str1+'.'
#prin
if miss==empt:
    print("Yes, the string is a pangram.")
else:
    print("No, the string is NOT a pangram. Missing letter(s) is(are)",str1)