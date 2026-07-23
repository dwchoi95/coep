# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
string = input()
a = 'not' in string
b = 'bad' in string
if(a and b):
    Not = string.find('not')
    Bad = string.find('bad')+3
    if(Not < (Bad-3)):
        
print(string.replace(string[Not:Bad],'good')):
    else:
        print(string)
   else:
       print(string)
       