

S = input()

def is_kaibun(s):
    l = len(s)
    print('former', s[:int(l/2)])
    print('latter', s[:-(int(l/2))-1:-1])
    if s[:int(l/2)] == s[:-(int(l/2))-1:-1]:
        return True
    else:
        return False

if is_kaibun(S):
    if is_kaibun(S[:int((len(S)-1)/2)]):
        if is_kaibun(S[int((len(S)+3)/2)-1:]):
            print('Yes')
            exit()
print('No')