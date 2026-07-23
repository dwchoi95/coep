def flatten(nested):
    result = []
    for item in nested:
        if isinstance(item, list):
            return flatten(item)
        result.append(item)
    return result
