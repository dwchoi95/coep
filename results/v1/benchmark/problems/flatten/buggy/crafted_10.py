def flatten(nested):
    result = []
    for ch in str(nested):
        if ch.isdigit():
            result.append(int(ch))
    return result
