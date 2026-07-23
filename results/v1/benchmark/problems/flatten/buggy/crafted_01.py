def flatten(nested):
    result = []
    for item in nested:
        if isinstance(item, list):
            result.append(flatten(item))
        else:
            result.append(item)
    return result
