s = input().strip()
if not ('S' in s and 'N' in s) and ('S' in s or 'N' in s):
        print('No')
        exit()

if not ('E' in s and 'W' in s) and ('E' in s or 'W' in s):
        print('No')
        exit()

 
print('Yes')