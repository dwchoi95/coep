def regtri(a, b, c):
    if a == b and b == c:
        return 'Yes'
    else:
        return  'No'
 
a, b, c = (int(i) for i in input().split())
print(regtri(a, b, c))