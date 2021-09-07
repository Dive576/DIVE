from .._utilities import helper_functions
import copy
import numpy as np
import pandas as pd

class DIVEData:
    """
    This class stores data that can be accessed by DIVE.
    """
    def __init__(self):
        self.filtered_idx = None

    def apply_filter(self, filter_idx):
        self.filtered_idx = np.logical_and(self.filtered_idx, filter_idx)

    def apply_selection(self, selection):
        self.selection = np.zeros(len(self.data.index), dtype='bool') if selection is None else selection

    def get_state(self, as_copy=True):
        attrs = ['name', 'data', 'id_field', 'time_field', 'selection']
        if as_copy:
            return {attr: getattr(self, attr, None) if attr == 'data' else copy.deepcopy(getattr(self, attr, None)) for attr in attrs}
        return {attr: getattr(self, attr, None) for attr in attrs}

    def get_valid_idx(self, current_time, hold_time=None):
        """
        Calculate the indices in data that are in the current time range.

        Parameters
        ----------
        current_time : None, numeric, pandas.Timestamp with tz
            The current time value for the animation.
        hold_time : None, numeric, pandas.Timedelta (Default: None)
            The number of seconds prior to the current time that should be included.
            If None, all points prior to the current time will be included.

        Returns
        -------
        numpy.ndarray
            The valid indices in data as a boolean array.
        """
        if current_time is not None and self.time_field is not None:
            valid_idx = self.filtered_idx.copy()
            time = self.data.loc[:, self.time_field]
            if hold_time is not None:
                valid_idx[:time.searchsorted(helper_functions.safe_time_math(current_time, hold_time, add=False))] = False
            valid_idx[time.searchsorted(current_time, side='right'):] = False
            return valid_idx
        return self.filtered_idx

    def reset_filter(self):
        self.filtered_idx = np.ones(len(self.data.index), dtype='bool')

    def reset_selection(self):
        self.selection = None

    def set_state(self, data_names, state):
        attrs = self.get_state(as_copy=False)
        data_changed = selection_changed = False

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in data_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'data' in state:
            attrs['data'] = state['data']
            if not isinstance(attrs['data'], pd.DataFrame):
                return 'data must be of type: pandas.DataFrame'
            elif attrs['data'].size == 0:
                return 'data must have at least one value.'
            elif not all(isinstance(val, str) for val in attrs['data'].columns):
                return 'All data column names must be of type: str'
            data_changed = True
        if 'id_field' in state or data_changed:
            if 'id_field' in state:
                attrs['id_field'] = state['id_field']
            if not isinstance(attrs['id_field'], (type(None), str)):
                return 'id_field must be one of the following types: None, str'
            elif attrs['id_field'] is not None and attrs['id_field'] not in attrs['data']:
                return '"{}" is not a valid field name.'.format(attrs['id_field'])
        if 'time_field' in state or data_changed:
            if 'time_field' in state:
                attrs['time_field'] = state['time_field']
            if not isinstance(attrs['time_field'], (type(None), str)):
                return 'time_field must be one of the following types: None, str'
            elif attrs['time_field'] is not None:
                if attrs['time_field'] not in attrs['data']:
                    return '"{}" is not a valid field name.'.format(attrs['time_field'])
                time_vals = attrs['data'].loc[:, attrs['time_field']]
                is_numeric = pd.api.types.is_numeric_dtype(time_vals)
                if not pd.api.types.is_datetime64tz_dtype(time_vals) and (not is_numeric or pd.api.types.is_complex_dtype(time_vals)):
                    return 'Time values must be one of the following types: numeric (not complex), pandas.Timestamp with tz'
                elif is_numeric and not np.isfinite(time_vals).all():
                    return 'Time values must all be finite.'
                elif not time_vals.is_monotonic_increasing:
                    return 'Time values must be monotonic increasing.'
        if 'selection' in state or data_changed:
            if 'selection' in state:
                attrs['selection'] = state['selection']
                selection_changed = True
            if attrs['selection'] is not None:
                if isinstance(attrs['selection'], np.ndarray):
                    if attrs['selection'].ndim > 1:
                        attrs['selection'] = attrs['selection'].flatten()
                elif isinstance(attrs['selection'], pd.Series):
                    attrs['selection'] = attrs['selection'].to_numpy()
                elif isinstance(attrs['selection'], (list, tuple)):
                    attrs['selection'] = np.array(attrs['selection'])
                else:
                    return 'selection must be one of the following types: None, list, tuple, numpy.ndarray, pandas.Series'
                if not pd.api.types.is_bool_dtype(attrs['selection']):
                    return 'Values in selection must be of type: bool'
                elif len(attrs['selection']) != len(attrs['data'].index):
                    return 'selection length doesn\'t match the length of the data.'
                attrs['selection'] = copy.deepcopy(attrs['selection'])

        for attr in attrs:
            setattr(self, attr, attrs[attr])

        if data_changed:
            self.reset_filter()
            if self.selection is not None and not selection_changed:
                self.apply_selection(None)

    @staticmethod
    def get_time_limits(data_objs, use_filter=True):
        """
        Calculate the minimum and maximum time values in all of the given data objects.

        Parameters
        ----------
        data_objs : dict
            The data objects to use.
        use_filter : bool (Default: True)
            Toggle whether minimum and maximum time should be calculated using filtered data.

        Returns
        -------
        None, numeric, pandas.Timestamp with tz
            The minimum time value across all of the data objects.
            Will be None if there aren't any time values.
        None, numeric, pandas.Timestamp with tz
            The maximum time value across all of the data objects.
            Will be None if there aren't any time values. 
        """
        min_time, max_time = None, None
        timestamp_time, numeric_time = False, False
        for data_obj in data_objs.values():
            if data_obj.time_field is None:
                data_min, data_max = None, None
            else:
                time_vals = data_obj.data.loc[data_obj.filtered_idx if use_filter else slice(None), data_obj.time_field]
                data_min, data_max = time_vals.min(), time_vals.max()
                data_min, data_max = None if pd.isna(data_min) else data_min, None if pd.isna(data_max) else data_max
            if data_min is not None:
                if isinstance(data_min, pd.Timestamp):
                    timestamp_time = True
                elif pd.api.types.is_numeric_dtype(type(data_min)):
                    numeric_time = True
                if timestamp_time and numeric_time:
                    return None, None
                if min_time is None:
                    min_time, max_time = data_min, data_max
                else:
                    if data_min < min_time: min_time = data_min
                    if data_max > max_time: max_time = data_max
        return min_time, max_time