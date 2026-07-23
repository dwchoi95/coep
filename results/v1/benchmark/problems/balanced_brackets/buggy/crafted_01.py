def balanced_brackets(s):
    return (s.count("(") == s.count(")")
            and s.count("[") == s.count("]")
            and s.count("{") == s.count("}"))
