import numpy as np
import pandas as pd
import vispy.color as vpcolor

def validate_color(name, color):
    if not isinstance(color, str):
        return '{} must be of type: str'.format(name)
    try:
        vpcolor.Color(color)
    except:
        return '{} must be either a hex str (such as "#ff0000") or the name of a CSS color.'.format(name)

def validate_colormap(name, colormap):
    if not isinstance(colormap, str):
        return '{} must be of type: str'.format(name)
    try:
        vpcolor.get_colormap(colormap)
    except:
        return '{} must be one of the following (or a matplotlib colormap name if the python module "matplotlib" is installed): {}'.format(name, str(list(vpcolor.get_colormaps()))[1:-1])

def validate_field(name, data_objs, data_name, field_name, required_names=[], optional_names=[], size_names=[]):
    if name in required_names and not isinstance(field_name, str):
        return '{} must be of type: str'.format(name)
    elif name in optional_names and not isinstance(field_name, (type(None), str)):
        return '{} must be one of the following types: None, str'.format(name)
    elif field_name is not None:
        if data_name is None:
            return 'data_name is required when {} is not None.'.format(name)
        elif field_name not in data_objs[data_name].data:
            return '"{}" is not a valid field name for data object "{}".'.format(field_name, data_name)
        elif name in size_names:
            data = data_objs[data_name].data.loc[:, field_name]
            if not pd.api.types.is_numeric_dtype(data):
                return '{} must have numeric values.'.format(name)
            elif not np.isfinite(data).all():
                return '{} must have finite values.'.format(name)
            elif data.min() < 0:
                return '{} must have values greater than or equal to 0.'.format(name)

def validate_unit(name, unit_reg, unit):
    if unit_reg is None:
        return None, None
    elif isinstance(unit, np.ndarray):
        if unit.ndim > 1:
            unit = unit.flatten()
    elif isinstance(unit, pd.Series):
        unit = unit.to_numpy()
    elif not isinstance(unit, (type(None), list, tuple)):
        return None, '{} must be one of the following types: None, list, tuple, numpy.ndarray, pandas.Series'.format(name)
    if unit is None:
        return unit, None
    else:
        if len(unit) < 2:
            return None, '{} must contain two elements.'.format(name)
        elif not isinstance(unit[0], str) or not isinstance(unit[1], str):
            return None, '{} must contain elements of type: str'.format(name)
        try:
            unit_reg.Quantity(unit[0]).to(unit[1])
        except:
            return None, '"{}" to "{}" is not a valid unit conversion for the python module "pint".'.format(unit[0], unit[1])
        return (unit[0], unit[1]), None