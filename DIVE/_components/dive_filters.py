from .._utilities import helper_functions
import copy
import numpy as np
import pandas as pd

class DIVECustomFilter:
    """
    This class stores a custom filter group.
    """
    def __init__(self):
        self.values = {}

    def get_data_names(self):
        return list(self.values)

    def get_filter_indices(self, data_objs, data_subset):
        if data_subset is None:
            return copy.deepcopy(self.values)
        else:
            return {key: copy.deepcopy(value) for key, value in self.values.items() if key in data_subset}

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['name', 'values', 'enabled']}
        state['values'] = dict(sorted(state['values'].items(), key=lambda item: helper_functions.natural_order(item[0])))
        return copy.deepcopy(state) if as_copy else state

    def remove_data(self, name):
        if name is None:
            self.values = {}
        else:
            self.values.pop(name, None)

    def set_state(self, data_objs, custom_filter_names, state):
        attrs = self.get_state(as_copy=False)

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in custom_filter_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'values' in state:
            attrs['values'] = state['values']
            if not isinstance(attrs['values'], dict):
                return 'values must be of type: dict'
            values = {}
            for key, value in attrs['values'].items():
                if not isinstance(key, str):
                    return 'data names in values must be of type: str'
                elif key not in data_objs:
                    return '"{}" is not a valid data name.'.format(key)
                if isinstance(value, np.ndarray):
                    if value.ndim > 1:
                        value = value.flatten()
                elif isinstance(value, pd.Series):
                    value = value.to_numpy()
                elif isinstance(value, (list, tuple)):
                    value = np.array(value)
                else:
                    return 'Each value in values must be one of the following types: list, tuple, numpy.ndarray, pandas.Series'
                if not pd.api.types.is_bool_dtype(value):
                    return 'Array for "{}" must be of type: bool'.format(key)
                elif len(value) != len(data_objs[key].data.index):
                    return 'Array length for "{}" doesn\'t match the length of the data.'.format(key)
                values[key] = copy.deepcopy(value)
            attrs['values'] = values
        if 'enabled' in state:
            attrs['enabled'] = state['enabled']
            if not isinstance(attrs['enabled'], (bool, np.bool_)):
                return 'enabled must be of type: bool'

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def validate_data(self, data_objs, name):
        err_msg = self.set_state(data_objs, [], {'values': self.values})
        if err_msg is not None:
            self.remove_data(name)

class DIVEIDFilter:
    """
    This class stores an ID filter group.
    """
    def __init__(self):
        self.values = {}

    def get_data_names(self):
        return list(self.values)

    def get_filter_indices(self, data_objs, data_subset):
        filter_idx = {}
        for data_name, value in self.values.items():
            if data_subset is None or data_name in data_subset:
                id_vals = data_objs[data_name].data.loc[:, data_objs[data_name].id_field]
                id_dtype = data_objs[data_name].data.dtypes.at[data_objs[data_name].id_field]
                if not pd.api.types.is_numeric_dtype(id_dtype) and not pd.api.types.is_datetime64tz_dtype(id_dtype):
                    id_vals = id_vals.astype('str')
                    value = pd.Series(value, dtype='str')
                filter_idx[data_name] = id_vals.isin(value).to_numpy()
        return filter_idx

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['name', 'values', 'enabled']}
        state['values'] = dict(sorted(state['values'].items(), key=lambda item: helper_functions.natural_order(item[0])))
        return copy.deepcopy(state) if as_copy else state

    def remove_data(self, name):
        if name is None:
            self.values = {}
        else:
            self.values.pop(name, None)

    def set_state(self, data_objs, id_filter_names, state):
        attrs = self.get_state(as_copy=False)

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in id_filter_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'values' in state:
            attrs['values'] = state['values']
            if not isinstance(attrs['values'], dict):
                return 'values must be of type: dict'
            values = {}
            for key, value in attrs['values'].items():
                if not isinstance(key, str):
                    return 'data names in values must be of type: str'
                elif key not in data_objs:
                    return '"{}" is not a valid data name.'.format(key)
                elif data_objs[key].id_field is None:
                    return 'Data object "{}" doesn\'t have an ID field.'.format(key)
                if isinstance(value, np.ndarray):
                    if value.ndim > 1:
                        value = value.flatten()
                elif isinstance(value, pd.Series):
                    value = value.to_numpy()
                elif not isinstance(value, (list, tuple)):
                    return 'Each value in values must be one of the following types: list, tuple, numpy.ndarray, pandas.Series'
                values[key] = copy.deepcopy(value)
            attrs['values'] = values
        if 'enabled' in state:
            attrs['enabled'] = state['enabled']
            if not isinstance(attrs['enabled'], (bool, np.bool_)):
                return 'enabled must be of type: bool'

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def validate_data(self, data_objs, name):
        err_msg = self.set_state(data_objs, [], {'values': self.values})
        if err_msg is not None:
            self.remove_data(name)

class DIVEValueFilter:
    """
    This class stores a value filter group.
    """
    def __init__(self):
        self.data_names = []

    def calculate_filter_idx(self, data_objs, filters, data_names, is_top):
        """
        Loop through every logical filter item recursively, calculate
        the indices of its filter items, and merge them accordingly.

        Parameters
        ----------
        data_objs : dict
            The data objects that have been added to DIVE.
        filters : list
            The logical filter item to loop through.
        data_names : list
            The names of the data objects that indices should be returned for.
        is_top : bool
            Indicator for whether the current logical filter item is the topmost one.

        Returns
        -------
        dict
            The indices for the data objects specified by "data_names".
        """
        valid_idx = {}
        if self.id_filter is not None:
            data_names = [data_name for data_name in data_names if data_objs[data_name].id_field is not None]
        if len(data_names) == 0:
            return valid_idx
        logical_op = np.logical_and if filters[0] == 'AND' else np.logical_or
        for f in filters[1:]:
            if f[0] in ['AND', 'OR']: # Logical item
                data_idx = self.calculate_filter_idx(data_objs, f, data_names, False)
                for data_name in data_idx:
                    valid_idx[data_name] = logical_op(valid_idx[data_name], data_idx[data_name]) if data_name in valid_idx else data_idx[data_name]
            else: # Filter item
                comparison_op, filter_data_name, filter_field_name, filter_value = f

                # Don't calculate filter if there aren't any data objects that it can be applied to
                if filter_data_name not in data_names:
                    if data_objs[filter_data_name].time_field is None:
                        continue
                    filter_is_datetime = pd.api.types.is_datetime64tz_dtype(data_objs[filter_data_name].data.dtypes.at[data_objs[filter_data_name].time_field])
                    all_invalid = True
                    for data_name in data_names:
                        if data_objs[data_name].time_field is not None and filter_is_datetime == pd.api.types.is_datetime64tz_dtype(data_objs[data_name].data.dtypes.at[data_objs[data_name].time_field]):
                            all_invalid = False
                            break
                    if all_invalid:
                        continue

                # Calculate filter
                filter_data = data_objs[filter_data_name].data.loc[:, filter_field_name]
                try:
                    idx = helper_functions.apply_operation(comparison_op, filter_data, filter_value)
                except:
                    idx = helper_functions.apply_operation(comparison_op, filter_data.astype('str'), str(filter_value))

                # Map filter to each data object
                time_bins = None
                for data_name in data_names:
                    data_idx = None
                    if data_name == filter_data_name:
                        data_idx = idx.to_numpy()
                    elif data_objs[data_name].time_field is not None and data_objs[filter_data_name].time_field is not None:
                        data_time = data_objs[data_name].data.loc[:, data_objs[data_name].time_field]
                        filter_time = data_objs[filter_data_name].data.loc[:, data_objs[filter_data_name].time_field]
                        if (pd.api.types.is_numeric_dtype(data_time) and pd.api.types.is_numeric_dtype(filter_time)) or (pd.api.types.is_datetime64tz_dtype(data_time) and pd.api.types.is_datetime64tz_dtype(filter_time)):
                            if time_bins is None:
                                diff_idx = np.diff(idx.astype('int'), prepend=0)
                                if pd.api.types.is_datetime64tz_dtype(filter_time):
                                    filter_time = filter_time.view('int64') / 1e9
                                start_time = filter_time.loc[diff_idx == 1]
                                end_time = filter_time.loc[diff_idx == -1]
                                time_bins = np.zeros(start_time.size * 2, dtype=start_time.dtype)
                                time_bins[0::2] = start_time
                                if start_time.size > end_time.size:
                                    end_time = end_time.append(pd.Series([np.inf]))
                                if end_time.size > 0:
                                    time_bins[1::2] = end_time
                            if pd.api.types.is_datetime64tz_dtype(data_time):
                                data_time = data_time.view('int64') / 1e9
                            bin_num = np.digitize(data_time, time_bins)
                            data_idx = (bin_num % 2 == 1).astype('bool')
                    if data_idx is not None:
                        valid_idx[data_name] = logical_op(valid_idx[data_name], data_idx) if data_name in valid_idx else data_idx

        # Apply ID filter
        if is_top and self.id_filter is not None:
            for data_name in valid_idx:
                id_vals = data_objs[data_name].data.loc[:, data_objs[data_name].id_field]
                group = pd.Series(valid_idx[data_name]).groupby(id_vals.values, sort=False)
                group = group.any() if self.id_filter in ['any match', 'all mismatch'] else group.all()
                valid_ids = group.index[group] if self.id_filter in ['any match', 'all match'] else group.index[~group]
                valid_idx[data_name] = id_vals.isin(valid_ids).to_numpy()

        return valid_idx

    def get_data_names(self):
        return self.data_names

    def get_filter_indices(self, data_objs, data_subset):
        data_names = self.data_names if data_subset is None else [data_name for data_name in self.data_names if data_name in data_subset]
        return self.calculate_filter_idx(data_objs, self.filters, data_names, True)

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['name', 'data_names', 'filters', 'id_filter', 'enabled']}
        state['data_names'] = sorted(state['data_names'], key=helper_functions.natural_order)
        return copy.deepcopy(state) if as_copy else state

    def remove_data(self, name):
        if name is None:
            self.data_names = []
        elif name in self.data_names:
            self.data_names.remove(name)
        self.filters, _ = self.remove_data_filters(name, self.filters)

    def remove_data_filters(self, name, filters):
        if filters[0] in ['AND', 'OR']:
            output = [filters[0]]
            for filter_val in filters[1:]:
                item, ok = self.remove_data_filters(name, filter_val)
                if ok:
                    output.append(item)
            return output, True
        else:
            return filters, (False if filters[1] == name or name is None else True)

    def set_state(self, data_objs, value_filter_names, state):
        attrs = self.get_state(as_copy=False)

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in value_filter_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'data_names' in state:
            attrs['data_names'] = state['data_names']
            if isinstance(attrs['data_names'], np.ndarray):
                if attrs['data_names'].ndim > 1:
                    attrs['data_names'] = attrs['data_names'].flatten()
            elif not isinstance(attrs['data_names'], (list, tuple, pd.Series)):
                return 'data_names must be one of the following types: list, tuple, numpy.ndarray, pandas.Series'
            data_names = set()
            for data_name in attrs['data_names']:
                if not isinstance(data_name, str):
                    return 'All values in data_names must be of type: str'
                elif data_name not in data_objs:
                    return '"{}" is not a valid data name.'.format(data_name)
                data_names.add(data_name)
            attrs['data_names'] = list(data_names)
        if 'filters' in state:
            attrs['filters'], err_msg = self.validate_filters(data_objs, state['filters'], True)
            if err_msg is not None:
                return err_msg
        if 'id_filter' in state:
            attrs['id_filter'] = state['id_filter']
            if not isinstance(attrs['id_filter'], (type(None), str)):
                return 'id_filter must be one of the following types: None, str'
            elif attrs['id_filter'] is not None:
                attrs['id_filter'] = attrs['id_filter'].lower()
                if attrs['id_filter'] not in ['any match', 'all match', 'any mismatch', 'all mismatch']:
                    return 'id_filter must be one of the following: "any match", "all match", "any mismatch", "all mismatch"'
        if 'enabled' in state:
            attrs['enabled'] = state['enabled']
            if not isinstance(attrs['enabled'], (bool, np.bool_)):
                return 'enabled must be of type: bool'

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def validate_data(self, data_objs, name):
        err_msg = self.set_state(data_objs, [], {'filters': self.filters})
        if err_msg is not None:
            self.filters, _ = self.remove_data_filters(name, self.filters)

    def validate_filters(self, data_objs, filters, is_top):
        """
        Loop through every filter item recursively and
        validate that its input parameters are correct.

        Parameters
        ----------
        data_objs : dict
            The data objects that have been added to DIVE.
        filters : list
            The filter item to validate.
        is_top : bool
            Indicator for whether the current filter item is the topmost one.

        Returns
        -------
        None, list
            The filter item that was validated.
        None, str
            The error message if an input parameter is invalid.
        """
        if isinstance(filters, np.ndarray):
            if filters.ndim > 1:
                filters = filters.flatten()
        elif isinstance(filters, pd.Series):
            filters = filters.to_numpy()
        elif not isinstance(filters, (list, tuple)):
            return None, 'Arrays in filters must be one of the following types: list, tuple, numpy.ndarray, pandas.Series'
        if len(filters) == 0:
            return None, 'filters cannot contain empty arrays.'
        elif is_top and filters[0] not in ['AND', 'OR']:
            return None, 'The first element in filters must be one of the following: "AND", "OR"'
        elif filters[0] in ['AND', 'OR']:
            output = [filters[0]]
            for filter_val in filters[1:]:
                item, err_msg = self.validate_filters(data_objs, filter_val, False)
                if err_msg is not None:
                    return None, err_msg
                output.append(item)
            return output, None
        elif filters[0] in ['>', '>=', '==', '!=', '<=', '<']:
            if len(filters) < 4:
                return None, 'Not enough elements in filter array that starts with "{}". Filter array should have the format: ["{}", data_name, field_name, comparison_value]'.format(filters[0], filters[0])
            elif not isinstance(filters[1], str):
                return None, 'Data names must be of type: str'
            elif filters[1] not in data_objs:
                return None, '"{}" is not a valid data name.'.format(filters[1])
            elif not isinstance(filters[2], str):
                return None, "Field names must be of type: str"
            elif filters[2] not in data_objs[filters[1]].data:
                return None, '"{}" is not a valid field name for data object "{}".'.format(filters[2], filters[1])
            data_dtype = data_objs[filters[1]].data.dtypes.at[filters[2]]
            if pd.api.types.is_numeric_dtype(data_dtype):
                if not pd.api.types.is_numeric_dtype(type(filters[3])):
                    return None, '"{}" cannot be compared with field "{}" in data object "{}" because it isn\'t numeric.'.format(filters[3], filters[2], filters[1])
            elif pd.api.types.is_datetime64tz_dtype(data_dtype):
                if not (isinstance(filters[3], pd.Timestamp) and filters[3].tzinfo is not None):
                    return None, '"{}" cannot be compared with field "{}" in data object "{}" because it isn\'t a pandas.Timestamp with tz.'.format(filters[3], filters[2], filters[1])
            return [filters[0], filters[1], filters[2], copy.deepcopy(filters[3])], None
        else:
            return None, 'The first element in each array of filters must be one of the following: "AND", "OR", ">", ">=", "==", "!=", "<=", "<"'

class DIVEFilters:
    """
    This class stores filter groups for the data objects that have been added to DIVE.
    """
    def __init__(self):
        self.custom = {}
        self.ID = {}
        self.value = {}

    def add_filter(self, data_objs, filter_type, state):
        if filter_type == 'custom':
            filter_obj = DIVECustomFilter()
        elif filter_type == 'ID':
            filter_obj = DIVEIDFilter()
        elif filter_type == 'value':
            filter_obj = DIVEValueFilter()
        filter_objs = getattr(self, filter_type)
        err_msg = filter_obj.set_state(data_objs, list(filter_objs), state)
        if err_msg is None:
            filter_objs[filter_obj.name] = filter_obj
        return err_msg

    def edit_filter(self, data_objs, filter_type, filter_name, state):
        filter_state, err_msg = None, None
        filter_objs = getattr(self, filter_type)
        if not isinstance(filter_name, str):
            err_msg = 'filter_name must be of type: str'
        elif filter_name in filter_objs:
            filter_obj = filter_objs[filter_name]
            filter_names = [name for name in filter_objs if name != filter_name]
            err_msg = filter_obj.set_state(data_objs, filter_names, state)
            if err_msg is None:
                filter_state = filter_obj.get_state(as_copy=False)
        else:
            err_msg = '"{}" is not a valid {} filter group name.'.format(filter_name, filter_type)
        return filter_state, err_msg

    def get_data_names(self, filter_type, name):
        return getattr(self, filter_type)[name].get_data_names()

    def get_filter(self, filter_type, name):
        filters, err_msg = None, None
        filter_objs = getattr(self, filter_type)
        if not isinstance(name, (type(None), str)):
            err_msg = 'name must be one of the following types: None, str'
        elif name is None:
            filter_names = sorted(list(filter_objs), key=helper_functions.natural_order)
            filters = [filter_objs[filter_name].get_state() for filter_name in filter_names]
        elif name in filter_objs:
            filters = filter_objs[name].get_state()
        else:
            err_msg = '"{}" is not a valid {} filter group name.'.format(name, filter_type)
        return filters, err_msg

    def get_filter_indices(self, data_objs, filter_type, name, and_filters, data_subset):
        filter_idx, err_msg = {}, None
        if filter_type is None:
            logical_op = np.logical_and if and_filters else np.logical_or
            for filter_objs in [self.custom, self.ID, self.value]:
                for filter_obj in filter_objs.values():
                    if filter_obj.enabled:
                        idx = filter_obj.get_filter_indices(data_objs, data_subset)
                        for data_name in idx:
                            filter_idx[data_name] = logical_op(filter_idx[data_name], idx[data_name]) if data_name in filter_idx else idx[data_name]
            for data_name in sorted(list(filter_idx), key=helper_functions.natural_order):
                filter_idx[data_name] = filter_idx.pop(data_name)
        else:
            filter_objs = getattr(self, filter_type)
            if not isinstance(name, (type(None), str)):
                err_msg = 'name must be one of the following types: None, str'
            elif name is None:
                filter_names = sorted(list(filter_objs), key=helper_functions.natural_order)
                filter_idx = [{'name': filter_name, 'indices': filter_objs[filter_name].get_filter_indices(data_objs, data_subset)} for filter_name in filter_names]
            elif name in filter_objs:
                filter_idx = filter_objs[name].get_filter_indices(data_objs, data_subset)
            else:
                err_msg = '"{}" is not a valid {} filter group name.'.format(name, filter_type)
        return filter_idx, err_msg

    def remove_data(self, name):
        for filter_objs in [self.custom, self.ID, self.value]:
            for filter_obj in filter_objs.values():
                filter_obj.remove_data(name)

    def remove_filter(self, filter_type, name):
        filters = getattr(self, filter_type)
        if not isinstance(name, (type(None), str)):
            return 'name must be one of the following types: None, str'
        elif name is None:
            setattr(self, filter_type, {})
        elif name in filters:
            del filters[name]
            return None
        else:
            return '"{}" is not a valid {} filter group name.'.format(name, filter_type)

    def validate_data(self, data_objs, name):
        for filter_objs in [self.custom, self.ID, self.value]:
            for filter_obj in filter_objs.values():
                filter_obj.validate_data(data_objs, name)
