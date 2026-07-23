# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a = int(input())
b = str(a)
c = b[::-1]
d = int(c)
print('Reverse:', d)
X = a + d
print('Sum:', X )