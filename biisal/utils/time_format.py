# (c) @biisal
# (c) adarsh-goel
# (c) TechifyBots
import re

def get_readable_time(seconds: int) -> str:
    count = 0
    readable_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", " days"]
    while count < 4:
        count += 1
        if count < 3:
            remainder, result = divmod(seconds, 60)
        else:
            remainder, result = divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        readable_time += time_list.pop() + ", "
    time_list.reverse()
    readable_time += ": ".join(time_list)
    return readable_time


_DURATION_UNITS = {
    "d": 86400, "day": 86400, "days": 86400,
    "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
    "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
}
_DURATION_PATTERN = re.compile(
    r"(\d+)\s*(d|day|days|h|hr|hrs|hour|hours|m|min|mins|minute|minutes|s|sec|secs|second|seconds)",
    re.IGNORECASE,
)


def parse_duration(time_str) -> int:
    """
    Parses a duration string into total seconds.

    Accepts a plain number (treated as raw seconds, e.g. "3600"), or a
    human string using suffixes such as "45s", "30m", "2h", "1d" or a
    combination like "1h30m". Returns None if `time_str` is empty/None
    (meaning "no expiry"). Raises ValueError on an unrecognised format.
    """
    if time_str is None:
        return None
    time_str = str(time_str).strip().lower()
    if not time_str:
        return None

    if re.fullmatch(r"\d+", time_str):
        return int(time_str)

    matches = _DURATION_PATTERN.findall(time_str)
    if not matches:
        raise ValueError(f"Invalid duration: {time_str!r}")

    total = 0
    for value, unit in matches:
        total += int(value) * _DURATION_UNITS[unit]
    return total


def readable_duration(seconds: int) -> str:
    """
    Formats a number of seconds into a readable string such as
    "1 Hour 0 Minutes 0 Seconds" or "1 Day 2 Hours 3 Minutes 4 Seconds".
    """
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)

    def unit(value, singular):
        return f"{value} {singular if value == 1 else singular + 's'}"

    parts = []
    if days:
        parts.append(unit(days, "Day"))
    parts.append(unit(hours, "Hour"))
    parts.append(unit(minutes, "Minute"))
    parts.append(unit(secs, "Second"))
    return " ".join(parts)
