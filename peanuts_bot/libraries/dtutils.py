from dateutil.relativedelta import relativedelta


def format_relativedelta(rd: relativedelta) -> str:
    """Format a relativedelta object into a human-readable string."""
    parts = []
    if rd.years:
        parts.append(f"{rd.years} year{'s' if rd.years != 1 else ''}")
    if rd.months:
        parts.append(f"{rd.months} month{'s' if rd.months != 1 else ''}")
    if rd.days:
        parts.append(f"{rd.days} day{'s' if rd.days != 1 else ''}")
    if rd.hours:
        parts.append(f"{rd.hours} hour{'s' if rd.hours != 1 else ''}")
    if rd.minutes:
        parts.append(f"{rd.minutes} minute{'s' if rd.minutes != 1 else ''}")
    if rd.seconds:
        parts.append(f"{rd.seconds} second{'s' if rd.seconds != 1 else ''}")

    match len(parts):
        case 0:
            return "0 seconds"
        case 1:
            return parts[0]
        case _:
            except_last = ", ".join(parts[:-1])
            return f"{except_last}, and {parts[-1]}"
