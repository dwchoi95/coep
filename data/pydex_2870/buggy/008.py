# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
name = str(input())
c = name.casefold()
reverse = c[::-1]
print( c == reverse)
if(reverse == c):
    print(name , 'is a palindrome')
    else:
        print(name , 'is NOT a palindrome')