from .._utilities import validators
import copy
import numpy as np
import pandas as pd
import vispy.color as vpcolor
import vispy.geometry as vpgeometry
import vispy.io as vpio
import vispy.scene as vpscene
import vispy.visuals as vpvisuals

class Artist:
    def __init__(self):
        self.selectable = False

    def calc_limits(self, data_obj, valid_idx, field, is_1d, get_last=False, size=None, radius_size=False, color_keys=None):
        if field is None:
            return [], [], []
        elif color_keys is not None:
            limits, strs, source = {}, {}, {}
            for i in range(len(field)):
                color_field, color_key = field[i], color_keys[i]
                color_limits, color_strs, color_source = self.calc_limits(data_obj, valid_idx, color_field, is_1d=is_1d, get_last=get_last)
                if len(color_source) > 0:
                    limits[color_key] = limits.get(color_key, []) + color_limits
                    strs[color_key] = strs.get(color_key, []) + color_strs
                    source[color_key] = source.get(color_key, []) + color_source
            return limits, strs, source
        elif isinstance(field, str):
            val_array = data_obj.data.loc[valid_idx, field]
            if len(val_array.index) == 0:
                return [], [], []
            elif get_last:
                val_array = val_array.iat[-1]
            if not is_1d:
                if isinstance(val_array, pd.Series):
                    val_array = val_array.to_numpy()
                val_array = pd.Series(np.concatenate(val_array, axis=None))
        else:
            val_array = field
        if not pd.api.types.is_list_like(val_array):
            val_array = pd.Series([val_array])
        if size is not None:
            if isinstance(size, str):
                extent = data_obj.data.loc[valid_idx, size]
                if get_last:
                    extent = extent.iat[-1]
            else:
                extent = size
            if not radius_size:
                extent /= 2
        if pd.api.types.is_numeric_dtype(val_array):
            val_array = np.real(val_array).astype('float64')
            val_array = val_array[np.isfinite(val_array)]
            if len(val_array) == 0:
                return [], [], []
            elif size is not None:
                val_array = [val_array + extent, val_array - extent]
            return [np.min(val_array), np.max(val_array)], [], ['num']
        elif pd.api.types.is_datetime64tz_dtype(val_array):
            nulls = val_array.isnull()
            val_array = (val_array.astype('int64') / 1e9)[~nulls]
            if len(val_array) == 0:
                return [], [], []
            elif size is not None:
                val_array = [val_array + extent, val_array - extent]
            return [np.min(val_array), np.max(val_array)], [], ['date']
        else:
            return [], val_array.astype('str').drop_duplicates().tolist(), ['str']

    def create_color(self, data_obj, valid_idx, str_map, color_limits, color, color_field, colormap, color_label, color_unit, is_1d, get_last, to_shape):
        if color_field is None: # Data array with single color
            if len(to_shape) == 1:
                output = np.tile(vpcolor.Color(color=color).rgba.reshape(1, 4), (to_shape[0], 1))
            else:
                output = np.tile(vpcolor.Color(color=color).rgba.reshape(1, 4), (to_shape[0] * to_shape[1], 1)).reshape(to_shape[0], to_shape[1], 4)
        else: # Color array
            color_key = (colormap, color_label, color_unit)
            color_data = self.field_to_numeric(data_obj, valid_idx, str_map[color_key], color_field, is_1d=is_1d, get_last=get_last)
            if not pd.api.types.is_list_like(color_data):
                color_data = np.array([color_data])
            min_color, max_color = color_limits[color_key][0], color_limits[color_key][1]
            normalized_vals = np.array((color_data - min_color) / (max_color - min_color))
            output = vpcolor.get_colormap(colormap).map(normalized_vals.reshape(-1, 1))
            if normalized_vals.ndim > 1:
                output = output.reshape(*normalized_vals.shape, 4)
        if self.selectable and not get_last and data_obj is not None and data_obj.selection is not None:
            alpha = output[tuple([slice(None)] * (output.ndim - 1) + [-1])]
            selected_alpha = np.full(len(alpha), 0.3)
            selected_alpha[data_obj.selection[valid_idx]] = 1.0
            output[tuple([slice(None)] * (output.ndim - 1) + [-1])] = selected_alpha
        else:
            output[tuple([slice(None)] * (output.ndim - 1) + [-1])] = 1
        return output

    def create_legend_color(self, name, color, color_field, colormap):
        if color_field is None:
            colormap_str = ''
            color_str = vpcolor.Color(color).hex
        else:
            color_hex = vpcolor.get_colormap(colormap).colors.hex
            color_pct = np.linspace(0, 100, len(color_hex))
            colormap_str = '<linearGradient id="{}" x1="0%" y1="0%" x2="100%" y2="0%">{}</linearGradient>'.format(name, ''.join(['<stop offset="{}%" stop-color="{}" />'.format(color_pct[i], color_hex[i]) for i in range(len(color_hex))]))
            color_str = 'url(#{})'.format(name)
        return colormap_str, color_str

    def create_legend_default(self, str_map, limits_source, color, color_field, colormap, color_label, color_unit, edge_color=None, edge_color_field=None, edge_colormap=None, edge_color_label=None, edge_color_unit=None, edge_width=None, is_line=False):
        colormap_str, color_str = self.create_legend_color('color', color, color_field, colormap)
        if (edge_color is not None or edge_color_field is not None) and edge_width is not None:
            edge_colormap_str, edge_color_str = self.create_legend_color('edge', edge_color, edge_color_field, edge_colormap)
            edge_opacity = 1 if edge_width > 0 else 0
            shape = '<rect x="0" y="7.5" width="30" height="15" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" />'.format('{}', edge_opacity, '{}')
            sub_shapes = self.create_legend_subentries(shape.format('none', '{}'), str_map, limits_source, color_field, colormap, color_label, color_unit)
            sub_edges = self.create_legend_subentries(shape.format('{}', 'none'), str_map, limits_source, edge_color_field, edge_colormap, edge_color_label, edge_color_unit)
            subentries = sub_shapes + sub_edges
            merged_subentries = {label: '<svg width="30" height="30">' for label, _ in subentries}
            for label, icon in subentries: merged_subentries[label] += icon
            for label in merged_subentries: merged_subentries[label] += '</svg>'
            shape = shape.format(edge_color_str, color_str)
            icon = '<svg width="30" height="30"><defs>{}{}</defs>{}</svg>'.format(colormap_str, edge_colormap_str, shape)
            return icon, list(merged_subentries.items())
        else:
            if is_line:
                shape = '<svg width="30" height="30"><defs>{}</defs><rect x="0" y="14" width="30" height="2" fill="{}" /></svg>'
            else:
                shape = '<svg width="30" height="30"><defs>{}</defs><rect x="0" y="7.5" width="30" height="15" fill="{}" /></svg>'
            subentries = self.create_legend_subentries(shape.format('', '{}'), str_map, limits_source, color_field, colormap, color_label, color_unit)
            return shape.format(colormap_str, color_str), subentries

    def create_legend_subentries(self, shape_str, str_map, limits_source, color_field, colormap, color_label, color_unit):
        color_key = (colormap, color_label, color_unit)
        if color_field is not None and limits_source[color_key] == 'str':
            color_vals = str_map[color_key]
            min_color, max_color = color_vals.iat[0], color_vals.iat[-1]
            normalized_vals = np.full(len(color_vals), 0.5) if min_color == max_color else np.array((color_vals - min_color) / (max_color - min_color))
            colors = vpcolor.get_colormap(colormap)[normalized_vals].hex
            return list(zip(color_vals.index.tolist(), [shape_str.format(color) for color in colors]))
        return []

    def field_to_numeric(self, data_obj, valid_idx, str_map, field, is_1d, get_last=False, norm_limits=None, is_size=False):
        if isinstance(field, str):
            array = data_obj.data.loc[valid_idx, field]
            if get_last:
                array = array.iat[-1]
                if is_1d:
                    return self.value_to_numeric(str_map, array, norm_limits=norm_limits, is_size=is_size)
            if pd.api.types.is_numeric_dtype(array):
                output = np.real(array)
            elif pd.api.types.is_datetime64tz_dtype(array):
                nulls = array.isnull()
                array = array.astype('int64') / 1e9
                array[nulls] = np.nan
                output = array
            else:
                output = str_map.loc[array.astype('str')]
            if norm_limits is not None:
                if is_size:
                    return output / abs(norm_limits[0] - norm_limits[1])
                return -0.5 + (output - norm_limits[0]) / (norm_limits[1] - norm_limits[0])
            return output
        return field

    def get_coordinates(self, data_obj, valid_idx, norm_limits, str_maps):
        pass

    def set_theme(self, visuals, theme):
        pass

    def value_to_numeric(self, str_map, value, norm_limits=None, is_size=False):
        if pd.api.types.is_numeric_dtype(type(value)):
            output = value.real
        elif isinstance(value, pd.Timestamp) and value.tzinfo is not None:
            output = value.timestamp()
        elif value is pd.NaT:
            output = np.nan
        else:
            output = str_map.at[str(value)]
        if norm_limits is not None:
            if is_size:
                return output / abs(norm_limits[0] - norm_limits[1])
            return -0.5 + (output - norm_limits[0]) / (norm_limits[1] - norm_limits[0])
        return output

class ArrowArtist(Artist):
    def __init__(self):
        super().__init__()
        self.artist_type = 'arrow'

    def get_coordinates(self, data_obj, valid_idx, norm_limits, str_maps):
        x = self.field_to_numeric(data_obj, valid_idx, str_maps['x'], self.x_field, is_1d=True, norm_limits=norm_limits['x'])
        y = self.field_to_numeric(data_obj, valid_idx, str_maps['y'], self.y_field, is_1d=True, norm_limits=norm_limits['y'])
        z = self.field_to_numeric(data_obj, valid_idx, str_maps['z'], self.z_field, is_1d=True, norm_limits=norm_limits['z'])
        return np.column_stack([x, y]) if z is None else np.column_stack([x, y, z])

    def get_current_data(self, data_obj, valid_idx, norm_limits, str_maps, color_limits):
        visual_input, text_input = {}, {}
        visual_input['pos'] = self.get_coordinates(data_obj, valid_idx, norm_limits, str_maps)
        to_shape = (visual_input['pos'].shape[0],)
        visual_input['arrow_color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.arrow_color, self.arrow_color_field, self.arrow_colormap, self.arrow_color_label, self.arrow_color_unit, is_1d=True, get_last=False, to_shape=to_shape)
        visual_input['color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.line_color, self.line_color_field, self.line_colormap, self.line_color_label, self.line_color_unit, is_1d=True, get_last=False, to_shape=to_shape) if self.line_width > 0 else self.line_color
        if data_obj.id_field is not None:
            id_vals = data_obj.data.loc[valid_idx, data_obj.id_field]
            id_vals.reset_index(drop=True, inplace=True)
            id_vals.sort_values(inplace=True, kind='mergesort')
            id_names = id_vals.loc[id_vals.duplicated(keep='last')]
            id_connect = pd.DataFrame({0: id_names.index, 1: id_vals.loc[id_vals.duplicated(keep='first')].index})
            visual_input['connect'] = id_connect.to_numpy()
            id_groups = id_connect.groupby(id_names.to_numpy(), as_index=False, dropna=False, sort=False)
            if self.arrow_spacing == 0:
                arrows = id_groups.tail(1)
            else:
                nth_arrow = id_groups.nth(list(range(np.max([self.arrow_spacing - 2, 0]), id_connect.shape[0], self.arrow_spacing)))
                if self.show_last_arrow:
                    arrows = nth_arrow.append(id_groups.tail(1)).drop_duplicates()
                    arrows.sort_index(inplace=True)
                else:
                    arrows = nth_arrow
            n_cols = visual_input['pos'].shape[1]
            arrow_color_idx = arrows.loc[:, 1]
            visual_input['arrows'] = np.empty((arrows.shape[0], n_cols * 2))
            visual_input['arrows'][:, :n_cols] = visual_input['pos'][arrows.loc[:, 0]]
            visual_input['arrows'][:, n_cols:] = visual_input['pos'][arrow_color_idx]
        else:
            visual_input['connect'] = 'strip'
            n_rows, n_cols = visual_input['pos'].shape
            arrow_color_idx = []
            if n_rows > 1:
                if self.arrow_spacing == 0:
                    visual_input['arrows'] = np.empty((1, n_cols * 2))
                    visual_input['arrows'][0, :n_cols] = visual_input['pos'][-2]
                    visual_input['arrows'][0, n_cols:] = visual_input['pos'][-1]
                    arrow_color_idx = [-1]
                else:
                    from_pos = visual_input['pos'][:-1][np.max([self.arrow_spacing - 2, 0])::self.arrow_spacing]
                    to_pos = visual_input['pos'][1:][np.max([self.arrow_spacing - 2, 0])::self.arrow_spacing]
                    n_spaced = from_pos.shape[0]
                    arrow_color_idx = to_pos
                    if self.show_last_arrow and n_rows % self.arrow_spacing != 0:
                        visual_input['arrows'] = np.empty((n_spaced + 1, n_cols * 2))
                        visual_input['arrows'][-1, :n_cols] = visual_input['pos'][-2]
                        visual_input['arrows'][-1, n_cols:] = visual_input['pos'][-1]
                        arrow_color_idx = np.append(arrow_color_idx, [-1])
                    else:
                        visual_input['arrows'] = np.empty((n_spaced, n_cols * 2))
                    visual_input['arrows'][:n_spaced, :n_cols] = from_pos
                    visual_input['arrows'][:n_spaced, n_cols:] = to_pos
            else:
                visual_input['arrows'] = np.empty((0, n_cols * 2))
        visual_input['arrow_color'] = visual_input['arrow_color'][arrow_color_idx, :]
        if self.label_field is not None:
            if data_obj.time_field is None:
                last_idx = slice(None)
            elif data_obj.id_field is not None:
                last_idx = id_vals.drop_duplicates(keep='last').index
            else:
                last_idx = [-1]
            text_input['pos'] = visual_input['pos'][last_idx]
            text_input['text'] = ('  ' + data_obj.data.loc[valid_idx, self.label_field].iloc[last_idx].astype(str)).to_numpy()
        return visual_input, text_input

    def get_legend_info(self, str_map, limits_source):
        arrow_colormap, arrow_color = self.create_legend_color('arrow', self.arrow_color, self.arrow_color_field, self.arrow_colormap)
        line_colormap, line_color = self.create_legend_color('line', self.line_color, self.line_color_field, self.line_colormap)
        line_opacity = 1 if self.line_width > 0 else 0
        line = '<rect x="0" y="14" width="30" height="2" fill="{}" fill-opacity="{}" />'.format('{}', line_opacity)
        if self.arrow_shape == 'stealth':
            arrow = '<polygon points="18.75,8.5 30,15 18.75,21.5 21.5,15" fill="{}" />'
        elif self.arrow_shape == 'curved':
            arrow = '<path d="M18.75 8.5 Q22.775 13.35 30 15 Q22.775 16.65 18.75 21.5 Q21.0 15 18.75 8.5 z" fill="{}" />'
        elif self.arrow_shape == 'angle_30':
            arrow = '<polyline points="15,11 30,15 15,15 30,15 15,19" stroke="{}" stroke-width="2" fill="none" />'
        elif self.arrow_shape == 'angle_60':
            arrow = '<polyline points="18.75,8.5 30,15 18.75,15 30,15 18.75,21.5" stroke="{}" stroke-width="2" fill="none" />'
        elif self.arrow_shape == 'angle_90':
            arrow = '<polyline points="22.5,7.5 30,15 22.5,15 30,15 22.5,22.5" stroke="{}" stroke-width="2" fill="none" />'
        elif self.arrow_shape == 'triangle_30':
            arrow = '<polygon points="15,11 30,15 15,19" fill="{}" />'
        elif self.arrow_shape == 'triangle_60':
            arrow = '<polygon points="18.75,8.5 30,15 18.75,21.5" fill="{}" />'
        elif self.arrow_shape == 'triangle_90':
            arrow = '<polygon points="22.5,7.5 30,15 22.5,22.5" fill="{}" />'
        elif self.arrow_shape == 'inhibitor_round':
            arrow = '<path d="M30 7.5 A7.5 7.5 0 0 0 30 22.5" stroke="{}" stroke-width="2" fill="none" />'
        else:
            arrow = ''
        sub_arrows = self.create_legend_subentries(arrow, str_map, limits_source, self.arrow_color_field, self.arrow_colormap, self.arrow_color_label, self.arrow_color_unit)
        sub_lines = self.create_legend_subentries(line, str_map, limits_source, self.line_color_field, self.line_colormap, self.line_color_label, self.line_color_unit) if line_opacity == 1 else []
        subentries = sub_arrows + sub_lines
        merged_subentries = {label: '<svg width="30" height="30">' for label, _ in subentries}
        for label, icon in subentries: merged_subentries[label] += icon
        for label in merged_subentries: merged_subentries[label] += '</svg>'
        line = line.format(line_color)
        arrow = arrow.format(arrow_color)
        icon = '<svg width="30" height="30"><defs>{}{}</defs>{}{}</svg>'.format(arrow_colormap, line_colormap, line, arrow)
        return icon, list(merged_subentries.items())

    def get_limits(self, data_obj, valid_idx, limit_type, is_time):
        if limit_type == 'x':
            return self.calc_limits(data_obj, valid_idx, self.x_field, is_1d=True)
        elif limit_type == 'y':
            return self.calc_limits(data_obj, valid_idx, self.y_field, is_1d=True)
        elif limit_type == 'z':
            return self.calc_limits(data_obj, valid_idx, self.z_field, is_1d=True)
        else:
            color_fields, color_keys = [self.arrow_color_field], [(self.arrow_colormap, self.arrow_color_label, self.arrow_color_unit)]
            if self.line_width > 0:
                color_fields.append(self.line_color_field)
                color_keys.append((self.line_colormap, self.line_color_label, self.line_color_unit))
            return self.calc_limits(data_obj, valid_idx, color_fields, is_1d=True, color_keys=color_keys)

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['artist_type', 'name', 'data_name', 'x_field', 'y_field', 'z_field', 'label_field', 'label_size', 'visible', 'draw_order', 'label_draw_order', 'legend_text', 'selectable',
                                                              'line_width', 'line_color', 'line_color_field', 'line_colormap', 'line_color_label', 'line_color_unit',
                                                              'arrow_shape', 'arrow_spacing', 'show_last_arrow', 'arrow_size',
                                                              'arrow_color', 'arrow_color_field', 'arrow_colormap', 'arrow_color_label', 'arrow_color_unit']}
        return copy.deepcopy(state) if as_copy else state

    def initialize(self, view):
        arrow = vpscene.Arrow(arrow_size=self.arrow_size, arrow_type=self.arrow_shape, width=self.line_width, parent=view.scene)
        arrow.order = self.draw_order
        text = vpscene.Text(anchor_x='left', font_size=self.label_size, parent=view.scene)
        text.order = self.label_draw_order
        return [arrow, text]

    def set_state(self, data_objs, axis_type, artist_names, unit_reg, state):
        attrs = self.get_state(as_copy=False)
        data_changed = False

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in artist_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'data_name' in state:
            attrs['data_name'] = state['data_name']
            if not isinstance(attrs['data_name'], str):
                return 'data_name must be of type: str'
            elif attrs['data_name'] not in data_objs:
                return '"{}" is not a valid data name.'.format(attrs['data_name'])
            data_changed = True
        for attr in ['x_field', 'y_field', 'z_field', 'label_field', 'line_color_field', 'arrow_color_field']:
            if attr in state or data_changed:
                if attr == 'z_field' and axis_type == '2d':
                    continue
                elif attr in state:
                    attrs[attr] = state[attr]
                err_msg = validators.validate_field(attr, data_objs, attrs['data_name'], attrs[attr], required_names=['x_field', 'y_field'], optional_names=['z_field', 'label_field', 'line_color_field', 'arrow_color_field'])
                if err_msg is not None:
                    return err_msg
        for attr in ['legend_text', 'line_color_label', 'arrow_color_label']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (type(None), str)):
                    return '{} must be one of the following types: None, str'
        if 'arrow_shape' in state:
            attrs['arrow_shape'] = state['arrow_shape']
            if not isinstance(attrs['arrow_shape'], str):
                return 'arrow_shape must be of type: str'
            elif attrs['arrow_shape'] not in vpvisuals.line.arrow.ARROW_TYPES:
                return 'arrow_shape must be one of the following: {}'.format(str(vpvisuals.line.arrow.ARROW_TYPES)[1:-1])
        if 'arrow_spacing' in state:
            attrs['arrow_spacing'] = state['arrow_spacing']
            if not isinstance(attrs['arrow_spacing'], (int, np.integer)):
                return 'arrow_spacing must be of type: int'
            elif 0 > attrs['arrow_spacing']:
                return 'arrow_spacing must be greater than or equal to 0.'
        if 'show_last_arrow' in state:
            attrs['show_last_arrow'] = state['show_last_arrow']
            if not isinstance(attrs['show_last_arrow'], (bool, np.bool_)):
                return 'show_last_arrow must be of type: bool'
        for attr in ['label_size', 'draw_order', 'label_draw_order', 'line_width', 'arrow_size']:
            if attr in state:
                attrs[attr] = state[attr]
                if not pd.api.types.is_numeric_dtype(type(attrs[attr])):
                    return '{} must be numeric.'.format(attr)
                attrs[attr] = attrs[attr].real
                if not np.isfinite(attrs[attr]):
                    return '{} must be finite.'.format(attr)
                elif attr in ['label_size', 'line_width', 'arrow_size'] and 0 >= attrs[attr]:
                    return '{} must be greater than 0.'.format(attr)
        for attr in ['line_color', 'arrow_color']:
            if attr in state:
                attrs[attr] = state[attr]
                err_msg = validators.validate_color(attr, attrs[attr])
                if err_msg is not None:
                    return err_msg
        for attr in ['line_colormap', 'arrow_colormap']:
            if attr in state:
                attrs[attr] = state[attr]
                err_msg = validators.validate_colormap(attr, attrs[attr])
                if err_msg is not None:
                    return err_msg
        for attr in ['line_color_unit', 'arrow_color_unit']:
            if attr in state:
                attrs[attr], err_msg = validators.validate_unit(attr, unit_reg, state[attr])
                if err_msg is not None:
                    return err_msg
        for attr in ['visible', 'selectable']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (bool, np.bool_)):
                    return '{} must be of type: bool'.format(attr)

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def set_theme(self, visuals, theme):
        visuals[1].color = 'w' if theme == 'dark' else 'k'

    def update(self, data_obj, visuals, valid_idx, norm_limits, str_maps, color_limits):
        if self.visible and valid_idx.any():
            visual_input, text_input = self.get_current_data(data_obj, valid_idx, norm_limits, str_maps, color_limits)
            visuals[0].arrow_color = visual_input.pop('arrow_color')
            visuals[0].set_data(**visual_input)
            show_labels = len(text_input) > 0
            if not visuals[0].visible:
                visuals[0].visible = True
            if show_labels:
                for attr in text_input:
                    setattr(visuals[1], attr, text_input[attr])
            if show_labels != visuals[1].visible:
                visuals[1].visible = show_labels
        else:
            if visuals[0].visible:
                visuals[0].visible = False
            if visuals[1].visible:
                visuals[1].visible = False

class BoxArtist(Artist):
    def __init__(self):
        super().__init__()
        self.artist_type = 'box'

    def get_current_data(self, data_obj, valid_idx, norm_limits, str_maps, color_limits):
        visual_input = {}

        if self.x_pos_field is None:
            x = self.value_to_numeric(str_maps['x'], self.x_pos, norm_limits=norm_limits['x'])
        else:
            x = self.field_to_numeric(data_obj, valid_idx, str_maps['x'], self.x_pos_field, is_1d=True, get_last=True, norm_limits=norm_limits['x'])
        if self.y_pos_field is None:
            y = self.value_to_numeric(str_maps['y'], self.y_pos, norm_limits=norm_limits['y'])
        else:
            y = self.field_to_numeric(data_obj, valid_idx, str_maps['y'], self.y_pos_field, is_1d=True, get_last=True, norm_limits=norm_limits['y'])
        if self.z_pos_field is None:
            z = self.value_to_numeric(str_maps['z'], self.z_pos, norm_limits=norm_limits['z'])
        else:
            z = self.field_to_numeric(data_obj, valid_idx, str_maps['z'], self.z_pos_field, is_1d=True, get_last=True, norm_limits=norm_limits['z'])
        if self.width_field is None:
            visual_input['width'] = self.value_to_numeric(None, self.width, norm_limits=norm_limits['x'], is_size=True)
        else:
            visual_input['width'] = self.field_to_numeric(data_obj, valid_idx, None, self.width_field, is_1d=True, get_last=True, norm_limits=norm_limits['x'], is_size=True)
        if self.height_field is None:
            visual_input['height'] = self.value_to_numeric(None, self.height, norm_limits=norm_limits['y'], is_size=True)
        else:
            visual_input['heigth'] = self.field_to_numeric(data_obj, valid_idx, None, self.height_field, is_1d=True, get_last=True, norm_limits=norm_limits['y'], is_size=True)
        if self.depth_field is None:
            visual_input['depth'] = self.value_to_numeric(None, self.depth, norm_limits=norm_limits['z'], is_size=True)
        else:
            visual_input['depth'] = self.field_to_numeric(data_obj, valid_idx, None, self.depth_field, is_1d=True, get_last=True, norm_limits=norm_limits['z'], is_size=True)
        visual_input['color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.color, self.color_field, self.colormap, self.color_label, self.color_unit, is_1d=True, get_last=True, to_shape=(1,))
        visual_input['planes'] = []
        for face in self.faces:
            face_lower = face.lower()
            visual_input['planes'].append('{}{}'.format('-' if face == face_lower else '+', face_lower))
        transform = vpvisuals.transforms.MatrixTransform()
        transform.translate([x, y, z])
        return visual_input, transform

    def get_legend_info(self, str_map, limits_source):
        return self.create_legend_default(str_map, limits_source, self.color, self.color_field, self.colormap, self.color_label, self.color_unit)

    def get_limits(self, data_obj, valid_idx, limit_type, is_time):
        if limit_type == 'x':
            return self.calc_limits(data_obj, valid_idx, self.x_pos if self.x_pos_field is None else self.x_pos_field, is_1d=True, get_last=is_time, size=self.width if self.width_field is None else self.width_field)
        elif limit_type == 'y':
            return self.calc_limits(data_obj, valid_idx, self.y_pos if self.y_pos_field is None else self.y_pos_field, is_1d=True, get_last=is_time, size=self.height if self.height_field is None else self.height_field)
        elif limit_type == 'z':
            return self.calc_limits(data_obj, valid_idx, self.z_pos if self.z_pos_field is None else self.z_pos_field, is_1d=True, get_last=is_time, size=self.depth if self.depth_field is None else self.depth_field)
        else:
            return self.calc_limits(data_obj, valid_idx, [self.color_field], is_1d=True, get_last=is_time, color_keys=[(self.colormap, self.color_label, self.color_unit)])

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['artist_type', 'name', 'data_name', 'visible', 'draw_order', 'legend_text', 'x_pos', 'x_pos_field', 'y_pos', 'y_pos_field', 'z_pos', 'z_pos_field', 'width', 'width_field', 'height', 'height_field', 'depth', 'depth_field', 'color', 'color_field', 'colormap', 'color_label', 'color_unit', 'faces']}
        return copy.deepcopy(state) if as_copy else state

    def initialize(self, view):
        box = vpscene.Mesh(parent=view.scene)
        box.set_gl_state(polygon_offset_fill=True, polygon_offset=(1, 1), depth_test=True)
        box.order = self.draw_order
        return [box]

    def set_state(self, data_objs, axis_type, artist_names, unit_reg, state):
        attrs = self.get_state(as_copy=False)
        data_changed, no_fields = False, True

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in artist_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'data_name' in state:
            attrs['data_name'] = state['data_name']
            if not isinstance(attrs['data_name'], (type(None), str)):
                return 'data_name must be one of the following types: None, str'
            elif attrs['data_name'] is not None and attrs['data_name'] not in data_objs:
                return '"{}" is not a valid data name.'.format(attrs['data_name'])
            data_changed = True
        for attr in ['x_pos_field', 'y_pos_field', 'z_pos_field', 'width_field', 'height_field', 'depth_field', 'color_field']:
            if attr in state or data_changed:
                if attr in state:
                    attrs[attr] = state[attr]
                err_msg = validators.validate_field(attr, data_objs, attrs['data_name'], attrs[attr], optional_names=['x_pos_field', 'y_pos_field', 'z_pos_field', 'width_field', 'height_field', 'depth_field', 'color_field'], size_names=['width_field', 'height_field', 'depth_field'])
                if err_msg is not None:
                    return err_msg
            if attrs[attr] is not None:
                no_fields = False
        for attr in ['legend_text', 'color_label']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (type(None), str)):
                    return '{} must be one of the following types: None, str'
        for attr in ['draw_order', 'x_pos', 'y_pos', 'z_pos', 'width', 'height', 'depth']:
            if attr in state:
                attrs[attr] = state[attr]
                if not pd.api.types.is_numeric_dtype(type(attrs[attr])):
                    return '{} must be numeric.'.format(attr)
                attrs[attr] = attrs[attr].real
                if not np.isfinite(attrs[attr]):
                    return '{} must be finite.'.format(attr)
                elif attr in ['width', 'height', 'depth'] and 0 > attrs[attr]:
                    return '{} must be greater than or equal 0.'.format(attr)
        if 'color' in state:
            attrs['color'] = state['color']
            err_msg = validators.validate_color('color', attrs['color'])
            if err_msg is not None:
                return err_msg
        if 'colormap' in state:
            attrs['colormap'] = state['colormap']
            err_msg = validators.validate_colormap('colormap', attrs['colormap'])
            if err_msg is not None:
                return err_msg
        if 'color_unit' in state:
            attrs['color_unit'], err_msg = validators.validate_unit('color_unit', unit_reg, state['color_unit'])
            if err_msg is not None:
                return err_msg
        if 'faces' in state:
            faces = ''
            if not isinstance(state['faces'], str):
                return 'faces must be of type: str'
            for face in 'XxYyZz':
                if face in state['faces']:
                    faces += face
            attrs['faces'] = faces
        if 'visible' in state:
            attrs['visible'] = state['visible']
            if not isinstance(attrs['visible'], (bool, np.bool_)):
                return 'visible must be of type: bool'

        if no_fields:
            attrs['data_name'] = None

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def update(self, data_obj, visuals, valid_idx, norm_limits, str_maps, color_limits):
        if self.visible and (self.data_name is None or valid_idx.any()):
            visual_input, transform = self.get_current_data(data_obj, valid_idx, norm_limits, str_maps, color_limits)
            vertices, faces, _ = vpgeometry.create_box(width=visual_input['width'], height=visual_input['height'], depth=visual_input['depth'], planes=visual_input['planes'])
            visuals[0].set_data(vertices=vertices['position'], faces=faces, color=visual_input['color'])
            visuals[0].transform = transform
            if not visuals[0].visible:
                visuals[0].visible = True
        elif visuals[0].visible:
            visuals[0].visible = False

class EllipseArtist(Artist):
    def __init__(self):
        super().__init__()
        self.artist_type = 'ellipse'

    def get_current_data(self, data_obj, valid_idx, norm_limits, str_maps, color_limits):
        visual_input = {}
        if self.x_pos_field is None:
            x = self.value_to_numeric(str_maps['x'], self.x_pos, norm_limits=norm_limits['x'])
        else:
            x = self.field_to_numeric(data_obj, valid_idx, str_maps['x'], self.x_pos_field, is_1d=True, get_last=True, norm_limits=norm_limits['x'])
        if self.y_pos_field is None:
            y = self.value_to_numeric(str_maps['y'], self.y_pos, norm_limits=norm_limits['y'])
        else:
            y = self.field_to_numeric(data_obj, valid_idx, str_maps['y'], self.y_pos_field, is_1d=True, get_last=True, norm_limits=norm_limits['y'])
        if self.edge_width_field is None:
            visual_input['border_width'] = self.edge_width
        else:
            visual_input['border_width'] = self.field_to_numeric(data_obj, valid_idx, None, self.edge_width_field, is_1d=True, get_last=True)
        if self.x_radius_field is None:
            x_radius = self.value_to_numeric(None, self.x_radius, norm_limits=norm_limits['x'], is_size=True)
        else:
            x_radius = self.field_to_numeric(data_obj, valid_idx, None, self.x_radius_field, is_1d=True, get_last=True, norm_limits=norm_limits['x'], is_size=True)
        if self.y_radius_field is None:
            y_radius = self.value_to_numeric(None, self.y_radius, norm_limits=norm_limits['y'], is_size=True)
        else:
            y_radius = self.field_to_numeric(data_obj, valid_idx, None, self.y_radius_field, is_1d=True, get_last=True, norm_limits=norm_limits['y'], is_size=True)
        if self.start_angle_field is None:
            visual_input['start_angle'] = self.start_angle
        else:
            visual_input['start_angle'] = self.field_to_numeric(data_obj, valid_idx, None, self.start_angle_field, is_1d=True, get_last=True)
        if self.span_angle_field is None:
            visual_input['span_angle'] = self.span_angle
        else:
            visual_input['span_angle'] = self.field_to_numeric(data_obj, valid_idx, None, self.span_angle_field, is_1d=True, get_last=True)
        visual_input['center'] = [x, y]
        visual_input['radius'] = [x_radius, y_radius]
        to_shape = (1,)
        visual_input['color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.color, self.color_field, self.colormap, self.color_label, self.color_unit, is_1d=True, get_last=True, to_shape=to_shape)
        visual_input['border_color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.edge_color, self.edge_color_field, self.edge_colormap, self.edge_color_label, self.edge_color_unit, is_1d=True, get_last=True, to_shape=to_shape) if visual_input['border_width'] > 0 else self.edge_color
        return visual_input

    def get_legend_info(self, str_map, limits_source):
        return self.create_legend_default(str_map, limits_source, self.color, self.color_field, self.colormap, self.color_label, self.color_unit, edge_color=self.edge_color, edge_color_field=self.edge_color_field, edge_colormap=self.edge_colormap, edge_color_label=self.edge_color_label, edge_color_unit=self.edge_color_unit, edge_width=self.edge_width)

    def get_limits(self, data_obj, valid_idx, limit_type, is_time):
        if limit_type == 'x':
            return self.calc_limits(data_obj, valid_idx, self.x_pos if self.x_pos_field is None else self.x_pos_field, is_1d=True, get_last=is_time, size=self.x_radius if self.x_radius_field is None else self.x_radius_field, radius_size=True)
        elif limit_type == 'y':
            return self.calc_limits(data_obj, valid_idx, self.y_pos if self.y_pos_field is None else self.y_pos_field, is_1d=True, get_last=is_time, size=self.y_radius if self.y_radius_field is None else self.y_radius_field, radius_size=True)
        elif limit_type == 'z':
            return self.calc_limits(data_obj, valid_idx, None, is_1d=True, get_last=is_time)
        else:
            color_fields, color_keys = [self.color_field], [(self.colormap, self.color_label, self.color_unit)]
            if self.edge_width > 0 or self.edge_width_field is not None:
                color_fields.append(self.edge_color_field)
                color_keys.append((self.edge_colormap, self.edge_color_label, self.edge_color_unit))
            return self.calc_limits(data_obj, valid_idx, color_fields, is_1d=True, get_last=is_time, color_keys=color_keys)

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['artist_type', 'name', 'data_name', 'visible', 'draw_order', 'legend_text', 'start_angle', 'start_angle_field', 'span_angle', 'span_angle_field', 'x_pos', 'x_pos_field', 'y_pos', 'y_pos_field', 'edge_width', 'edge_width_field', 'x_radius', 'x_radius_field', 'y_radius', 'y_radius_field', 'color', 'color_field', 'colormap', 'color_label', 'color_unit', 'edge_color', 'edge_color_field', 'edge_colormap', 'edge_color_label', 'edge_color_unit']}
        return copy.deepcopy(state) if as_copy else state

    def initialize(self, view):
        ellipse = vpscene.Ellipse(center=[0, 0], parent=view.scene)
        ellipse.order = self.draw_order
        return [ellipse]

    def set_state(self, data_objs, axis_type, artist_names, unit_reg, state):
        attrs = self.get_state(as_copy=False)
        data_changed, no_fields = False, True

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in artist_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'data_name' in state:
            attrs['data_name'] = state['data_name']
            if not isinstance(attrs['data_name'], (type(None), str)):
                return 'data_name must be one of the following types: None, str'
            elif attrs['data_name'] is not None and attrs['data_name'] not in data_objs:
                return '"{}" is not a valid data name.'.format(attrs['data_name'])
            data_changed = True
        for attr in ['start_angle_field', 'span_angle_field', 'x_pos_field', 'y_pos_field', 'edge_width_field', 'x_radius_field', 'y_radius_field', 'color_field', 'edge_color_field']:
            if attr in state or data_changed:
                if attr in state:
                    attrs[attr] = state[attr]
                err_msg = validators.validate_field(attr, data_objs, attrs['data_name'], attrs[attr], optional_names=['start_angle_field', 'span_angle_field', 'x_pos_field', 'y_pos_field', 'edge_width_field', 'x_radius_field', 'y_radius_field', 'color_field', 'edge_color_field'], size_names=['x_radius_field', 'y_radius_field'])
                if err_msg is not None:
                    return err_msg
                elif attr in ['start_angle_field', 'span_angle_field'] and attrs[attr] is not None:
                    data = data_objs[attrs['data_name']].data.loc[:, attrs[attr]]
                    if not pd.api.types.is_numeric_dtype(data):
                        return '{} must have numeric values.'.format(attr)
                    elif not np.isfinite(data).all():
                        return '{} must have finite values.'.format(attr)
            if attrs[attr] is not None:
                no_fields = False
        for attr in ['legend_text', 'color_label', 'edge_color_label']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (type(None), str)):
                    return '{} must be one of the following types: None, str'
        for attr in ['draw_order', 'start_angle', 'span_angle', 'x_pos', 'y_pos', 'edge_width', 'x_radius', 'y_radius']:
            if attr in state:
                attrs[attr] = state[attr]
                if not pd.api.types.is_numeric_dtype(type(attrs[attr])):
                    return '{} must be numeric.'.format(attr)
                attrs[attr] = attrs[attr].real
                if not np.isfinite(attrs[attr]):
                    return '{} must be finite.'.format(attr)
                elif attr in ['edge_width', 'x_radius', 'y_radius'] and 0 > attrs[attr]:
                    return '{} must be greater than or equal 0.'.format(attr)
        for attr in ['color', 'edge_color']:
            if attr in state:
                attrs[attr] = state[attr]
                err_msg = validators.validate_color(attr, attrs[attr])
                if err_msg is not None:
                    return err_msg
        for attr in ['colormap', 'edge_colormap']:
            if attr in state:
                attrs[attr] = state[attr]
                err_msg = validators.validate_colormap(attr, attrs[attr])
                if err_msg is not None:
                    return err_msg
        for attr in ['color_unit', 'edge_color_unit']:
            if attr in state:
                attrs[attr], err_msg = validators.validate_unit(attr, unit_reg, state[attr])
                if err_msg is not None:
                    return err_msg
        if 'visible' in state:
            attrs['visible'] = state['visible']
            if not isinstance(attrs['visible'], (bool, np.bool_)):
                return 'visible must be of type: bool'

        if no_fields:
            attrs['data_name'] = None

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def update(self, data_obj, visuals, valid_idx, norm_limits, str_maps, color_limits):
        if self.visible and (self.data_name is None or valid_idx.any()):
            visual_input = self.get_current_data(data_obj, valid_idx, norm_limits, str_maps, color_limits)
            visuals[0].border.set_data(width=visual_input.pop('border_width'))
            for attr in visual_input:
                setattr(visuals[0], attr, visual_input[attr])
            if not visuals[0].visible:
                visuals[0].visible = True
        elif visuals[0].visible:
            visuals[0].visible = False

class ImageArtist(Artist):
    def __init__(self):
        super().__init__()
        self.artist_type = 'image'

    def get_current_data(self, data_obj, valid_idx, norm_limits, str_maps, color_limits):
        visual_input = {}
        visual_input['data'] = np.flipud(self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, None, self.color_field, self.colormap, self.color_label, self.color_unit, is_1d=False, get_last=True, to_shape=None)).astype('float32')
        x_shape, y_shape, _ = visual_input['data'].shape
        if self.x_pos_field is None:
            x = self.value_to_numeric(str_maps['x'], self.x_pos, norm_limits=norm_limits['x'])
        else:
            x = self.field_to_numeric(data_obj, valid_idx, str_maps['x'], self.x_pos_field, is_1d=True, get_last=True, norm_limits=norm_limits['x'])
        if self.y_pos_field is None:
            y = self.value_to_numeric(str_maps['y'], self.y_pos, norm_limits=norm_limits['y'])
        else:
            y = self.field_to_numeric(data_obj, valid_idx, str_maps['y'], self.y_pos_field, is_1d=True, get_last=True, norm_limits=norm_limits['y'])
        if self.width_field is None:
            width = self.value_to_numeric(None, self.width, norm_limits=norm_limits['x'], is_size=True)
        else:
            width = self.field_to_numeric(data_obj, valid_idx, None, self.width_field, is_1d=True, get_last=True, norm_limits=norm_limits['x'], is_size=True)
        if self.height_field is None:
            height = self.value_to_numeric(None, self.height, norm_limits=norm_limits['y'], is_size=True)
        else:
            height = self.field_to_numeric(data_obj, valid_idx, None, self.height_field, is_1d=True, get_last=True, norm_limits=norm_limits['y'], is_size=True)
        transform = vpvisuals.transforms.STTransform()
        transform.scale = (width / y_shape, height / x_shape)
        transform.translate = (x - width / 2, y - height / 2)
        return visual_input, transform

    def get_legend_info(self, str_map, limits_source):
        return self.create_legend_default(str_map, limits_source, None, self.color_field, self.colormap, self.color_label, self.color_unit)

    def get_limits(self, data_obj, valid_idx, limit_type, is_time):
        if limit_type == 'x':
            return self.calc_limits(data_obj, valid_idx, self.x_pos if self.x_pos_field is None else self.x_pos_field, is_1d=True, get_last=is_time, size=self.width if self.width_field is None else self.width_field)
        elif limit_type == 'y':
            return self.calc_limits(data_obj, valid_idx, self.y_pos if self.y_pos_field is None else self.y_pos_field, is_1d=True, get_last=is_time, size=self.height if self.height_field is None else self.height_field)
        elif limit_type == 'z':
            return self.calc_limits(data_obj, valid_idx, None, is_1d=True, get_last=is_time)
        else:
            return self.calc_limits(data_obj, valid_idx, [self.color_field], is_1d=False, get_last=is_time, color_keys=[(self.colormap, self.color_label, self.color_unit)])

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['artist_type', 'name', 'data_name', 'visible', 'draw_order', 'legend_text', 'x_pos', 'x_pos_field', 'y_pos', 'y_pos_field', 'width', 'width_field', 'height', 'height_field', 'color_field', 'colormap', 'color_label', 'color_unit', 'interpolation']}
        return copy.deepcopy(state) if as_copy else state

    def initialize(self, view):
        image = vpscene.Image(interpolation=self.interpolation, parent=view.scene)
        image.order = self.draw_order
        return [image]

    def set_state(self, data_objs, axis_type, artist_names, unit_reg, state):
        attrs = self.get_state(as_copy=False)
        data_changed = False

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in artist_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'data_name' in state:
            attrs['data_name'] = state['data_name']
            if not isinstance(attrs['data_name'], str):
                return 'data_name must be of type: str'
            elif attrs['data_name'] not in data_objs:
                return '"{}" is not a valid data name.'.format(attrs['data_name'])
            data_changed = True
        for attr in ['x_pos_field', 'y_pos_field', 'width_field', 'height_field', 'color_field']:
            if attr in state or data_changed:
                if attr in state:
                    attrs[attr] = state[attr]
                err_msg = validators.validate_field(attr, data_objs, attrs['data_name'], attrs[attr], required_names=['color_field'], optional_names=['x_pos_field', 'y_pos_field', 'width_field', 'height_field'], size_names=['width_field', 'height_field'])
                if err_msg is not None:
                    return err_msg
                if attrs[attr] is not None:
                    if attr == 'color_field':
                        data = data_objs[attrs['data_name']].data.loc[:, attrs[attr]]
                        dtypes = data.map(type).unique()
                        if len(dtypes) > 1 or dtypes[0] is not np.ndarray:
                            return '{} must contain numpy arrays.'.format(attr)
                        elif (data.map(np.ndim) != 2).any():
                            return '{} must contain 2D numpy arrays.'.format(attr)
                        elif (data.map(np.shape).map(np.prod) == 0).any():
                            return '{} must contain 2D numpy arrays with at least one row and one column.'
        for attr in ['legend_text', 'color_label']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (type(None), str)):
                    return '{} must be one of the following types: None, str'
        for attr in ['draw_order', 'x_pos', 'y_pos', 'width', 'height']:
            if attr in state:
                attrs[attr] = state[attr]
                if not pd.api.types.is_numeric_dtype(type(attrs[attr])):
                    return '{} must be numeric.'.format(attr)
                attrs[attr] = attrs[attr].real
                if not np.isfinite(attrs[attr]):
                    return '{} must be finite.'.format(attr)
                elif attr in ['width', 'height'] and 0 > attrs[attr]:
                    return '{} must be greater than or equal 0.'.format(attr)
        if 'colormap' in state:
            attrs['colormap'] = state['colormap']
            err_msg = validators.validate_colormap('colormap', attrs['colormap'])
            if err_msg is not None:
                return err_msg
        if 'color_unit' in state:
            attrs['color_unit'], err_msg = validators.validate_unit('color_unit', unit_reg, state['color_unit'])
            if err_msg is not None:
                return err_msg
        if 'interpolation' in state:
            attrs['interpolation'] = state['interpolation']
            if not isinstance(attrs['interpolation'], str):
                return 'interpolation must be of type: str'
            attrs['interpolation'] = attrs['interpolation'].lower()
            interp_names = [interp_name.lower() for interp_name in vpio.load_spatial_filters()[1]]
            if attrs['interpolation'] not in interp_names:
                return '{} must be one of the following: {}'.format(attr, str(interp_names)[1:-1])
        if 'visible' in state:
            attrs['visible'] = state['visible']
            if not isinstance(attrs['visible'], (bool, np.bool_)):
                return 'visible must be of type: bool'

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def update(self, data_obj, visuals, valid_idx, norm_limits, str_maps, color_limits):
        if self.visible and valid_idx.any():
            visual_input, transform = self.get_current_data(data_obj, valid_idx, norm_limits, str_maps, color_limits)
            visuals[0].set_data(visual_input['data'])
            visuals[0].transform = transform
            if not visuals[0].visible:
                visuals[0].visible = True
        elif visuals[0].visible:
            visuals[0].visible = False

class InfiniteLineArtist(Artist):
    def __init__(self):
        super().__init__()
        self.artist_type = 'infinite line'

    def get_current_data(self, data_obj, valid_idx, norm_limits, str_maps, color_limits):
        visual_input = {}
        axis = 'x' if self.is_vertical else 'y'
        if self.pos_field is None:
            visual_input['pos'] = self.value_to_numeric(str_maps[axis], self.pos, norm_limits=norm_limits[axis])
        else:
            visual_input['pos'] = self.field_to_numeric(data_obj, valid_idx, str_maps[axis], self.pos_field, is_1d=True, get_last=True, norm_limits=norm_limits[axis])
        visual_input['color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.color, self.color_field, self.colormap, self.color_label, self.color_unit, is_1d=True, get_last=True, to_shape=(1,)).flatten()
        return visual_input

    def get_legend_info(self, str_map, limits_source):
        return self.create_legend_default(str_map, limits_source, self.color, self.color_field, self.colormap, self.color_label, self.color_unit, is_line=True)

    def get_limits(self, data_obj, valid_idx, limit_type, is_time):
        if limit_type == 'x':
            if self.is_vertical:
                return self.calc_limits(data_obj, valid_idx, self.pos if self.pos_field is None else self.pos_field, is_1d=True, get_last=is_time)
            return self.calc_limits(data_obj, valid_idx, None, is_1d=True, get_last=is_time)
        elif limit_type == 'y':
            if self.is_vertical:
                return self.calc_limits(data_obj, valid_idx, None, is_1d=True, get_last=is_time)
            return self.calc_limits(data_obj, valid_idx, self.pos if self.pos_field is None else self.pos_field, is_1d=True, get_last=is_time)
        elif limit_type == 'z':
            return self.calc_limits(data_obj, valid_idx, None, is_1d=True, get_last=is_time)
        else:
            return self.calc_limits(data_obj, valid_idx, [self.color_field], is_1d=True, get_last=is_time, color_keys=[(self.colormap, self.color_label, self.color_unit)])

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['artist_type', 'name', 'data_name', 'visible', 'draw_order', 'legend_text', 'pos', 'pos_field', 'color', 'color_field', 'colormap', 'color_label', 'color_unit', 'is_vertical']}
        return copy.deepcopy(state) if as_copy else state

    def initialize(self, view):
        infinite_line = vpscene.InfiniteLine(vertical=self.is_vertical, parent=view.scene)
        infinite_line.order = self.draw_order
        return [infinite_line]

    def set_state(self, data_objs, axis_type, artist_names, unit_reg, state):
        attrs = self.get_state(as_copy=False)
        data_changed, no_fields = False, True

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in artist_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'data_name' in state:
            attrs['data_name'] = state['data_name']
            if not isinstance(attrs['data_name'], (type(None), str)):
                return 'data_name must be one of the following types: None, str'
            elif attrs['data_name'] is not None and attrs['data_name'] not in data_objs:
                return '"{}" is not a valid data name.'.format(attrs['data_name'])
            data_changed = True
        for attr in ['pos_field', 'color_field']:
            if attr in state or data_changed:
                if attr in state:
                    attrs[attr] = state[attr]
                err_msg = validators.validate_field(attr, data_objs, attrs['data_name'], attrs[attr], optional_names=['pos_field', 'color_field'])
                if err_msg is not None:
                    return err_msg
            if attrs[attr] is not None:
                no_fields = False
        for attr in ['legend_text', 'color_label']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (type(None), str)):
                    return '{} must be one of the following types: None, str'
        for attr in ['draw_order', 'pos']:
            if attr in state:
                attrs[attr] = state[attr]
                if not pd.api.types.is_numeric_dtype(type(attrs[attr])):
                    return '{} must be numeric.'.format(attr)
                attrs[attr] = attrs[attr].real
                if not np.isfinite(attrs[attr]):
                    return '{} must be finite.'.format(attr)
        if 'color' in state:
            attrs['color'] = state['color']
            err_msg = validators.validate_color('color', attrs['color'])
            if err_msg is not None:
                return err_msg
        if 'colormap' in state:
            attrs['colormap'] = state['colormap']
            err_msg = validators.validate_colormap('colormap', attrs['colormap'])
            if err_msg is not None:
                return err_msg
        if 'color_unit' in state:
            attrs['color_unit'], err_msg = validators.validate_unit('color_unit', unit_reg, state['color_unit'])
            if err_msg is not None:
                return err_msg
        for attr in ['visible', 'is_vertical']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (bool, np.bool_)):
                    return '{} must be of type: bool'.format(attr)

        if no_fields:
            attrs['data_name'] = None

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def update(self, data_obj, visuals, valid_idx, norm_limits, str_maps, color_limits):
        if self.visible and (self.data_name is None or valid_idx.any()):
            visual_input = self.get_current_data(data_obj, valid_idx, norm_limits, str_maps, color_limits)
            visuals[0].set_data(**visual_input)
            if not visuals[0].visible:
                visuals[0].visible = True
        elif visuals[0].visible:
            visuals[0].visible = False

class PolygonArtist(Artist):
    def __init__(self):
        super().__init__()
        self.artist_type = 'polygon'

    def get_current_data(self, data_obj, valid_idx, norm_limits, str_maps, color_limits):
        visual_input = {}
        x = self.field_to_numeric(data_obj, valid_idx, str_maps['x'], self.x_field, is_1d=False, get_last=True, norm_limits=norm_limits['x'])
        y = self.field_to_numeric(data_obj, valid_idx, str_maps['y'], self.y_field, is_1d=False, get_last=True, norm_limits=norm_limits['y'])
        visual_input['pos'] = np.column_stack([x, y])
        if self.edge_width_field is None:
            visual_input['border_width'] = self.edge_width
        else:
            visual_input['border_width'] = self.field_to_numeric(data_obj, valid_idx, None, self.edge_width_field, is_1d=True, get_last=True)
        to_shape = (1,)
        visual_input['color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.color, self.color_field, self.colormap, self.color_label, self.color_unit, is_1d=True, get_last=True, to_shape=to_shape)
        visual_input['border_color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.edge_color, self.edge_color_field, self.edge_colormap, self.edge_color_label, self.edge_color_unit, is_1d=True, get_last=True, to_shape=to_shape) if visual_input['border_width'] > 0 else self.edge_color
        return visual_input

    def get_legend_info(self, str_map, limits_source):
        return self.create_legend_default(str_map, limits_source, self.color, self.color_field, self.colormap, self.color_label, self.color_unit, edge_color=self.edge_color, edge_color_field=self.edge_color_field, edge_colormap=self.edge_colormap, edge_color_label=self.edge_color_label, edge_color_unit=self.edge_color_unit, edge_width=self.edge_width)

    def get_limits(self, data_obj, valid_idx, limit_type, is_time):
        if limit_type == 'x':
            return self.calc_limits(data_obj, valid_idx, self.x_field, is_1d=False, get_last=is_time)
        elif limit_type == 'y':
            return self.calc_limits(data_obj, valid_idx, self.y_field, is_1d=False, get_last=is_time)
        elif limit_type == 'z':
            return self.calc_limits(data_obj, valid_idx, None, is_1d=True, get_last=is_time)
        else:
            color_fields, color_keys = [self.color_field], [(self.colormap, self.color_label, self.color_unit)]
            if self.edge_width > 0 or self.edge_width_field is not None:
                color_fields.append(self.edge_color_field)
                color_keys.append((self.edge_colormap, self.edge_color_label, self.edge_color_unit))
            return self.calc_limits(data_obj, valid_idx, color_fields, is_1d=True, get_last=is_time, color_keys=color_keys)

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['artist_type', 'name', 'data_name', 'x_field', 'y_field', 'visible', 'draw_order', 'legend_text', 'edge_width', 'edge_width_field', 'color', 'color_field', 'colormap', 'color_label', 'color_unit', 'edge_color', 'edge_color_field', 'edge_colormap', 'edge_color_label', 'edge_color_unit']}
        return copy.deepcopy(state) if as_copy else state

    def initialize(self, view):
        polygon = vpscene.Polygon(parent=view.scene)
        polygon.order = self.draw_order
        return [polygon]

    def set_state(self, data_objs, axis_type, artist_names, unit_reg, state):
        attrs = self.get_state(as_copy=False)
        data_changed = field_changed = False

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in artist_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'data_name' in state:
            attrs['data_name'] = state['data_name']
            if not isinstance(attrs['data_name'], str):
                return 'data_name must be one of the following types: str'
            elif attrs['data_name'] not in data_objs:
                return '"{}" is not a valid data name.'.format(attrs['data_name'])
            data_changed = True
        for attr in ['x_field', 'y_field', 'edge_width_field', 'color_field', 'edge_color_field']:
            if attr in state or data_changed:
                if attr in state:
                    attrs[attr] = state[attr]
                    field_changed |= attr in ['x_field', 'y_field']
                err_msg = validators.validate_field(attr, data_objs, attrs['data_name'], attrs[attr], required_names=['x_field', 'y_field'], optional_names=['edge_width_field', 'color_field', 'edge_color_field'])
                if err_msg is not None:
                    return err_msg
        for attr in ['legend_text', 'color_label', 'edge_color_label']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (type(None), str)):
                    return '{} must be one of the following types: None, str'
        for attr in ['draw_order', 'edge_width']:
            if attr in state:
                attrs[attr] = state[attr]
                if not pd.api.types.is_numeric_dtype(type(attrs[attr])):
                    return '{} must be numeric.'.format(attr)
                attrs[attr] = attrs[attr].real
                if not np.isfinite(attrs[attr]):
                    return '{} must be finite.'.format(attr)
                elif attr == 'edge_width' and 0 > attrs[attr]:
                    return '{} must be greater than or equal 0.'.format(attr)
        for attr in ['color', 'edge_color']:
            if attr in state:
                attrs[attr] = state[attr]
                err_msg = validators.validate_color(attr, attrs[attr])
                if err_msg is not None:
                    return err_msg
        for attr in ['colormap', 'edge_colormap']:
            if attr in state:
                attrs[attr] = state[attr]
                err_msg = validators.validate_colormap(attr, attrs[attr])
                if err_msg is not None:
                    return err_msg
        for attr in ['color_unit', 'edge_color_unit']:
            if attr in state:
                attrs[attr], err_msg = validators.validate_unit(attr, unit_reg, state[attr])
                if err_msg is not None:
                    return err_msg
        if 'visible' in state:
            attrs['visible'] = state['visible']
            if not isinstance(attrs['visible'], (bool, np.bool_)):
                return 'visible must be of type: bool'

        if field_changed:
            data = data_objs[attrs['data_name']].data
            if (data.loc[:, attrs['x_field']].map(len) != data.loc[:, attrs['y_field']].map(len)).any():
                return 'Every array in y_field must have the same length as its corresponding array in x_field.'

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def update(self, data_obj, visuals, valid_idx, norm_limits, str_maps, color_limits):
        if self.visible and valid_idx.any():
            visual_input = self.get_current_data(data_obj, valid_idx, norm_limits, str_maps, color_limits)
            visuals[0].border.set_data(width=visual_input.pop('border_width'))
            for attr in visual_input:
                setattr(visuals[0], attr, visual_input[attr])
            if not visuals[0].visible:
                visuals[0].visible = True
        elif visuals[0].visible:
            visuals[0].visible = False

class RectangleArtist(Artist):
    def __init__(self):
        super().__init__()
        self.artist_type = 'rectangle'

    def get_current_data(self, data_obj, valid_idx, norm_limits, str_maps, color_limits):
        visual_input = {}
        if self.x_pos_field is None:
            x = self.value_to_numeric(str_maps['x'], self.x_pos, norm_limits=norm_limits['x'])
        else:
            x = self.field_to_numeric(data_obj, valid_idx, str_maps['x'], self.x_pos_field, is_1d=True, get_last=True, norm_limits=norm_limits['x'])
        if self.y_pos_field is None:
            y = self.value_to_numeric(str_maps['y'], self.y_pos, norm_limits=norm_limits['y'])
        else:
            y = self.field_to_numeric(data_obj, valid_idx, str_maps['y'], self.y_pos_field, is_1d=True, get_last=True, norm_limits=norm_limits['y'])
        if self.edge_width_field is None:
            visual_input['border_width'] = self.edge_width
        else:
            visual_input['border_width'] = self.field_to_numeric(data_obj, valid_idx, None, self.edge_width_field, is_1d=True, get_last=True)
        if self.width_field is None:
            visual_input['width'] = self.value_to_numeric(None, self.width, norm_limits=norm_limits['x'], is_size=True)
        else:
            visual_input['width'] = self.field_to_numeric(data_obj, valid_idx, None, self.width_field, is_1d=True, get_last=True, norm_limits=norm_limits['x'], is_size=True)
        if self.height_field is None:
            visual_input['height'] = self.value_to_numeric(None, self.height, norm_limits=norm_limits['y'], is_size=True)
        else:
            visual_input['height'] = self.field_to_numeric(data_obj, valid_idx, None, self.height_field, is_1d=True, get_last=True, norm_limits=norm_limits['y'], is_size=True)
        to_shape = (1,)
        visual_input['color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.color, self.color_field, self.colormap, self.color_label, self.color_unit, is_1d=True, get_last=True, to_shape=to_shape)
        visual_input['border_color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.edge_color, self.edge_color_field, self.edge_colormap, self.edge_color_label, self.edge_color_unit, is_1d=True, get_last=True, to_shape=to_shape) if visual_input['border_width'] > 0 else self.edge_color
        transform = vpvisuals.transforms.STTransform()
        transform.translate = (x, y, 0)
        return visual_input, transform

    def get_legend_info(self, str_map, limits_source):
        return self.create_legend_default(str_map, limits_source, self.color, self.color_field, self.colormap, self.color_label, self.color_unit, edge_color=self.edge_color, edge_color_field=self.edge_color_field, edge_colormap=self.edge_colormap, edge_color_label=self.edge_color_label, edge_color_unit=self.edge_color_unit, edge_width=self.edge_width)

    def get_limits(self, data_obj, valid_idx, limit_type, is_time):
        if limit_type == 'x':
            return self.calc_limits(data_obj, valid_idx, self.x_pos if self.x_pos_field is None else self.x_pos_field, is_1d=True, get_last=is_time, size=self.width if self.width_field is None else self.width_field)
        elif limit_type == 'y':
            return self.calc_limits(data_obj, valid_idx, self.y_pos if self.y_pos_field is None else self.y_pos_field, is_1d=True, get_last=is_time, size=self.height if self.height_field is None else self.height_field)
        elif limit_type == 'z':
            return self.calc_limits(data_obj, valid_idx, None, is_1d=True, get_last=is_time)
        else:
            color_fields, color_keys = [self.color_field], [(self.colormap, self.color_label, self.color_unit)]
            if self.edge_width > 0 or self.edge_width_field is not None:
                color_fields.append(self.edge_color_field)
                color_keys.append((self.edge_colormap, self.edge_color_label, self.edge_color_unit))
            return self.calc_limits(data_obj, valid_idx, color_fields, is_1d=True, get_last=is_time, color_keys=color_keys)

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['artist_type', 'name', 'data_name', 'visible', 'draw_order', 'legend_text', 'x_pos', 'x_pos_field', 'y_pos', 'y_pos_field', 'edge_width', 'edge_width_field', 'width', 'width_field', 'height', 'height_field', 'color', 'color_field', 'colormap', 'color_label', 'color_unit', 'edge_color', 'edge_color_field', 'edge_colormap', 'edge_color_label', 'edge_color_unit']}
        return copy.deepcopy(state) if as_copy else state

    def initialize(self, view):
        rectangle = vpscene.Rectangle(center=[0, 0], parent=view.scene)
        rectangle.order = self.draw_order
        return [rectangle]

    def set_state(self, data_objs, axis_type, artist_names, unit_reg, state):
        attrs = self.get_state(as_copy=False)
        data_changed, no_fields = False, True

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in artist_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'data_name' in state:
            attrs['data_name'] = state['data_name']
            if not isinstance(attrs['data_name'], (type(None), str)):
                return 'data_name must be one of the following types: None, str'
            elif attrs['data_name'] is not None and attrs['data_name'] not in data_objs:
                return '"{}" is not a valid data name.'.format(attrs['data_name'])
            data_changed = True
        for attr in ['x_pos_field', 'y_pos_field', 'edge_width_field', 'width_field', 'height_field', 'color_field', 'edge_color_field']:
            if attr in state or data_changed:
                if attr in state:
                    attrs[attr] = state[attr]
                err_msg = validators.validate_field(attr, data_objs, attrs['data_name'], attrs[attr], optional_names=['x_pos_field', 'y_pos_field', 'edge_width_field', 'width_field', 'height_field', 'color_field', 'edge_color_field'], size_names=['width_field', 'height_field'])
                if err_msg is not None:
                    return err_msg
            if attrs[attr] is not None:
                no_fields = False
        for attr in ['legend_text', 'color_label', 'edge_color_label']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (type(None), str)):
                    return '{} must be one of the following types: None, str'
        for attr in ['draw_order', 'x_pos', 'y_pos', 'edge_width', 'width', 'height']:
            if attr in state:
                attrs[attr] = state[attr]
                if not pd.api.types.is_numeric_dtype(type(attrs[attr])):
                    return '{} must be numeric.'.format(attr)
                attrs[attr] = attrs[attr].real
                if not np.isfinite(attrs[attr]):
                    return '{} must be finite.'.format(attr)
                elif attr in ['edge_width', 'width', 'height'] and 0 > attrs[attr]:
                    return '{} must be greater than or equal 0.'.format(attr)
        for attr in ['color', 'edge_color']:
            if attr in state:
                attrs[attr] = state[attr]
                err_msg = validators.validate_color(attr, attrs[attr])
                if err_msg is not None:
                    return err_msg
        for attr in ['colormap', 'edge_colormap']:
            if attr in state:
                attrs[attr] = state[attr]
                err_msg = validators.validate_colormap(attr, attrs[attr])
                if err_msg is not None:
                    return err_msg
        for attr in ['color_unit', 'edge_color_unit']:
            if attr in state:
                attrs[attr], err_msg = validators.validate_unit(attr, unit_reg, state[attr])
                if err_msg is not None:
                    return err_msg
        if 'visible' in state:
            attrs['visible'] = state['visible']
            if not isinstance(attrs['visible'], (bool, np.bool_)):
                return 'visible must be of type: bool'

        if no_fields:
            attrs['data_name'] = None

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def update(self, data_obj, visuals, valid_idx, norm_limits, str_maps, color_limits):
        if self.visible and (self.data_name is None or valid_idx.any()):
            visual_input, transform = self.get_current_data(data_obj, valid_idx, norm_limits, str_maps, color_limits)
            visuals[0].border.set_data(width=visual_input.pop('border_width'))
            visuals[0].transform = transform
            for attr in visual_input:
                setattr(visuals[0], attr, visual_input[attr])
            if not visuals[0].visible:
                visuals[0].visible = True
        elif visuals[0].visible:
            visuals[0].visible = False

class ScatterArtist(Artist):
    def __init__(self):
        super().__init__()
        self.artist_type = 'scatter'

    def get_coordinates(self, data_obj, valid_idx, norm_limits, str_maps):
        x = self.field_to_numeric(data_obj, valid_idx, str_maps['x'], self.x_field, is_1d=True, norm_limits=norm_limits['x'])
        y = self.field_to_numeric(data_obj, valid_idx, str_maps['y'], self.y_field, is_1d=True, norm_limits=norm_limits['y'])
        z = self.field_to_numeric(data_obj, valid_idx, str_maps['z'], self.z_field, is_1d=True, norm_limits=norm_limits['z'])
        return np.column_stack([x, y]) if z is None else np.column_stack([x, y, z])

    def get_current_data(self, data_obj, valid_idx, norm_limits, str_maps, color_limits):
        visual_input, text_input = {}, {}
        visual_input['data'] = self.get_coordinates(data_obj, valid_idx, norm_limits, str_maps)
        to_shape = (visual_input['data'].shape[0],)
        visual_input['face_color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.marker_color, self.marker_color_field, self.marker_colormap, self.marker_color_label, self.marker_color_unit, is_1d=True, get_last=False, to_shape=to_shape) if self.marker_size > 0 else self.marker_color
        visual_input['edge_color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.edge_color, self.edge_color_field, self.edge_colormap, self.edge_color_label, self.edge_color_unit, is_1d=True, get_last=False, to_shape=to_shape) if self.edge_width > 0 else self.edge_color
        visual_input['color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.line_color, self.line_color_field, self.line_colormap, self.line_color_label, self.line_color_unit, is_1d=True, get_last=False, to_shape=to_shape) if self.line_width > 0 else self.line_color
        if data_obj.id_field is not None:
            id_vals = data_obj.data.loc[valid_idx, data_obj.id_field]
            id_vals.reset_index(drop=True, inplace=True)
            id_vals.sort_values(inplace=True, kind='mergesort')
            visual_input['connect'] = np.column_stack([id_vals.loc[id_vals.duplicated(keep='last')].index, id_vals.loc[id_vals.duplicated(keep='first')].index])
        else:
            visual_input['connect'] = 'strip'
        if self.label_field is not None:
            if data_obj.time_field is None:
                last_idx = slice(None)
            elif data_obj.id_field is not None:
                last_idx = id_vals.drop_duplicates(keep='last').index
            else:
                last_idx = [-1]
            text_input['pos'] = visual_input['data'][last_idx]
            text_input['text'] = ('  ' + data_obj.data.loc[valid_idx, self.label_field].iloc[last_idx].astype(str)).to_numpy()
        return visual_input, text_input

    def get_legend_info(self, str_map, limits_source):
        marker_colormap, marker_color = self.create_legend_color('marker', self.marker_color, self.marker_color_field, self.marker_colormap)
        edge_colormap, edge_color = self.create_legend_color('edge', self.edge_color, self.edge_color_field, self.edge_colormap)
        line_colormap, line_color = self.create_legend_color('line', self.line_color, self.line_color_field, self.line_colormap)
        marker_opacity = 1 if self.marker_size > 0 else 0
        edge_opacity = 1 if self.edge_width > 0 else 0
        line_opacity = 1 if self.line_width > 0 else 0
        line = '<rect x="0" y="14" width="30" height="2" fill="{}" fill-opacity="{}" />'.format('{}', line_opacity)
        if self.marker in ['disc', 'o']:
            marker = '<circle cx="15" cy="15" r="7.5" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" fill-opacity="{}" />'
        elif self.marker in ['arrow', '>']:
            marker = '<polygon points="21,15 13.5,22.5 11.7,20.7 17.4,15 11.7,9.3 13.5,7.5" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" fill-opacity="{}" />'
        elif self.marker in ['square', 's']:
            marker = '<rect x="7.5" y="7.5" width="15" height="15" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" fill-opacity="{}" />'
        elif self.marker in ['vbar', '|']:
            marker = '<polygon points="12.5,7.5 17.5,7.5 17.5,22.5 12.5,22.5" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" fill-opacity="{}" />'
        elif self.marker in ['hbar', '-']:
            marker = '<polygon points="7.5,12.5 22.5,12.5 22.5,17.5 7.5,17.5" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" fill-opacity="{}" />'
        elif self.marker in ['cross', '+']:
            marker = '<polygon points="12.5,7.5 17.5,7.5 17.5,12.5 22.5,12.5 22.5,17.5 17.5,17.5 17.5,22.5 12.5,22.5 12.5,17.5 7.5,17.5 7.5,12.5 12.5,12.5" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" fill-opacity="{}" />'
        elif self.marker in ['tailed_arrow', '->']:
            marker = '<polygon points="22.5,15 15,22.5 13.2,20.7 17.8,16.25 7.5,16.25 7.5,13.75 17.8,13.75 13.2,9.3 15,7.5" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" fill-opacity="{}" />'
        elif self.marker in ['triangle_up', '^']:
            marker = '<polygon points="15,7.5 22.5,20.5 7.5,20.5" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" fill-opacity="{}" />'
        elif self.marker in ['triangle_down', 'v']:
            marker = '<polygon points="7.5,9.5 22.5,9.5 15,22.5" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" fill-opacity="{}" />'
        elif self.marker in ['star', '*']:
            marker = '<polygon points="15,3.7 17.9,12.3 26.9,12.3 19.7,17.7 22.3,26.3 15,21.2 7.7,26.3 10.3,17.7 3.1,12.3 12.1,12.3" transform="scale(0.75) translate(5, 4)" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" fill-opacity="{}" />'
        elif self.marker == 'ring':
            marker = '<circle cx="15" cy="15" r="6.5" stroke="{}" stroke-width="6" stroke-opacity="{}" fill="none" /><circle cx="15" cy="15" r="6.5" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="none" />'
        elif self.marker == 'clobber':
            marker = '<path d="M15 7.5 A5 5 0 0 0 10.05 12.52 A5 5 0 0 0 7.55 16.85 A5 5 0 0 0 12.55 21.85 A5 5 0 0 0 15.05 21.18 A5 5 0 0 0 17.55 21.85 A5 5 0 0 0 22.55 16.85 A5 5 0 0 0 20.05 12.52 A5 5 0 0 0 15.05 7.55 A5 5 0 0 0 15.04 7.55 z" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" fill-opacity="{}" />'
        elif self.marker == 'diamond':
            marker = '<polygon points="15,7.5 22.5,15 15,22.5 7.5,15" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" fill-opacity="{}" />'
        elif self.marker == 'x':
            marker = '<polygon points="11.25,7.5 15,11.25 18.75,7.5 22.5,11.25 18.75,15 22.5,18.75 18.75,22.5 15,18.75 11.25,22.5 7.5,18.75 11.25,15 7.5,11.25" stroke="{}" stroke-width="2" stroke-opacity="{}" fill="{}" fill-opacity="{}" />'
        else:
            marker = ''
        marker = marker.format('{}', edge_opacity, '{}', marker_opacity)
        sub_markers = self.create_legend_subentries(marker.format('none', '{}'), str_map, limits_source, self.marker_color_field, self.marker_colormap, self.marker_color_label, self.marker_color_unit) if marker_opacity == 1 else []
        sub_edges = self.create_legend_subentries(marker.format('{}', 'none'), str_map, limits_source, self.edge_color_field, self.edge_colormap, self.edge_color_label, self.edge_color_unit) if edge_opacity == 1 else []
        sub_lines = self.create_legend_subentries(line, str_map, limits_source, self.line_color_field, self.line_colormap, self.line_color_label, self.line_color_unit) if line_opacity == 1 else []
        subentries = sub_markers + sub_edges + sub_lines
        merged_subentries = {label: '<svg width="30" height="30">' for label, _ in subentries}
        for label, icon in subentries: merged_subentries[label] += icon
        for label in merged_subentries: merged_subentries[label] += '</svg>'
        line = line.format(line_color)
        marker = marker.format(edge_color, marker_color)
        icon = '<svg width="30" height="30"><defs>{}{}{}</defs>{}{}</svg>'.format(marker_colormap, edge_colormap, line_colormap, line, marker)
        return icon, list(merged_subentries.items())

    def get_limits(self, data_obj, valid_idx, limit_type, is_time):
        if limit_type == 'x':
            return self.calc_limits(data_obj, valid_idx, self.x_field, is_1d=True)
        elif limit_type == 'y':
            return self.calc_limits(data_obj, valid_idx, self.y_field, is_1d=True)
        elif limit_type == 'z':
            return self.calc_limits(data_obj, valid_idx, self.z_field, is_1d=True)
        else:
            color_fields, color_keys = [], []
            if self.line_width > 0:
                color_fields.append(self.line_color_field)
                color_keys.append((self.line_colormap, self.line_color_label, self.line_color_unit))
            if self.marker_size > 0:
                color_fields.append(self.marker_color_field)
                color_keys.append((self.marker_colormap, self.marker_color_label, self.marker_color_unit))
            if self.edge_width > 0:
                color_fields.append(self.edge_color_field)
                color_keys.append((self.edge_colormap, self.edge_color_label, self.edge_color_unit))
            return self.calc_limits(data_obj, valid_idx, color_fields, is_1d=True, color_keys=color_keys)

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['artist_type', 'name', 'data_name', 'x_field', 'y_field', 'z_field', 'label_field', 'label_size', 'visible', 'draw_order', 'label_draw_order', 'legend_text', 'selectable',
                                                              'line_width', 'line_color', 'line_color_field', 'line_colormap', 'line_color_label', 'line_color_unit',
                                                              'marker', 'marker_size', 'marker_color', 'marker_color_field', 'marker_colormap', 'marker_color_label', 'marker_color_unit',
                                                              'edge_width', 'edge_color', 'edge_color_field', 'edge_colormap', 'edge_color_label', 'edge_color_unit']}
        return copy.deepcopy(state) if as_copy else state

    def initialize(self, view):
        scatter = vpscene.LinePlot(edge_width=self.edge_width, marker_size=self.marker_size, symbol=self.marker, width=self.line_width, parent=view.scene)
        scatter.remove_subvisual(scatter._line)
        scatter.add_subvisual(scatter._line)
        scatter._markers.antialias = 0
        scatter.order = self.draw_order
        text = vpscene.Text(anchor_x='left', font_size=self.label_size, parent=view.scene)
        text.order = self.label_draw_order
        return [scatter, text]

    def set_state(self, data_objs, axis_type, artist_names, unit_reg, state):
        attrs = self.get_state(as_copy=False)
        data_changed = False

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in artist_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'data_name' in state:
            attrs['data_name'] = state['data_name']
            if not isinstance(attrs['data_name'], str):
                return 'data_name must be of type: str'
            elif attrs['data_name'] not in data_objs:
                return '"{}" is not a valid data name.'.format(attrs['data_name'])
            data_changed = True
        for attr in ['x_field', 'y_field', 'z_field', 'label_field', 'line_color_field', 'marker_color_field', 'edge_color_field']:
            if attr in state or data_changed:
                if attr == 'z_field' and axis_type == '2d':
                    continue
                elif attr in state:
                    attrs[attr] = state[attr]
                err_msg = validators.validate_field(attr, data_objs, attrs['data_name'], attrs[attr], required_names=['x_field', 'y_field'], optional_names=['z_field', 'label_field', 'line_color_field', 'marker_color_field', 'edge_color_field'])
                if err_msg is not None:
                    return err_msg
        for attr in ['legend_text', 'line_color_label', 'marker_color_label', 'edge_color_label']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (type(None), str)):
                    return '{} must be one of the following types: None, str'
        if 'marker' in state:
            attrs['marker'] = state['marker']
            if not isinstance(attrs['marker'], str):
                return 'marker must be of type: str'
            elif attrs['marker'] not in vpvisuals.marker_types:
                return 'marker must be one of the following: {}'.format(str(vpvisuals.marker_types)[1:-1])
        for attr in ['label_size', 'draw_order', 'label_draw_order', 'line_width', 'marker_size', 'edge_width']:
            if attr in state:
                attrs[attr] = state[attr]
                if not pd.api.types.is_numeric_dtype(type(attrs[attr])):
                    return '{} must be numeric.'.format(attr)
                attrs[attr] = attrs[attr].real
                if not np.isfinite(attrs[attr]):
                    return '{} must be finite.'.format(attr)
                elif attr in ['label_size', 'line_width', 'marker_size', 'edge_width'] and 0 > attrs[attr]:
                    return '{} must be greater than or equal to 0.'.format(attr)
        for attr in ['line_color', 'marker_color', 'edge_color']:
            if attr in state:
                attrs[attr] = state[attr]
                err_msg = validators.validate_color(attr, attrs[attr])
                if err_msg is not None:
                    return err_msg
        for attr in ['line_colormap', 'marker_colormap', 'edge_colormap']:
            if attr in state:
                attrs[attr] = state[attr]
                err_msg = validators.validate_colormap(attr, attrs[attr])
                if err_msg is not None:
                    return err_msg
        for attr in ['line_color_unit', 'marker_color_unit', 'edge_color_unit']:
            if attr in state:
                attrs[attr], err_msg = validators.validate_unit(attr, unit_reg, state[attr])
                if err_msg is not None:
                    return err_msg
        for attr in ['visible', 'selectable']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (bool, np.bool_)):
                    return '{} must be of type: bool'.format(attr)

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def set_theme(self, visuals, theme):
        visuals[1].color = 'w' if theme == 'dark' else 'k'

    def update(self, data_obj, visuals, valid_idx, norm_limits, str_maps, color_limits):
        if self.visible and valid_idx.any():
            visual_input, text_input = self.get_current_data(data_obj, valid_idx, norm_limits, str_maps, color_limits)
            visuals[0].set_data(**visual_input)
            show_labels = len(text_input) > 0
            if not visuals[0].visible:
                visuals[0].visible = True
            if show_labels:
                for attr in text_input:
                    setattr(visuals[1], attr, text_input[attr])
            if show_labels != visuals[1].visible:
                visuals[1].visible = show_labels
        else:
            if visuals[0].visible:
                visuals[0].visible = False
            if visuals[1].visible:
                visuals[1].visible = False

class SurfaceArtist(Artist):
    def __init__(self):
        super().__init__()
        self.artist_type = 'surface'

    def get_current_data(self, data_obj, valid_idx, norm_limits, str_maps, color_limits):
        visual_input = {}
        visual_input['x'] = self.field_to_numeric(data_obj, valid_idx, str_maps['x'], self.x_field, is_1d=False, get_last=True, norm_limits=norm_limits['x'])
        visual_input['y'] = self.field_to_numeric(data_obj, valid_idx, str_maps['y'], self.y_field, is_1d=False, get_last=True, norm_limits=norm_limits['y'])
        visual_input['z'] = np.rot90(self.field_to_numeric(data_obj, valid_idx, str_maps['z'], self.z_field, is_1d=False, get_last=True, norm_limits=norm_limits['z']), 3)
        to_shape = visual_input['z'].shape
        visual_input['colors'] = np.rot90(self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.color, self.color_field, self.colormap, self.color_label, self.color_unit, is_1d=False, get_last=True, to_shape=to_shape), 3).reshape(to_shape[0] * to_shape[1], 4)
        return visual_input

    def get_legend_info(self, str_map, limits_source):
        return self.create_legend_default(str_map, limits_source, self.color, self.color_field, self.colormap, self.color_label, self.color_unit)

    def get_limits(self, data_obj, valid_idx, limit_type, is_time):
        if limit_type == 'x':
            return self.calc_limits(data_obj, valid_idx, self.x_field, is_1d=False, get_last=is_time)
        elif limit_type == 'y':
            return self.calc_limits(data_obj, valid_idx, self.y_field, is_1d=False, get_last=is_time)
        elif limit_type == 'z':
            return self.calc_limits(data_obj, valid_idx, self.z_field, is_1d=False, get_last=is_time)
        else:
            return self.calc_limits(data_obj, valid_idx, [self.color_field], is_1d=False, get_last=is_time, color_keys=[(self.colormap, self.color_label, self.color_unit)])

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['artist_type', 'name', 'data_name', 'x_field', 'y_field', 'z_field', 'visible', 'draw_order', 'legend_text', 'color', 'color_field', 'colormap', 'color_label', 'color_unit']}
        return copy.deepcopy(state) if as_copy else state

    def initialize(self, view):
        surface = vpscene.SurfacePlot(shading=None, parent=view.scene)
        surface.order = self.draw_order
        return [surface]

    def set_state(self, data_objs, axis_type, artist_names, unit_reg, state):
        attrs = self.get_state(as_copy=False)
        data_changed = field_changed = False

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in artist_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'data_name' in state:
            attrs['data_name'] = state['data_name']
            if not isinstance(attrs['data_name'], str):
                return 'data_name must be of type: str'
            elif attrs['data_name'] not in data_objs:
                return '"{}" is not a valid data name.'.format(attrs['data_name'])
            data_changed = True
        for attr in ['x_field', 'y_field', 'z_field', 'color_field']:
            if attr in state or data_changed:
                if attr in state:
                    attrs[attr] = state[attr]
                    field_changed = True
                err_msg = validators.validate_field(attr, data_objs, attrs['data_name'], attrs[attr], required_names=['x_field', 'y_field', 'z_field'], optional_names=['color_field'])
                if err_msg is not None:
                    return err_msg
                if attrs[attr] is not None:
                    data = data_objs[attrs['data_name']].data.loc[:, attrs[attr]]
                    dtypes = data.map(type).unique()
                    if len(dtypes) > 1 or dtypes[0] is not np.ndarray:
                        return '{} must contain numpy arrays.'.format(attr)
                    elif attr in ['x_field', 'y_field']:
                        if (data.map(np.ndim) != 1).any():
                            return '{} must contain 1D numpy arrays.'.format(attr)
                        elif (data.map(len) == 0).any():
                            return '{} must contain 1D numpy arrays with at least one value.'.format(attr)
                    elif attr in ['z_field', 'color_field']:
                        if (data.map(np.ndim) != 2).any():
                            return '{} must contain 2D numpy arrays.'.format(attr)
                        elif (data.map(np.shape).map(np.prod) == 0).any():
                            return '{} must contain 2D numpy arrays with at least one row and one column.'.format(attr)
        for attr in ['legend_text', 'color_label']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (type(None), str)):
                    return '{} must be one of the following types: None, str'
        if 'draw_order' in state:
            attrs['draw_order'] = state['draw_order']
            if not pd.api.types.is_numeric_dtype(type(attrs['draw_order'])):
                return 'draw_order must be numeric.'
            attrs['draw_order'] = attrs['draw_order'].real
            if not np.isfinite(attrs['draw_order']):
                return 'draw_order must be finite.'
        if 'color' in state:
            attrs['color'] = state['color']
            err_msg = validators.validate_color('color', attrs['color'])
            if err_msg is not None:
                return err_msg
        if 'colormap' in state:
            attrs['colormap'] = state['colormap']
            err_msg = validators.validate_colormap('colormap', attrs['colormap'])
            if err_msg is not None:
                return err_msg
        if 'color_unit' in state:
            attrs['color_unit'], err_msg = validators.validate_unit('color_unit', unit_reg, state['color_unit'])
            if err_msg is not None:
                return err_msg
        if 'visible' in state:
            attrs['visible'] = state['visible']
            if not isinstance(attrs['visible'], (bool, np.bool_)):
                return 'visible must be of type: bool'

        if field_changed:
            data = data_objs[attrs['data_name']].data
            x_len = data.loc[:, attrs['x_field']].map(len)
            y_len = data.loc[:, attrs['y_field']].map(len)
            z_shape = data.loc[:, attrs['z_field']].map(np.shape)
            color_shape = None if attrs['color_field'] is None else data.loc[:, attrs['color_field']].map(np.shape)
            if color_shape is not None and (z_shape != color_shape).any():
                return 'Every array in color_field must have the same shape as its corresponding array in z_field.'
            elif (x_len != z_shape.map(lambda s: s[1])).any():
                return 'Every array in x_field must have the same number of values as there are columns in z_field.'
            elif (y_len != z_shape.map(lambda s: s[0])).any():
                return 'Every array in y_field must have the same number of values as there are rows in z_field.'

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def update(self, data_obj, visuals, valid_idx, norm_limits, str_maps, color_limits):
        if self.visible and valid_idx.any():
            visual_input = self.get_current_data(data_obj, valid_idx, norm_limits, str_maps, color_limits)
            colors = visual_input.pop('colors')
            visuals[0].set_data(**visual_input)
            visuals[0].mesh_data.set_vertex_colors(colors)
            if not visuals[0].visible:
                visuals[0].visible = True
        elif visuals[0].visible:
            visuals[0].visible = False

class TextArtist(Artist):
    def __init__(self):
        super().__init__()
        self.artist_type = 'text'

    def get_current_data(self, data_obj, valid_idx, norm_limits, str_maps, color_limits):
        visual_input = {}
        visual_input['text'] = data_obj.data.loc[valid_idx, self.text_field].astype('str').to_numpy()
        x = self.field_to_numeric(data_obj, valid_idx, str_maps['x'], self.x_field, is_1d=True, norm_limits=norm_limits['x'])
        y = self.field_to_numeric(data_obj, valid_idx, str_maps['y'], self.y_field, is_1d=True, norm_limits=norm_limits['y'])
        z = self.field_to_numeric(data_obj, valid_idx, str_maps['z'], self.z_field, is_1d=True, norm_limits=norm_limits['z'])
        visual_input['pos'] = np.column_stack([x, y]) if z is None else np.column_stack([x, y, z])
        visual_input['color'] = self.create_color(data_obj, valid_idx, str_maps['color'], color_limits, self.color, self.color_field, self.colormap, self.color_label, self.color_unit, is_1d=True, get_last=False, to_shape=x.shape)
        return visual_input

    def get_legend_info(self, str_map, limits_source):
        return self.create_legend_default(str_map, limits_source, self.color, self.color_field, self.colormap, self.color_label, self.color_unit)

    def get_limits(self, data_obj, valid_idx, limit_type, is_time):
        if limit_type == 'x':
            return self.calc_limits(data_obj, valid_idx, self.x_field, is_1d=True)
        elif limit_type == 'y':
            return self.calc_limits(data_obj, valid_idx, self.y_field, is_1d=True)
        elif limit_type == 'z':
            return self.calc_limits(data_obj, valid_idx, self.z_field, is_1d=True)
        else:
            return self.calc_limits(data_obj, valid_idx, [self.color_field], is_1d=True, color_keys=[self.colormap, self.color_label, self.color_unit])

    def get_state(self, as_copy=True):
        state = {attr: getattr(self, attr, None) for attr in ['artist_type', 'name', 'data_name', 'text_field', 'x_field', 'y_field', 'z_field', 'visible', 'draw_order', 'legend_text',
                                                              'x_anchor', 'y_anchor', 'font_size', 'bold', 'italic', 'color', 'color_field', 'colormap', 'color_label', 'color_unit']}
        return copy.deepcopy(state) if as_copy else state

    def initialize(self, view):
        text = vpscene.Text(anchor_x=self.x_anchor, anchor_y=self.y_anchor, bold=self.bold, font_size=self.font_size, italic=self.italic, parent=view.scene)
        text.order = self.draw_order
        return [text]

    def set_state(self, data_objs, axis_type, artist_names, unit_reg, state):
        attrs = self.get_state(as_copy=False)
        data_changed = False

        # Validate parameters
        if 'name' in state and attrs['name'] is None:
            attrs['name'] = state['name']
            if not isinstance(attrs['name'], str):
                return 'name must be of type: str'
            elif attrs['name'] in artist_names:
                return 'Name "{}" is already in use.'.format(attrs['name'])
        if 'data_name' in state:
            attrs['data_name'] = state['data_name']
            if not isinstance(attrs['data_name'], str):
                return 'data_name must be of type: str'
            elif attrs['data_name'] not in data_objs:
                return '"{}" is not a valid data name.'.format(attrs['data_name'])
            data_changed = True
        for attr in ['text_field', 'x_field', 'y_field', 'z_field', 'color_field']:
            if attr in state or data_changed:
                if attr == 'z_field' and axis_type == '2d':
                    continue
                elif attr in state:
                    attrs[attr] = state[attr]
                err_msg = validators.validate_field(attr, data_objs, attrs['data_name'], attrs[attr], required_names=['text_field', 'x_field', 'y_field'], optional_names=['z_field', 'color_field'])
                if err_msg is not None:
                    return err_msg
        for attr in ['legend_text', 'color_label']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (type(None), str)):
                    return '{} must be one of the following types: None, str'
        for attr in ['x_anchor', 'y_anchor']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], str):
                    return '{} must be of type: str'.format(attr)
                elif attr == 'x_anchor' and attrs[attr] not in ['left', 'center', 'right']:
                    return '{} must be one of the following: "left", "center", "right"'.format(attr)
                elif attr == 'y_anchor' and attrs[attr] not in ['top', 'center', 'bottom']:
                    return '{} must be one of the following: "top", "center", "bottom"'.format(attr)
        for attr in ['draw_order', 'font_size']:
            if attr in state:
                attrs[attr] = state[attr]
                if not pd.api.types.is_numeric_dtype(type(attrs[attr])):
                    return '{} must be numeric.'.format(attr)
                attrs[attr] = attrs[attr].real
                if not np.isfinite(attrs[attr]):
                    return '{} must be finite.'.format(attr)
                elif attr == 'font_size' and 0 > attrs[attr]:
                    return '{} must be greater than or equal to 0.'.format(attr)
        if 'color' in state:
            attrs['color'] = state['color']
            err_msg = validators.validate_color('color', attrs['color'])
            if err_msg is not None:
                return err_msg
        if 'colormap' in state:
            attrs['colormap'] = state['colormap']
            err_msg = validators.validate_colormap('colormap', attrs['colormap'])
            if err_msg is not None:
                return err_msg
        if 'color_unit' in state:
            attrs['color_unit'], err_msg = validators.validate_unit('color_unit', unit_reg, state['color_unit'])
            if err_msg is not None:
                return err_msg
        for attr in ['visible', 'bold', 'italic']:
            if attr in state:
                attrs[attr] = state[attr]
                if not isinstance(attrs[attr], (bool, np.bool_)):
                    return '{} must be of type: bool'.format(attr)

        for attr in attrs:
            setattr(self, attr, attrs[attr])

    def update(self, data_obj, visuals, valid_idx, norm_limits, str_maps, color_limits):
        if self.visible and valid_idx.any():
            visual_input = self.get_current_data(data_obj, valid_idx, norm_limits, str_maps, color_limits)
            for attr in visual_input:
                setattr(visuals[0], attr, visual_input[attr])
            if not visuals[0].visible:
                visuals[0].visible = True
        elif visuals[0].visible:
            visuals[0].visible = False

def create_artist(artist_type):
    if artist_type == 'arrow':
        return ArrowArtist()
    elif artist_type == 'box':
        return BoxArtist()
    elif artist_type == 'ellipse':
        return EllipseArtist()
    elif artist_type == 'image':
        return ImageArtist()
    elif artist_type == 'infinite line':
        return InfiniteLineArtist()
    elif artist_type == 'polygon':
        return PolygonArtist()
    elif artist_type == 'rectangle':
        return RectangleArtist()
    elif artist_type == 'scatter':
        return ScatterArtist()
    elif artist_type == 'surface':
        return SurfaceArtist()
    elif artist_type == 'text':
        return TextArtist()
