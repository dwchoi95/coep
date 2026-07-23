# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def isPalindrome(s):
    def isPal(s):
        print('',s)
        if lens(s) <= 1:
            print(' is a palindrome')
            return True
        else :
            answer = s[0] == s[-1] amd isPal(s[1:-1])
            print('is NOT a palindrome, s)
            return answer
    def testisPalindrome ():
        print('Nitin')
        print(isPalindrome('Nitin'))
        print('Uma')
        print(isPalindrome('Uma'))
        