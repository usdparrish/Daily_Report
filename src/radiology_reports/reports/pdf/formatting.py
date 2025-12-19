def fmt_number(value):
    """ Executive-safe number formatter.
    - None -> 'N/A'
    - Int / float -> comma separated
    """
    if value is None:
        return "N/A"
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)

def fmt_percent(value):
    """ Executive-safe percent formatter.
    - None -> 'N/A'
    - Float -> formatted with 1 decimal place and % sign, including sign for negatives
    """
    if value is None:
        return "N/A"
    try:
        return f"{value * 100:.1f}%"
    except (ValueError, TypeError):
        return str(value)
