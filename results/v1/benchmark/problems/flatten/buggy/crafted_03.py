def flatten(nested):
    if nested == []:
        return []
    if isinstance(nested[0], list):
        return flatten(nested[0]) + flatten(nested[1:])
    return [nested[0]] + nested[1:]
