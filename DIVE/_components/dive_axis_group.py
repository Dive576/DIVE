import copy
import numpy as np
import pandas as pd

class DIVEAxisGroup:
    """
    This class stores a group of axes that can be displayed by DIVE.
    """
    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['name', 'row_count', 'column_count', 'axis_names', 'rows', 'columns', 'row_spans', 'column_spans']}
        return copy.deepcopy(state) if as_copy else state

    def remove_axis(self, name):
        for i in reversed(range(len(self.axis_names))):
            if name == self.axis_names[i]:
                del self.axis_names[i]
                del self.rows[i]
                del self.columns[i]
                del self.row_spans[i]
                del self.column_spans[i]

    def set_state(self, axes, axis_group_names, state):
        attrs = self.get_state(as_copy=False)
        validate_grid = False

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in axis_group_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        for attr in ['row_count', 'column_count']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (int, np.integer)):
                    return '{} must be of type: int'.format(attr)
                elif not (1 <= attrs[attr] <= 20):
                    return '{} must be greater than or equal to 1 and less than or equal to 20.'.format(attr)
        for attr in ['axis_names', 'rows', 'columns', 'row_spans', 'column_spans']:
            if attr in state:
                validate_grid = True
                attrs[attr] = state[attr]
                if isinstance(attrs[attr], np.ndarray):
                    if attrs[attr].ndim > 1:
                        attrs[attr] = attrs[attr].flatten()
                elif not isinstance(attrs[attr], (list, tuple, pd.Series)):
                    return '{} must be one of the following types: list, tuple, numpy.ndarray, pandas.Series'.format(attr)
        if validate_grid:
            values = list(zip(attrs['axis_names'], attrs['rows'], attrs['columns'], attrs['row_spans'], attrs['column_spans']))
            attrs['axis_names'], attrs['rows'], attrs['columns'], attrs['row_spans'], attrs['column_spans'] = [], [], [], [], []
            grid = np.zeros((attrs['row_count'], attrs['column_count']), dtype='int')
            for value in values:
                if not isinstance(value[0], str):
                    return 'All values in axis_names must be of type: str'
                elif value[0] not in axes:
                    return '"{}" is not a valid axis name.'.format(value[0])
                elif not isinstance(value[1], (int, np.integer)):
                    return 'All values in rows must be of type: int'.format(value[1])
                elif not isinstance(value[2], (int, np.integer)):
                    return 'All values in columns must be of type: int'.format(value[2])
                elif not isinstance(value[3], (int, np.integer)):
                    return 'All values in row_spans must be of type: int'.format(value[3])
                elif not isinstance(value[4], (int, np.integer)):
                    return 'All values in column_spans must be of type: int'.format(value[4])
                attrs['axis_names'].append(value[0])
                row, col = int(np.clip(value[1], 0, attrs['row_count'] - 1)), int(np.clip(value[2], 0, attrs['column_count'] - 1))
                row_span, col_span = int(np.clip(value[3], 1, attrs['row_count'] - row)), int(np.clip(value[4], 1, attrs['column_count'] - col))
                attrs['rows'].append(row)
                attrs['columns'].append(col)
                attrs['row_spans'].append(row_span)
                attrs['column_spans'].append(col_span)
                grid[row:row+row_span, col:col+col_span] += 1
            if grid.max() > 1:
                return 'Cannot have multiple axes with the same row and column.'

        for attr in attrs:
            setattr(self, attr, attrs[attr])