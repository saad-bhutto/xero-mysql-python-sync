import re
from datetime import datetime

def parse_xero_date(date_str):
    """
    Parses a Xero API date string and converts it to a MySQL DATETIME format.

    Args:
        date_str (str): The date string from the Xero API, e.g., "/Date(1741564800000)/".

    Returns:
        str: A string formatted as 'YYYY-MM-DD HH:MM:SS', or None if the input is invalid.
    """
    # Use a regular expression to find the number inside the parentheses.
    # The `\d+` matches one or more digits.
    match = re.search(r'\/Date\((\d+)', date_str)

    if match:
        # Extract the timestamp as a string and convert it to an integer.
        timestamp_ms = int(match.group(1))

        # The Xero timestamp is in milliseconds, so convert it to seconds.
        timestamp_s = timestamp_ms / 1000

        # Use the datetime module to convert the Unix timestamp to a datetime object.
        dt_object = datetime.fromtimestamp(timestamp_s)

        # Format the datetime object into the MySQL DATETIME string format.
        return dt_object.strftime('%Y-%m-%d %H:%M:%S')
    else:
        # Return None or raise an error if the format doesn't match.
        return None
