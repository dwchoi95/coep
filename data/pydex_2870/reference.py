name = input()
cname = name.upper()
rname = cname[::-1]

if cname == rname:
    print('{} is a palindrome.'.format(name))
else:
    print('{} is NOT a palindrome.'.format(name))