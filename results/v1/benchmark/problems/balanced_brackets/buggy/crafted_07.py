def balanced_brackets(s):
    t = "".join(c for c in s if c in "()[]{}")
    t = t.replace("()", "").replace("[]", "").replace("{}", "")
    return t == ""
