# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
import string as s
l1 = list(s.ascii_lowercase)
l2 = []
text = input()
text = text.lower()
for i in range(26):
    if l1[i] not in text:
        l2.append(l1[i])
if len(l2) == 0:
    print('Yes, the string is a pangram.')
else:
    print('No, the string is NOT a pangram. Missing letter(s) is(are)', end = ' ')
    print(*l2, sep = ", ", end = '.')