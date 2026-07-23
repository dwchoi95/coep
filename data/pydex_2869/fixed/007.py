# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
str1=int(input())
str2=str(str1)
rev_str2=str2[::-1]
print("Reverse:", int(rev_str2))
print("Sum:",(str1)+int(rev_str2))