import numpy as np
import pandas as pd
import re
import traceback

def apply_operation(op, left, right):
    """
    This function applies a logical operation to two values and returns the result.

    Parameters
    ----------
    op : str
        The logical operation to apply.
    left : object
        The value on the left side of the operation.
    right : object
        The value on the right side of the operation.

    Returns
    -------
    object
        The result of the operation on the two values.
    """
    if op == '>':
        return left > right
    elif op == '>=':
        return left >= right
    elif op == '==':
        return (left == right) | (pd.isnull(left) & pd.isnull(right))
    elif op == '!=':
        return (left != right) & (np.invert(pd.isnull(left)) | np.invert(pd.isnull(right)))
    elif op == '<=':
        return left <= right
    elif op == '<':
        return left < right
    else:
        raise Exception('Operation not recognized.')

def natural_order(text):
    """
    This function should be passed in as the "key" parameter
    when sorting an array of strings using a sorting function.
    When used, all of the strings in the array will be sorted in natural order.

    Parameters
    ----------
    text : str
        A string to sort.

    Returns
    -------
    list
        The values the sorting function will sort by.
    """
    return [int(c) if c.isdigit() else c for c in re.split('(\d+)', text)]

def print_error(err_msg):
    """
    This function is called when an invalid input is passed into one of the functions in DIVEWidget.
    It prints the error message describing the invalid input and the traceback information for the function
    call that was given invalid input.

    Parameters
    ----------
    err_msg : str
        The error message to print.
    """
    print('Traceback (most recent call last):\n{}{}\n'.format(''.join(traceback.format_stack()[:-2]), err_msg))

def safe_time_math(time, amount, add=True):
    """
    This function applies a mathematical operation (addition or subtraction) to a time
    value and ensures it won't go beyond the min/max values for pandas.Timestamps.

    Parameters
    ----------
    time : numeric, pandas.Timestamp with tz
        The time value.
    amount : numeric, pandas.Timedelta
        The amount to increment/decrement "time" by.
    add : bool (Default: True)
        Toggle whether "amount" will be added to "time".
        If False, "amount" will be subtracted from "time".

    Returns
    -------
    numeric, pandas.Timestamp with tz
        The incremented/decremented time value.
    """
    if isinstance(time, pd.Timestamp):
        edge_offset = pd.Timedelta(days=365)
        min_time, max_time = (pd.Timestamp.min + edge_offset).replace(nanosecond=0).tz_localize('UTC').tz_convert(time.tzinfo), (pd.Timestamp.max - edge_offset).replace(nanosecond=0).tz_localize('UTC').tz_convert(time.tzinfo)
        seconds = time.timestamp() + amount.total_seconds() if add else time.timestamp() - amount.total_seconds()
        if seconds < min_time.timestamp():
            return min_time
        elif seconds > max_time.timestamp():
            return max_time
    return time + amount if add else time - amount

def safe_tz_convert(time, timezone):
    """
    This function converts a pandas.Timestamp to a specific timezone and
    ensures it won't go beyond the min/max values for pandas.Timestamps.

    Parameters
    ----------
    time : None, numeric, pandas.Timestamp with tz
        The time value to convert.
    timezone : str
        The timezone the timestamp should be converted to.

    Returns
    -------
    None, numeric, pandas.Timestamp with tz
        The converted time value.
    """
    if isinstance(time, pd.Timestamp):
        edge_offset = pd.Timedelta(days=365)
        return np.clip(time, (pd.Timestamp.min + edge_offset).replace(nanosecond=0).tz_localize('UTC'), (pd.Timestamp.max - edge_offset).replace(nanosecond=0).tz_localize('UTC')).tz_convert(timezone)
    return time

def strftime(time, include_date=True, include_tz=False):
    """
    This function converts a time value to a string.

    Parameters
    ----------
    time : numeric, pandas.Timestamp with tz
        The time value to convert.
    include_date : bool (Default: True)
        If time is a pandas.Timestamp, include the date in the output string.
    include_tz : bool (Default: False)
        If time is a pandas.Timestamp, include the timezone name in the output string.

    Returns
    -------
    str
        A string representation of the time value.
    """
    if isinstance(time, pd.Timestamp):
        fmt = '{}%H:%M:%S.%f{}'.format('%m/%d/%Y ' if include_date else '', ' (' + str(time.tzinfo) + ')' if include_tz else '')
        return time.strftime(fmt)
    else:
        abs_time = abs(time)
        return '{}{}.{:06d}'.format('-' if time < 0 else '', int(abs_time // 1), int(abs_time * 1e6 - abs_time // 1 * 1e6))
