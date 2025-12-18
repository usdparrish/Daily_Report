def fmt_number(value):
    """
    Executive-safe number formatter.

    - None -> 'N/A'
    - Int / float -> comma separated
    """
    if value is None:
        return "N/A"

    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)
