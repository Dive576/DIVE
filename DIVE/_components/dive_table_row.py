from .._utilities import helper_functions
import copy
import numpy as np
import pandas as pd
import vispy.color as vpcolor

class DIVETableRow:
    """
    This class stores information for a table row that can be displayed by the table in DIVE.
    """
    def get_row_data(self, data_objs, change_idx, current_time, timezone, change_duration):
        """
        Return the text and color to use for this row.

        Parameters
        ----------
        data_objs : dict
            The data objects currently in DIVE.
        change_idx : dict
            The valid data indices for the current time value.
            It is used to avoid recalculating the indices when updating
            table rows in a loop.
        current_time : None, numeric, pandas.Timestamp with tz
            The current time value in DIVE.
        timezone : str
            The current timezone in DIVE.
        change_duration : numeric, pandas.Timedelta
            The number of seconds prior to the current time that should be examined
            for color criteria that use "change".

        Returns
        -------
        str
            The text to use for this row.
        array
            The color to use for this row\'s background color.
        array
            The color to use for this row\'s text color.
        """
        data_obj = data_objs[self.data_name]
        if self.data_name not in change_idx:
            change_idx[self.data_name] = [None, data_obj.get_valid_idx(current_time)] # [(change_start_idx, change_end_idx), valid_idx]
        valid_idx = change_idx[self.data_name][1]
        has_data = np.any(valid_idx)
        if not has_data:
            val = ''
        elif self.operation == 'latest':
            val = data_obj.data.loc[valid_idx, self.field_name].iat[-1]
        else:
            val = data_obj.data.loc[valid_idx, self.field_name].apply(self.operation)
        text = helper_functions.strftime(helper_functions.safe_tz_convert(val, timezone), include_tz=True) if isinstance(val, pd.Timestamp) and val.tzinfo is not None else str(val)
        color_val = []
        if has_data:
            for color_operation, criteria_value, color_str in self.color_criteria:
                if color_operation != 'change':
                    try:
                        valid = helper_functions.apply_operation(color_operation, val, criteria_value)
                    except:
                        valid = helper_functions.apply_operation(color_operation, str(val), str(criteria_value))
                    if valid:
                        color_val.append(vpcolor.Color(color=color_str).RGB)
                elif color_operation == 'change' and current_time is not None:
                    time_vals = data_obj.data.loc[valid_idx, data_obj.time_field]
                    if current_time >= time_vals.iloc[0]:
                        if change_idx[self.data_name][0] is None:
                            change_idx[self.data_name][0] = time_vals.searchsorted(helper_functions.safe_time_math(current_time, change_duration, add=False)), time_vals.searchsorted(current_time, side='right')
                        s, e = change_idx[self.data_name][0]
                        if s != e: # Both values are in range
                            if s == 0: # First value
                                color_val.append(vpcolor.Color(color=color_str).RGB)
                            elif data_obj.data.loc[valid_idx, self.field_name].iloc[s - 1:e].nunique() > 1: # Value has changed
                                color_val.append(vpcolor.Color(color=color_str).RGB)
        criteria_count = len(color_val)
        row_color, text_color = None, None
        if criteria_count > 0:
            row_color = np.array(color_val).sum(axis=0) / criteria_count if self.blend_colors else color_val[-1]
            # Determine text color that is appropriate for the row color
            text_color = (row_color / 255)**2.2
            text_color = [0, 0, 0] if 0.2126 * text_color[0] + 0.7151 * text_color[1] + 0.0721 * text_color[2] > 0.18 else [255, 255, 255]
        return text, row_color, text_color

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['data_name', 'field_name', 'label', 'operation', 'color_criteria', 'blend_colors']}
        return copy.deepcopy(state) if as_copy else state

    def set_state(self, data_objs, state):
        attrs = self.get_state(as_copy=False)
        data_changed = field_changed = operation_changed = False

        # Validate parameters
        if 'data_name' in state:
            attrs['data_name'] = state['data_name']
            if not isinstance(attrs['data_name'], str):
                return 'data_name must be of type: str'
            elif attrs['data_name'] not in data_objs:
                return '"{}" is not a valid data name.'.format(attrs['data_name'])
            data_changed = True
        if 'field_name' in state or data_changed:
            if 'field_name' in state:
                attrs['field_name'] = state['field_name']
                field_changed = True
            if not isinstance(attrs['field_name'], str):
                return 'field_name must be of type: str'
            elif attrs['field_name'] not in data_objs[attrs['data_name']].data:
                return '"{}" is not a valid field name for data object "{}".'.format(attrs['field_name'], attrs['data_name'])
        if 'label' in state:
            attrs['label'] = state['label']
            if not isinstance(attrs['label'], str):
                return 'label must be of type: str'
        if 'operation' in state or data_changed or field_changed:
            if 'operation' in state:
                attrs['operation'] = state['operation']
                operation_changed = True
            if not isinstance(attrs['operation'], str):
                return 'operation must be of type: str'
            elif attrs['operation'] != 'latest':
                try:
                    data_objs[attrs['data_name']].data.loc[:, attrs['field_name']].apply(attrs['operation'])
                except:
                    return 'Cannot perform operation "{}" on field "{}" in data object, "{}".'.format(attrs['operation'], attrs['field_name'], attrs['data_name'])
        if 'color_criteria' in state or data_changed or field_changed or operation_changed:
            if 'color_criteria' in state:
                attrs['color_criteria'] = state['color_criteria']
            if isinstance(attrs['color_criteria'], np.ndarray):
                if attrs['color_criteria'].ndim > 1:
                    attrs['color_criteria'] = attrs['color_criteria'].flatten()
            elif isinstance(attrs['color_criteria'], pd.Series):
                attrs['color_criteria'] = attrs['color_criteria'].to_numpy()
            elif not isinstance(attrs['color_criteria'], (list, tuple)):
                return 'color_criteria must be one of the following types: list, tuple, numpy.ndarray, pandas.Series'
            color_criteria = []
            for criteria in attrs['color_criteria']:
                if isinstance(criteria, np.ndarray):
                    if criteria.ndim > 1:
                        criteria = criteria.flatten()
                elif isinstance(criteria, pd.Series):
                    criteria = criteria.to_numpy()
                elif not isinstance(criteria, (list, tuple)):
                    return 'Arrays in color_criteria must be one of the following types: list, tuple, numpy.ndarray, pandas.Series'
                if len(criteria) < 3:
                    return 'Arrays in color_criteria must contain 3 elements.'
                elif not isinstance(criteria[0], str):
                    return 'The first element in a color_criteria array must be of type: str'
                comparison_op = criteria[0].lower()
                if comparison_op not in ['>', '>=', '==', '!=', '<=', '<', 'change']:
                    return 'The first element in a color_criteria array must be one of the following: ">", ">=", "==", "!=", "<=", "<", "change"'
                elif comparison_op == 'change':
                    if data_objs[attrs['data_name']].time_field is None:
                        return 'The first element in a color_criteria array cannot be "change" if the data object doesn\'t have a time field.'
                    elif attrs['operation'] != 'latest':
                        return 'The first element in a color_criteria array cannot be "change" if "operation" isn\'t "latest".'
                elif comparison_op != 'change':
                    data_dtype = data_objs[attrs['data_name']].data.dtypes.at[attrs['field_name']]
                    if pd.api.types.is_numeric_dtype(data_dtype):
                        if not pd.api.types.is_numeric_dtype(type(criteria[1])):
                            return '"{}" cannot be compared with field "{}" in data object "{}" because it isn\'t numeric.'.format(criteria[1], attrs['field_name'], attrs['data_name'])
                    elif pd.api.types.is_datetime64tz_dtype(data_dtype):
                        if not (isinstance(criteria[1], pd.Timestamp) and criteria[1].tzinfo is not None):
                            return '"{}" cannot be compared with field "{}" in data object "{}" because it isn\'t a pandas.Timestamp with tz.'.format(criteria[1], attrs['field_name'], attrs['data_name'])
                if not isinstance(criteria[2], str):
                    return 'The third element in a color_criteria array must be of type: str'
                try:
                    vpcolor.Color(criteria[2])
                except:
                    return '"{}" is not a valid color string.'.format(criteria[2])
                color_criteria.append([comparison_op, copy.deepcopy(criteria[1]), criteria[2]])
            attrs['color_criteria'] = color_criteria
        if 'blend_colors' in state:
            attrs['blend_colors'] = state['blend_colors']
            if not isinstance(attrs['blend_colors'], (bool, np.bool_)):
                return 'blend_colors must be of type: bool'

        for attr in attrs:
            setattr(self, attr, attrs[attr])