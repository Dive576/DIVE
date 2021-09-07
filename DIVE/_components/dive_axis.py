from .._plotting import artists
from .._utilities import helper_functions, validators
import copy
import numpy as np

class DIVEAxis:
    """
    This class stores an axis that can be displayed by DIVE.
    """
    def __init__(self):
        self.artists = {}

    def add_artist(self, data_objs, artist_type, unit_reg, state):
        artist_obj = artists.create_artist(artist_type)
        err_msg = artist_obj.set_state(data_objs, self.axis_type, list(self.artists), unit_reg, state)
        if err_msg is None:
            self.artists[artist_obj.name] = artist_obj
        return err_msg

    def edit_artist(self, data_objs, name, unit_reg, state):
        err_msg = None
        if not isinstance(name, str):
            err_msg = 'name must one of type: str'
        elif name in self.artists:
            err_msg = self.artists[name].set_state(data_objs, self.axis_type, list(self.artists), unit_reg, state)
        else:
            err_msg = '"{}" is not a valid artist name.'.format(name)
        return err_msg

    def get_artist(self, name):
        artist = err_msg = None
        if not isinstance(name, (type(None), str)):
            err_msg = 'name must one of the following types: None, str'
        elif name is None:
            artist_names = sorted(list(self.artists), key=helper_functions.natural_order)
            artist = [self.artists[artist_name].get_state() for artist_name in artist_names]
        elif name in self.artists:
            artist = self.artists[name].get_state()
        else:
            err_msg = '"{}" is not a valid artist name.'.format(name)
        return artist, err_msg

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['name', 'axis_type', 'title', 'x_grid', 'y_grid', 'z_grid', 'x_label', 'y_label', 'z_label', 'x_unit', 'y_unit', 'z_unit', 'time_autoscale']}
        return copy.deepcopy(state) if as_copy else state

    def remove_artist(self, name):
        err_msg = None
        if not isinstance(name, (type(None), str)):
            err_msg = 'name must one of the following types: None, str'
        elif name is None:
            self.artists = {}
        elif name in self.artists:
            del self.artists[name]
        else:
            err_msg = '"{}" is not a valid artist name.'.format(name)
        return err_msg

    def remove_data(self, name):
        if name is None:
            invalid_artists = [artist_name for artist_name in self.artists if self.artists[artist_name] is not None]
        else:
            invalid_artists = [artist_name for artist_name in self.artists if self.artists[artist_name].data_name == name]
        for artist_name in invalid_artists:
            self.artists.pop(artist_name)

    def set_state(self, axis_names, unit_reg, state):
        attrs = self.get_state(as_copy=False)

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in axis_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'axis_type' in state and attrs['axis_type'] is None:
            attrs['axis_type'] = state['axis_type']
            if not isinstance(attrs['axis_type'], str):
                return 'axis_type must be of type: str'
            attrs['axis_type'] = attrs['axis_type'].lower()
            if attrs['axis_type'] not in ['2d', '3d']:
                return 'axis_type must be one of the following: "2d", "3d"'
        for attr in ['x_grid', 'y_grid', 'z_grid']:
            if attr in state:
                if attr == 'z_grid' and attrs['axis_type'] == '2d':
                    attrs['z_grid'] = True
                    continue
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (bool, np.bool_)):
                    return '{} must be of type: bool'.format(attr)
        for attr in ['title', 'x_label', 'y_label', 'z_label']:
            if attr in state:
                if attr == 'z_label' and attrs['axis_type'] == '2d':
                    continue
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (type(None), str)):
                    return '{} must be one of the following types: None, str'.format(attr)
        for attr in ['x_unit', 'y_unit', 'z_unit']:
            if attr in state:
                if attr == 'z_unit' and attrs['axis_type'] == '2d':
                    continue
                attrs[attr], err_msg = validators.validate_unit(attr, unit_reg, state[attr])
                if err_msg is not None:
                    return err_msg
        if 'time_autoscale' in state:
            attrs['time_autoscale'] = state['time_autoscale']
            if not isinstance(attrs['time_autoscale'], (bool, np.bool_)):
                return 'time_autoscale must be of type: bool'

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def validate_data(self, data_objs, unit_reg):
        invalid_artists = [artist_name for artist_name in self.artists if self.artists[artist_name].set_state(data_objs, self.axis_type, [], unit_reg, {'data_name': self.artists[artist_name].data_name}) is not None]
        for artist_name in invalid_artists:
            self.artists.pop(artist_name)