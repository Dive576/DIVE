from . import custom_vispy
from .._utilities import helper_functions
import dateutil
import numpy as np
import pandas as pd
import vispy.scene as vpscene

class AxisInstance:
    """
    This class is an instance of a DIVEAxis object that contains the vispy objects for the axis.

    Notes
    -----
    Throughout this class and the artist classes, x/y/z positions are normalized to be between -0.5 and 0.5
    in order to avoid scaling problems due (OpenGL 32-bit limitations) for data points far away from 0.
    """
    def __init__(self, data_objs, axis_obj, grid_cell, apply_limits_filter, theme, label_size, tick_size):
        self.state = axis_obj.get_state()
        self.artists = {}
        self.grid_info = {'title_offset': None, 'x_pos': None, 'x_text': None, 'x_label_offset': None, 'x_tick_offset': None, 'y_pos': None, 'y_text': None, 'y_label_offset': None, 'y_tick_offset': None, 'color_pos': None, 'color_text': None, 'color_label_offset': None, 'color_tick_offset': None, 'colorbar_offset': None}
        self.current_color_key = None
        self.timezone = 'UTC'
        self.unit_reg = None
        self.str_maps = {}
        self.label_cache = {}
        self.tick_cache = {}
        self.axis_text_padding = 10

        self.limits_all, self.str_maps_all, self.limits_source_all = self.get_artist_limits(data_objs, axis_obj, 'all')
        self.limits_filter, self.str_maps_filter, self.limits_source_filter = self.get_artist_limits(data_objs, axis_obj, 'filter')

        self.view = grid_cell.add_widget(custom_vispy.ViewBox(self, camera=custom_vispy.Camera_2D() if axis_obj.axis_type == '2d' else custom_vispy.Camera_3D(fov=0.0)))
        for artist_obj in axis_obj.artists.values():
            self.artists[artist_obj.name] = artist_obj.initialize(self.view)
        self.labels_3d = vpscene.Text(bold=True)
        self.ticks_3d = vpscene.Text()
        if isinstance(self.view.camera, custom_vispy.Camera_3D):
            self.labels_3d.parent = self.ticks_3d.parent = self.view.scene
        self.gridlines = vpscene.Line(pos=np.array([[0, 0]]), color='grey', connect='segments', parent=self.view.scene)
        self.colorbar = vpscene.ColorBar(cmap='viridis', orientation='right', size=[1, 0.5], parent=self.view.parent)
        for sv in [self.colorbar._border, self.colorbar._ticks[0], self.colorbar._ticks[1], self.colorbar._label]:
            self.colorbar.remove_subvisual(sv)
        self.colorbar.interactive = True

        self.filter_limits(None, axis_obj, apply_limits_filter)
        self.reset_camera_limits()
        self.set_theme(axis_obj, theme)
        self.set_font_sizes(label_size, tick_size)

    def autoscale_camera_limits(self, data_objs, axis_obj, valid_idx, current_time, hold_time):
        limits, _, _ = self.get_artist_limits(data_objs, axis_obj, 'time', valid_idx, current_time, hold_time)
        self.set_camera_limits(limits)

    def cycle_color_key(self):
        prev_cmap = None if self.current_color_key is None else self.current_color_key[0]
        keys = [key for key, val in self.limits_source['color'].items() if val != 'str']
        if len(keys) == 0:
            self.current_color_key = None
        elif self.current_color_key is None:
            self.current_color_key = keys[0]
        else:
            n_keys = len(keys)
            for i, key in enumerate(keys):
                if key == self.current_color_key:
                    self.current_color_key = keys[(i + 1) % n_keys]
                    break
        if self.current_color_key is not None and prev_cmap != self.current_color_key[0]:
            self.colorbar.cmap = self.current_color_key[0]

    def filter_limits(self, data_objs, axis_obj, apply_limits_filter):
        if data_objs is not None:
            self.limits_filter, self.str_maps_filter, self.limits_source_filter = self.get_artist_limits(data_objs, axis_obj, 'filter')
        if apply_limits_filter:
            self.limits, self.str_maps, self.limits_source = self.limits_filter, self.str_maps_filter, self.limits_source_filter
            if self.current_color_key not in self.limits_source['color']:
                self.current_color_key = None
        else:
            self.limits, self.str_maps, self.limits_source = self.limits_all, self.str_maps_all, self.limits_source_all
        if self.current_color_key is None:
            self.cycle_color_key()

    def get_artist_legend(self, data_objs, axis_obj, apply_limits_filter):
        entries = []
        for artist in axis_obj.artists.values():
            if (artist.visible or not apply_limits_filter) and artist.legend_text is not None and (artist.data_name is None or data_objs[artist.data_name].filtered_idx.any()):
                artist_icon, artist_subentries = artist.get_legend_info(self.str_maps['color'], self.limits_source['color'])
                entries.append((artist.legend_text, artist_icon, artist_subentries))
        return entries

    def get_artist_limits(self, data_objs, axis_obj, scope, valid_idx=None, current_time=None, hold_time=None):
        temp_key = 0 # Using temp_key for x, y, and z simplifies the code for combining limits
        limits = {'x': {temp_key: []}, 'y': {temp_key: []}, 'z': {temp_key: []}, 'color': {}}
        str_maps = {'x': {temp_key: []}, 'y': {temp_key: []}, 'z': {temp_key: []}, 'color': {}}
        limits_source = {'x': {temp_key: []}, 'y': {temp_key: []}, 'z': {temp_key: []}, 'color': {}}

        # Get limits for each artist
        for artist_obj in axis_obj.artists.values():
            if scope in ['filter', 'time'] and not artist_obj.visible:
                continue
            data_obj = data_objs.get(artist_obj.data_name, None)
            is_time = False
            if scope == 'filter':
                idx = data_obj.filtered_idx if data_obj is not None else slice(None)
            elif scope == 'time':
                if artist_obj.data_name is not None and artist_obj.data_name not in valid_idx:
                    valid_idx[artist_obj.data_name] = data_obj.get_valid_idx(current_time, hold_time)
                idx = valid_idx.get(artist_obj.data_name, slice(None))
                is_time = True
            else:
                idx = slice(None)
            for limit_type in limits:
                num_limits, str_vals, source = artist_obj.get_limits(data_obj, idx, limit_type, is_time)
                if limit_type == 'color':
                    for key in num_limits:
                        limits[limit_type][key] = limits[limit_type].get(key, []) + num_limits[key]
                    for key in str_vals:
                        str_maps[limit_type][key] = str_maps[limit_type].get(key, []) + str_vals[key]
                    for key in source:
                        limits_source[limit_type][key] = limits_source[limit_type].get(key, []) + source[key]
                else:
                    limits[limit_type][temp_key] += num_limits
                    str_maps[limit_type][temp_key] += str_vals
                    limits_source[limit_type][temp_key] += source

        # Combine limits of all artists
        for limit_type in limits:
            for key in str_maps[limit_type]:
                unique_strs = np.unique(str_maps[limit_type][key]).tolist()
                unique_strs.sort(key=helper_functions.natural_order)
                n_strs = len(unique_strs)
                str_maps[limit_type][key] = pd.Series(np.arange(n_strs), index=unique_strs)
                if n_strs > 0:
                    if scope == 'time':
                        current_map = self.str_maps[limit_type][key] if limit_type == 'color' else self.str_maps[limit_type]
                        current_map = current_map.loc[unique_strs]
                        limits[limit_type][key] += [np.min(current_map), np.max(current_map)]
                    else:
                        limits[limit_type][key] += [0, n_strs - 1]
            for key in limits[limit_type]:
                if len(limits[limit_type][key]) > 0:
                    limits[limit_type][key] = [np.min(limits[limit_type][key]), np.max(limits[limit_type][key])]
                    if limits[limit_type][key][0] == limits[limit_type][key][1]:
                        limits[limit_type][key][0] -= 1
                        limits[limit_type][key][1] += 1
                else:
                    limits[limit_type][key] = [0, 1]
            for key in limits_source[limit_type]:
                unique_sources = set(limits_source[limit_type][key])
                if len(unique_sources) > 1:
                    print('Warning: {}-axis in "{}" is using multiple data types.'.format(limit_type, self.state['name']))
                    for s in ['str', 'date']:
                        if s in unique_sources:
                            limits_source[limit_type][key] = s
                            break
                else:
                    limits_source[limit_type][key] = 'num' if len(unique_sources) == 0 else unique_sources.pop()

        for key in ['x', 'y', 'z']:
            limits[key] = limits[key][temp_key]
            str_maps[key] = str_maps[key][temp_key]
            limits_source[key] = limits_source[key][temp_key]

        return limits, str_maps, limits_source

    def get_artist_selected(self, data_objs, axis_obj, current_time, hold_time, vertices):
        output, valid_idx = {}, {}
        norm_limits = self.limits_all if isinstance(self.view.camera, custom_vispy.Camera_2D) else self.limits
        for artist_obj in axis_obj.artists.values():
            if artist_obj.data_name is not None and artist_obj.visible and artist_obj.selectable:
                if artist_obj.data_name not in valid_idx:
                    valid_idx[artist_obj.data_name] = data_objs[artist_obj.data_name].get_valid_idx(current_time, hold_time)
                artist_coords = artist_obj.get_coordinates(data_objs[artist_obj.data_name], valid_idx[artist_obj.data_name], norm_limits, self.str_maps)
                if artist_coords is not None:
                    # Get points inside polygon defined by vertices
                    conv_coords = self.view.scene.node_transform(self.view.canvas.scene).map(artist_coords)[:, :2]
                    x, y = conv_coords[:, 0], conv_coords[:, 1]
                    selected = np.zeros(conv_coords.shape[0], 'bool')
                    output_idx = np.zeros(len(valid_idx[artist_obj.data_name]), 'bool')
                    x1, y1 = vertices[0]
                    intersect_x = 0.0
                    for x2, y2 in vertices:
                        idx = np.nonzero((x <= max(x1, x2)) & (y > min(y1, y2)) & (y <= max(y1, y2)))[0]
                        if len(idx) > 0:
                            if y1 != y2:
                                intersect_x = (y[idx] - y1) * (x2 - x1) / (y2 - y1) + x1
                            if x1 != x2:
                                idx = idx[x[idx] <= intersect_x]
                            selected[idx] = ~selected[idx]
                        x1, y1 = x2, y2
                    output_idx[valid_idx[artist_obj.data_name]] = selected
                    output[artist_obj.data_name] = np.logical_or(output[artist_obj.data_name], output_idx) if artist_obj.data_name in output else output_idx
        return output

    def get_camera_limits_2d(self):
        if isinstance(self.view.camera, custom_vispy.Camera_2D):
            rect = self.view.camera.rect
            # Reverse the normalization
            x_min = (rect.left + 0.5) * (self.limits_all['x'][1] - self.limits_all['x'][0]) + self.limits_all['x'][0]
            x_max = (rect.right + 0.5) * (self.limits_all['x'][1] - self.limits_all['x'][0]) + self.limits_all['x'][0]
            y_min = (rect.bottom + 0.5) * (self.limits_all['y'][1] - self.limits_all['y'][0]) + self.limits_all['y'][0]
            y_max = (rect.top + 0.5) * (self.limits_all['y'][1] - self.limits_all['y'][0]) + self.limits_all['y'][0]
            return x_min, x_max, y_min, y_max
        return None, None, None, None

    def get_label(self, label, source, unit):
        if label is None or len(label) == 0:
            if source == 'date':
                return '({})'.format(self.timezone)
            return None if unit is None else '({})'.format(unit[1])
        else:
            if source == 'date':
                return '{} ({})'.format(label, self.timezone)
            return label if unit is None else '{} ({})'.format(label, unit[1])

    def get_spacing(self):
        label_scale = self.view.canvas.label_font_size / 72 * self.view.canvas.dpi
        tick_scale = self.view.canvas.tick_font_size / 72 * self.view.canvas.dpi
        if self.current_color_key is not None:
            colorbar_label = self.get_label(self.current_color_key[1], self.limits_source['color'][self.current_color_key], self.current_color_key[2])
            self.grid_info['color_pos'], color_time_interval = self.get_tick_location(self.limits['color'][self.current_color_key][0], self.limits['color'][self.current_color_key][1], False, self.limits_source['color'][self.current_color_key], self.str_maps['color'][self.current_color_key], self.current_color_key[2])
            self.grid_info['color_text'] = self.get_tick_format(self.grid_info['color_pos'], self.limits_source['color'][self.current_color_key], color_time_interval, self.str_maps['color'][self.current_color_key], self.current_color_key[2])
            self.grid_info['color_label_offset'] = np.ptp(label_scale * self.get_text_bbox(colorbar_label, self.view.canvas.labels_2d._font, self.view.canvas.labels_2d._font._lowres_size, self.label_cache)[:, 1]) + self.axis_text_padding if colorbar_label is not None else 0
            self.grid_info['color_tick_offset'] = np.array([np.ptp(tick_scale * self.get_text_bbox(val, self.view.canvas.ticks_2d._font, self.view.canvas.ticks_2d._font._lowres_size, self.tick_cache)[:, 0]) + self.axis_text_padding for val in self.grid_info['color_text']])
            self.grid_info['colorbar_offset'] = self.view.parent.size[0] * 0.02
        else:
            self.grid_info['color_label_offset'] = 0
            self.grid_info['color_tick_offset'] = 0
            self.grid_info['colorbar_offset'] = 0
        self.grid_info['title_offset'] =  np.ptp(label_scale * self.get_text_bbox(self.state['title'], self.view.canvas.labels_2d._font, self.view.canvas.labels_2d._font._lowres_size, self.label_cache)[:, 1]) + self.axis_text_padding if self.state['title'] is not None else self.axis_text_padding
        left, right, top, bottom = 0, np.max(self.grid_info['color_tick_offset']) + self.grid_info['color_label_offset'] + self.grid_info['colorbar_offset'] + self.axis_text_padding, self.grid_info['title_offset'], 0
        if isinstance(self.view.camera, custom_vispy.Camera_2D):
            x_min, x_max, y_min, y_max = self.get_camera_limits_2d() # Get non-normalized limits

            x_label = self.get_label(self.state['x_label'], self.limits_source['x'], self.state['x_unit'])
            self.grid_info['x_pos'], x_time_interval = self.get_tick_location(x_min, x_max, True, self.limits_source['x'], self.str_maps['x'], self.state['x_unit'])
            self.grid_info['x_text'] = self.get_tick_format(self.grid_info['x_pos'], self.limits_source['x'], x_time_interval, self.str_maps['x'], self.state['x_unit'])
            self.grid_info['x_label_offset'] = np.ptp(label_scale * self.get_text_bbox(x_label, self.view.canvas.labels_2d._font, self.view.canvas.labels_2d._font._lowres_size, self.label_cache)[:, 1]) + self.axis_text_padding if x_label is not None else 0
            self.grid_info['x_tick_offset'] = np.array([np.ptp(tick_scale * self.get_text_bbox(val, self.view.canvas.ticks_2d._font, self.view.canvas.ticks_2d._font._lowres_size, self.tick_cache)[:, 1]) + self.axis_text_padding for val in self.grid_info['x_text']])
            # Perform normalization
            self.grid_info['x_pos'] = -0.5 + (self.grid_info['x_pos'] - self.limits_all['x'][0]) / (self.limits_all['x'][1] - self.limits_all['x'][0])
            bottom = self.grid_info['x_label_offset'] + (np.max(self.grid_info['x_tick_offset']) if len(self.grid_info['x_tick_offset']) > 0 else 0)

            y_label = self.get_label(self.state['y_label'], self.limits_source['y'], self.state['y_unit'])
            self.grid_info['y_pos'], y_time_interval = self.get_tick_location(y_min, y_max, False, self.limits_source['y'], self.str_maps['y'], self.state['y_unit'])
            self.grid_info['y_text'] = self.get_tick_format(self.grid_info['y_pos'], self.limits_source['y'], y_time_interval, self.str_maps['y'], self.state['y_unit'])
            self.grid_info['y_label_offset'] = np.ptp(label_scale * self.get_text_bbox(y_label, self.view.canvas.labels_2d._font, self.view.canvas.labels_2d._font._lowres_size, self.label_cache)[:, 1]) + self.axis_text_padding if y_label is not None else 0
            self.grid_info['y_tick_offset'] = np.array([np.ptp(tick_scale * self.get_text_bbox(val, self.view.canvas.ticks_2d._font, self.view.canvas.ticks_2d._font._lowres_size, self.tick_cache)[:, 0]) + self.axis_text_padding for val in self.grid_info['y_text']])
            # Perform normalization
            self.grid_info['y_pos'] = -0.5 + (self.grid_info['y_pos'] - self.limits_all['y'][0]) / (self.limits_all['y'][1] - self.limits_all['y'][0])
            left = self.grid_info['y_label_offset'] + (np.max(self.grid_info['y_tick_offset']) if len(self.grid_info['y_tick_offset']) > 0 else 0)
        return (left, right, top, bottom)

    def get_text_bbox(self, text, font, lowres_size, cache):
        """
        This is a modified version of vispy.visuals.text.text._text_to_vbo
        """
        if text in cache:
            return cache[text]
        vertices = np.zeros((len(text) * 4, 2), dtype='float32')
        prev = None
        width = height = ascender = descender = 0
        ratio, slop = 1. / font.ratio, font.slop
        x_off = -slop

        for char in 'hy':
            glyph = font[char]
            y0 = glyph['offset'][1] * ratio + slop
            y1 = y0 - glyph['size'][1]
            ascender = max(ascender, y0 - slop)
            descender = min(descender, y1 + slop)
            height = max(height, glyph['size'][1] - 2*slop)

        glyph = font[' ']
        spacewidth = glyph['advance'] * ratio
        lineheight = height * 1.5

        esc_seq = {7: 0, 8: 0, 9: -4, 10: 1, 11: 4, 12: 0, 13: 0}

        y_offset = vi_marker = ii_offset = vi = 0

        for ii, char in enumerate(text):
            ord_char = ord(char)
            if ord_char in esc_seq:
                esc_ord = esc_seq[ord_char]
                if esc_ord < 0:
                    abs_esc = abs(esc_ord) * spacewidth
                    x_off += abs_esc
                    width += abs_esc
                elif esc_ord > 0:
                    dx = -width / 2.
                    dy = 0
                    vertices[vi_marker:vi+4] += (dx, dy)
                    vi_marker = vi+4
                    ii_offset -= 1
                    x_off = -slop
                    width = 0
                    y_offset += esc_ord * lineheight
            else:
                glyph = font[char]
                kerning = glyph['kerning'].get(prev, 0.) * ratio
                x0 = x_off + glyph['offset'][0] * ratio + kerning
                y0 = glyph['offset'][1] * ratio + slop - y_offset
                x1 = x0 + glyph['size'][0]
                y1 = y0 - glyph['size'][1]
                position = [[x0, y0], [x0, y1], [x1, y1], [x1, y0]]
                vi = (ii + ii_offset) * 4
                vertices[vi:vi+4] = position
                x_move = glyph['advance'] * ratio + kerning
                x_off += x_move
                ascender = max(ascender, y0 - slop)
                descender = min(descender, y1 + slop)
                width += x_move
                prev = char

        dx = -width / 2.
        dy = (-descender - ascender) / 2

        vertices[0:vi_marker] += (0, dy)
        vertices[vi_marker:] += (dx, dy)
        vertices /= lowres_size

        cache[text] = vertices
        return vertices

    def get_tick_format(self, ticks, tick_type, time_interval, str_map, unit):
        """
        Get the text for every tick position.
        """
        if len(ticks) == 0:
            return np.array([], dtype='str')
        if self.unit_reg is not None and unit is not None and tick_type == 'num':
            ticks = self.unit_reg.Quantity(ticks, unit[0]).to(unit[1]).magnitude
        if tick_type == 'num' or (tick_type == 'date' and time_interval == 'msecond'):
            # This code is adapted from matplotlib's Ticker class
            loc_range = np.ptp(ticks)
            loc_range_oom = int(np.floor(np.log10(loc_range)))
            sigfigs = max(0, 3 - loc_range_oom)
            thresh = 1e-3 * 10 ** loc_range_oom
            while sigfigs >= 0:
                if np.abs(ticks - np.round(ticks, decimals=sigfigs)).max() < thresh:
                    sigfigs -= 1
                else:
                    break
            sigfigs += 1
        if tick_type == 'num':
            return np.char.mod('%1.{}f'.format(sigfigs), ticks)
        elif tick_type == 'date':
            interval_map = {'year': '%Y', 'month': '%m/%Y', 'day': '%m/%d\n%Y', 'hour': '%H:%M\n%m/%d/%Y', 'minute': '%H:%M\n%m/%d/%Y', 'second': '%H:%M:%S\n%m/%d/%Y', 'msecond': '%H:%M:\n%m/%d/%Y'}
            times = pd.to_datetime((ticks * 1e9).astype('int64'), utc=True).tz_convert(self.timezone)
            if time_interval == 'msecond':
                secs = iter(np.char.mod('%0{}.{}f\n'.format(sigfigs + 3, sigfigs), times.second + times.microsecond / 1e6))
            times = times.strftime(interval_map[time_interval])
            trim_idx = times.str.extract('\n(.*)').duplicated(keep='first')
            output = times.to_numpy(dtype='object')
            if time_interval == 'msecond':
                output[:] = times[:].str.replace('\n', lambda _: next(secs))
            output[trim_idx] = times[trim_idx].str.replace('\n.*', '', regex=True)
            return output.astype('str')
        elif tick_type == 'str':
            return str_map.index[ticks].to_numpy(dtype='str')

    def get_tick_location(self, vmin, vmax, horizontal, tick_type, str_map, unit):
        """
        Get the tick positions based on the visible axis limits.
        """
        time_interval = 'msecond'
        dim_idx, tick_mult = (0, 6 if tick_type == 'date' else 3) if horizontal else (1, 2)
        length = (self.view.parent.size[dim_idx] / self.view.canvas.dpi) * 72
        space = int(np.floor(length / (self.view.canvas.tick_font_size * tick_mult))) if self.view.canvas.tick_font_size > 0 else 100
        if tick_type == 'date':
            edge_offset = pd.DateOffset(years=1)
            clip_vmin, clip_vmax = np.clip([vmin, vmax], (pd.Timestamp.min + edge_offset).normalize().timestamp(), (pd.Timestamp.max.replace(nanosecond=0) - edge_offset).normalize().timestamp())
            if clip_vmin == clip_vmax:
                return np.array([]), time_interval
            clip_dmin, clip_dmax = pd.Timestamp(clip_vmin * 1e9, tz='UTC').replace(nanosecond=0).tz_convert(self.timezone).to_pydatetime(), pd.Timestamp(clip_vmax * 1e9, tz='UTC').replace(nanosecond=0).tz_convert(self.timezone).to_pydatetime()
            delta = dateutil.relativedelta.relativedelta(clip_dmax, clip_dmin)
            tdelta = clip_dmax - clip_dmin
            nums = [delta.years]
            nums.append(nums[-1] * 12 + delta.months)
            nums.append(tdelta.days)
            nums.append(nums[-1] * 24 + delta.hours)
            nums.append(nums[-1] * 60 + delta.minutes)
            nums.append(int(np.floor(tdelta.total_seconds())))
            freq = ['YS', 'MS', 'D', 'H', 'T', 'S']
            freq_map = {'YS': 'year', 'MS': 'month', 'D': 'day', 'H': 'hour', 'T': 'minute', 'S': 'second'}
            intervals = [[1, 2, 4, 5, 10, 20, 40, 50, 100], [1, 2, 3, 4, 6], [1, 2, 4, 7, 14], [1, 2, 3, 4, 6, 12], [1, 2, 5, 10, 15, 30], [1, 2, 5, 10, 15, 30]]
            maxticks = [10, 11, 10, 11, 10, 10]
            byranges = [None, range(1, 13), range(1, 32), range(0, 24), range(0, 60), range(0, 60)]
            for i in range(len(nums)):
                if nums[i] < 5:
                    continue
                for interval in intervals[i]:
                    if nums[i] <= interval * np.clip(space, 1, maxticks[i]):
                        break
                if i == 0:
                    byrange = list(range(clip_dmin.year // interval * interval, clip_dmax.year // interval * interval + 1, interval))
                else:
                    byrange = list(byranges[i][::interval])
                    if i == 2 and (interval == 7 or interval == 14):
                        byrange = byrange[:-1]
                ticks = pd.date_range(clip_dmin.replace(tzinfo=None), clip_dmax.replace(tzinfo=None), freq=freq[i]).tz_localize(self.timezone, ambiguous=False, nonexistent='shift_backward').floor(freq='D' if freq[i] in ['YS', 'MS'] else freq[i])
                ticks = ticks[np.isin(getattr(ticks, freq_map[freq[i]]), byrange)].astype('int64') / 1e9
                return ticks[(ticks >= clip_vmin) & (ticks <= clip_vmax)], freq_map[freq[i]]

            # Use numerical tick calculation for ranges less than one second
            tick_type = 'num'
            unit = None
        if tick_type == 'num':
            # This block of code is adapted from matplotlib's Ticker class
            if self.unit_reg is not None and unit is not None:
                vmin, vmax = self.unit_reg.Quantity(vmin, unit[0]).to(unit[1]).magnitude, self.unit_reg.Quantity(vmax, unit[0]).to(unit[1]).magnitude

            if (not np.isfinite(vmin)) or (not np.isfinite(vmax)):
                vmin, vmax = -1e-13, 1e-13
            if vmax < vmin:
                vmin, vmax = vmax, vmin
            vmin, vmax = map(float, [vmin, vmax])
            maxabsvalue = max(np.abs(vmin), np.abs(vmax))
            if maxabsvalue < 1e20 * np.finfo('float').tiny:
                vmin, vmax = -1e-13, 1e-13
            elif vmax - vmin <= maxabsvalue * 1e-14:
                if vmin == 0 and vmax == 0:
                    vmin, vmax = -1e-13, 1e-13
                else:
                    vmin -= 1e-13 * np.abs(vmin)
                    vmax += 1e-13 * np.abs(vmax)

            nbins = np.clip(space, 1, 9)
            dv = np.abs(vmax - vmin)
            meanv = (vmax + vmin) / 2
            if np.abs(meanv) / dv < 100:
                offset = 0
            else:
                offset = np.copysign(10 ** (np.log10(np.abs(meanv)) // 1), meanv)
            scale = 10 ** (np.log10(dv / nbins) // 1)

            offset_vmin = vmin - offset
            offset_vmax = vmax - offset
            raw_step = (offset_vmax - offset_vmin) / nbins
            steps = np.array([0.1, 0.2, 0.25, 0.5, 1.0, 2.0, 2.5, 5.0, 10.0, 20.0]) * scale
            istep = np.nonzero(steps >= raw_step)[0][0]

            tol = lambda ms, edge: min(0.4999, max(1e-10, 10 ** (np.log10(np.abs(offset) / step) - 12))) if offset > 0 else 1e-10
            for istep in reversed(range(istep + 1)):
                step = steps[istep]
                best_vmin = (offset_vmin // step) * step
                d, m = divmod(offset_vmin - best_vmin, step)
                low = d + 1 if np.abs(m / step - 1) < tol(m / step, 1) else d
                d, m = divmod(offset_vmax - best_vmin, step)
                high = d if np.abs(m / step) < tol(m / step, 0) else d + 1
                ticks = np.arange(low, high + 1) * step + best_vmin
                if ((ticks <= offset_vmax) & (ticks >= offset_vmin)).sum() >= 2:
                    break
            ticks += offset
            ticks = ticks[(ticks >= vmin) & (ticks <= vmax)]

            if self.unit_reg is not None and unit is not None:
                ticks = self.unit_reg.Quantity(ticks, unit[1]).to(unit[0]).magnitude
            return ticks, time_interval
        elif tick_type == 'str':
            ticks = np.arange(np.ceil(vmin), np.floor(vmax) + 1, dtype='int')
            return ticks[(ticks >= str_map.iat[0]) & (ticks <= str_map.iat[-1])], time_interval

    def reset_camera_limits(self):
        self.set_camera_limits(self.limits)

    def set_camera_limits(self, limits, apply_norm=True, no_margin=False):
        if apply_norm:
            norm_limits = self.limits_all if isinstance(self.view.camera, custom_vispy.Camera_2D) else self.limits
            # Perform normalization
            x_limits = np.clip(-0.5 + (np.array(limits['x']) - norm_limits['x'][0]) / (norm_limits['x'][1] - norm_limits['x'][0]), -0.55, 0.55)
            y_limits = np.clip(-0.5 + (np.array(limits['y']) - norm_limits['y'][0]) / (norm_limits['y'][1] - norm_limits['y'][0]), -0.55, 0.55)
            z_limits = np.clip(-0.5 + (np.array(limits['z']) - norm_limits['z'][0]) / (norm_limits['z'][1] - norm_limits['z'][0]), -0.55, 0.55)
            if no_margin:
                self.view.camera.set_range(x=x_limits, y=y_limits, z=z_limits, margin=1e-45)
            else:
                self.view.camera.set_range(x=x_limits, y=y_limits, z=z_limits)
        else:
            self.view.camera.set_range(x=limits['x'], y=limits['y'], z=limits['z'], margin=1e-45)

    def set_font_sizes(self, label_size, tick_size):
        self.label_cache, self.tick_cache = {}, {}
        if isinstance(self.view.camera, custom_vispy.Camera_3D):
            self.labels_3d.font_size = label_size
            self.ticks_3d.font_size = tick_size

    def set_theme(self, axis_obj, theme):
        color = 'w' if theme == 'dark' else 'k'
        if isinstance(self.view.camera, custom_vispy.Camera_2D):
            self.view.border_color = color
        else:
            self.labels_3d.color = color
            self.ticks_3d.color = color
        for artist_obj in axis_obj.artists.values():
            artist_obj.set_theme(self.artists[artist_obj.name], theme)

    def update_artists(self, data_objs, axis_obj, valid_idx, current_time, hold_time, timezone, unit_reg, time_updated):
        self.timezone = timezone
        self.unit_reg = unit_reg
        for artist_obj in axis_obj.artists.values():
            if not ((artist_obj.data_name is None or data_objs[artist_obj.data_name].time_field is None) and time_updated): # If time was updated, don't bother updating artists that don't use a data object with a time field
                if artist_obj.data_name is not None and artist_obj.data_name not in valid_idx:
                    valid_idx[artist_obj.data_name] = data_objs[artist_obj.data_name].get_valid_idx(current_time, hold_time)
                norm_limits = self.limits_all if isinstance(self.view.camera, custom_vispy.Camera_2D) else self.limits
                artist_obj.update(data_objs.get(artist_obj.data_name), self.artists[artist_obj.name], valid_idx.get(artist_obj.data_name), norm_limits, self.str_maps, self.limits['color'])
                if time_updated and self.state['time_autoscale']:
                    self.autoscale_camera_limits(data_objs, axis_obj, valid_idx, current_time, hold_time)

    def update_grid(self):
        """
        Update the gridlines (as well the label/tick text if this is a 3D axis).
        """
        show_colorbar = self.current_color_key is not None
        if show_colorbar:
            self.colorbar.pos = [self.view.pos[0] + self.view.size[0] + self.grid_info['colorbar_offset'] / 2 + 3, self.view.pos[1] + self.view.size[1] / 2]
            self.colorbar.size = [max(self.view.size[1] * 0.95, self.grid_info['colorbar_offset']), self.grid_info['colorbar_offset']]
        if show_colorbar != self.colorbar.visible:
            self.colorbar.visible = show_colorbar
        if isinstance(self.view.camera, custom_vispy.Camera_2D):
            rect = self.view.camera.rect
            x_min, x_max, y_min, y_max = rect.left, rect.right, rect.bottom, rect.top
            pos = []
            if self.state['x_grid']:
                pos += list(zip(np.repeat(self.grid_info['x_pos'], 2), np.tile([y_min, y_max], len(self.grid_info['x_pos']))))
            if self.state['y_grid']:
                pos += list(zip(np.tile([x_min, x_max], len(self.grid_info['y_pos'])), np.repeat(self.grid_info['y_pos'], 2)))
            self.gridlines.set_data(pos=np.array(pos if len(pos) > 0 else [[0, 0]]))
        else:
            cam_az = self.view.camera.azimuth if abs(self.view.camera.azimuth) != 180 else 180
            cam_el = self.view.camera.elevation
            label_scale = self.view.canvas.label_font_size / 72 * self.view.canvas.dpi
            tick_scale = self.view.canvas.tick_font_size / 72 * self.view.canvas.dpi
            tr = self.view.scene.node_transform(self.view.canvas.scene)
            x_min, x_max, y_min, y_max, z_min, z_max = self.limits['x'][0], self.limits['x'][1], self.limits['y'][0], self.limits['y'][1], self.limits['z'][0], self.limits['z'][1]
            x_offset, y_offset, z_offset = abs(x_max - x_min) * 0.05, abs(y_max - y_min) * 0.05, abs(z_max - z_min) * 0.05
            x_min, x_max, y_min, y_max, z_min, z_max = x_min - x_offset, x_max + x_offset, y_min - y_offset, y_max + y_offset, z_min - z_offset, z_max + z_offset
            x_plane, x_inv = (x_min, x_max) if cam_az > 0 else (x_max, x_min)
            y_plane, y_inv = (y_max, y_min) if -90 < cam_az <= 90 else (y_min, y_max)
            z_plane, z_inv = (z_min, z_max) if cam_el >= 0 else (z_max, z_min)

            lines = tr.map(np.column_stack([[x_inv, x_inv, x_min, x_max], [y_min, y_max, y_inv, y_inv], [z_plane, z_plane, z_plane, z_plane]]))
            x_line_angle, y_line_angle = np.arctan2(abs(lines[1, 1] - lines[0, 1]), abs(lines[1, 0] - lines[0, 0])), np.arctan2(abs(lines[3, 1] - lines[2, 1]), abs(lines[3, 0] - lines[2, 0]))
            x_label_angle = y_line_angle * (1 if cam_el >= 0 else -1)
            y_label_angle = x_line_angle * (1 if cam_el >= 0 else -1)
            z_label_angle = np.pi / 2
            x_angle = (x_line_angle if abs(cam_el) >= 15 else np.pi / 2) * (1 if cam_el >= 0 else -1)
            y_angle = (y_line_angle if abs(cam_el) >= 15 else np.pi / 2) * (1 if cam_el >= 0 else -1)
            z_angle = (x_line_angle if 45 < (cam_az % 180) <= 135 else y_line_angle) * (1 if cam_el >= 0 else -1)
            if 0 < (cam_az % 180) <= 90: # left side is x
                x_angle *= -1
                y_label_angle *= -1
                x_cos_sign, x_sin_sign = (-1, 1) if abs(cam_el) >= 15 else (1, -1)
            else: # left side is y
                y_angle *= -1
                x_label_angle *= -1
                x_cos_sign, x_sin_sign = (1, -1) if abs(cam_el) >= 15 else (-1, 1)
            x_sin, x_cos, y_sin, y_cos = np.sin(-x_angle % (2 * np.pi)), np.cos(-x_angle % (2 * np.pi)), np.sin(-y_angle % (2 * np.pi)), np.cos(-y_angle % (2 * np.pi))

            grid_pos, label_pos, label_text, label_angle, tick_pos, tick_text, tick_angle = [], [], [], [], [], [], []

            # X Axis
            x_pos, x_time_interval = self.get_tick_location(x_min, x_max, True, self.limits_source['x'], self.str_maps['x'], self.state['x_unit'])
            if self.state['x_grid']:
                grid_pos += list(zip(np.repeat(x_pos, 2), np.tile([y_min, y_max], len(x_pos)), np.tile([z_plane, z_plane], len(x_pos)))) + list(zip(np.repeat(x_pos, 2), np.tile([y_plane, y_plane], len(x_pos)), np.tile([z_min, z_max], len(x_pos))))
            tick_text.append(self.get_tick_format(x_pos, self.limits_source['x'], x_time_interval, self.str_maps['x'], self.state['x_unit']))
            if self.limits_source['x'] == 'date':
                if abs(cam_el) >= 15:
                    tick_text[-1] = np.array([' '.join(reversed(val)) for val in np.char.split(tick_text[-1], '\n')]) if 0 < (cam_az % 180) <= 90 else np.array([' '.join(val) for val in np.char.split(tick_text[-1], '\n')])
                else:
                    tick_text[-1] = np.array([' '.join(val) for val in np.char.split(tick_text[-1], '\n')]) if 0 < (cam_az % 180) <= 90 else np.array([' '.join(reversed(val)) for val in np.char.split(tick_text[-1], '\n')])
            label_text.append(self.get_label(self.state['x_label'], self.limits_source['x'], self.state['x_unit']))
            x_label_offset = (np.ptp(label_scale * self.get_text_bbox(label_text[-1], self.labels_3d._font, self.labels_3d._font._lowres_size, self.label_cache)[:, 1]) + self.axis_text_padding) / 2 if label_text[-1] is not None else 0
            x_tick_offset = np.array([np.ptp(tick_scale * self.get_text_bbox(val, self.ticks_3d._font, self.ticks_3d._font._lowres_size, self.tick_cache)[:, 0]) + self.axis_text_padding for val in tick_text[-1]]) / 2
            x_label_offset += np.max(x_tick_offset) * 2
            label_pos.append(np.array([[(x_min + x_max) / 2, y_inv, z_plane]]) if abs(cam_el) >= 15 else np.array([[(x_min + x_max) / 2, y_plane, z_inv]]))
            tick_pos.append(np.column_stack([x_pos, [y_inv] * len(x_pos), [z_plane] * len(x_pos)]) if abs(cam_el) >= 15 else np.column_stack([x_pos, [y_plane] * len(x_pos), [z_inv] * len(x_pos)]))
            for i, val in enumerate(['x', 'y', 'z']):
                label_pos[-1][:, i] = -0.5 + (label_pos[-1][:, i] - self.limits[val][0]) / (self.limits[val][1] - self.limits[val][0])
                tick_pos[-1][:, i] = -0.5 + (tick_pos[-1][:, i] - self.limits[val][0]) / (self.limits[val][1] - self.limits[val][0])
            label_pos[-1], tick_pos[-1] = tr.map(label_pos[-1]), tr.map(tick_pos[-1])
            label_pos[-1][:, 0] += x_cos * x_label_offset * x_cos_sign
            label_pos[-1][:, 1] += x_sin * x_label_offset * x_sin_sign
            tick_pos[-1][:, 0] += x_cos * x_tick_offset * x_cos_sign
            tick_pos[-1][:, 1] += x_sin * x_tick_offset * x_sin_sign
            label_angle.append(x_label_angle)
            tick_angle.append(np.repeat(x_angle, len(x_pos)))

            # Y Axis
            y_pos, y_time_interval = self.get_tick_location(y_min, y_max, True, self.limits_source['y'], self.str_maps['y'], self.state['y_unit'])
            if self.state['y_grid']:
                grid_pos += list(zip(np.tile([x_min, x_max], len(y_pos)), np.repeat(y_pos, 2), np.tile([z_plane, z_plane], len(y_pos)))) + list(zip(np.tile([x_plane, x_plane], len(y_pos)), np.repeat(y_pos, 2), np.tile([z_min, z_max], len(y_pos))))
            tick_text.append(self.get_tick_format(y_pos, self.limits_source['y'], y_time_interval, self.str_maps['y'], self.state['y_unit']))
            if self.limits_source['y'] == 'date':
                if abs(cam_el) >= 15:
                    tick_text[-1] = np.array([' '.join(val) for val in np.char.split(tick_text[-1], '\n')]) if 0 < (cam_az % 180) <= 90 else np.array([' '.join(reversed(val)) for val in np.char.split(tick_text[-1], '\n')])
                else:
                    tick_text[-1] = np.array([' '.join(reversed(val)) for val in np.char.split(tick_text[-1], '\n')]) if 0 < (cam_az % 180) <= 90 else np.array([' '.join(val) for val in np.char.split(tick_text[-1], '\n')])
            label_text.append(self.get_label(self.state['y_label'], self.limits_source['y'], self.state['y_unit']))
            y_label_offset = (np.ptp(label_scale * self.get_text_bbox(label_text[-1], self.labels_3d._font, self.labels_3d._font._lowres_size, self.label_cache)[:, 1]) + self.axis_text_padding) / 2 if label_text[-1] is not None else 0
            y_tick_offset = np.array([np.ptp(tick_scale * self.get_text_bbox(val, self.ticks_3d._font, self.ticks_3d._font._lowres_size, self.tick_cache)[:, 0]) + self.axis_text_padding for val in tick_text[-1]]) / 2
            y_label_offset += np.max(y_tick_offset) * 2
            label_pos.append(np.array([[x_inv, (y_min + y_max) / 2, z_plane]]) if abs(cam_el) >= 15 else np.array([[x_plane, (y_min + y_max) / 2, z_inv]]))
            tick_pos.append(np.column_stack([[x_inv] * len(y_pos), y_pos, [z_plane] * len(y_pos)]) if abs(cam_el) >= 15 else np.column_stack([[x_plane] * len(y_pos), y_pos, [z_inv] * len(y_pos)]))
            for i, val in enumerate(['x', 'y', 'z']):
                label_pos[-1][:, i] = -0.5 + (label_pos[-1][:, i] - self.limits[val][0]) / (self.limits[val][1] - self.limits[val][0])
                tick_pos[-1][:, i] = -0.5 + (tick_pos[-1][:, i] - self.limits[val][0]) / (self.limits[val][1] - self.limits[val][0])
            label_pos[-1], tick_pos[-1] = tr.map(label_pos[-1]), tr.map(tick_pos[-1])
            label_pos[-1][:, 0] += y_cos * y_label_offset * x_sin_sign
            label_pos[-1][:, 1] += y_sin * y_label_offset * x_cos_sign
            tick_pos[-1][:, 0] += y_cos * y_tick_offset * x_sin_sign
            tick_pos[-1][:, 1] += y_sin * y_tick_offset * x_cos_sign
            label_angle.append(y_label_angle)
            tick_angle.append(np.repeat(y_angle, len(y_pos)))

            # Z Axis
            z_pos, z_time_interval = self.get_tick_location(z_min, z_max, False, self.limits_source['z'], self.str_maps['z'], self.state['z_unit'])
            if self.state['z_grid']:
                grid_pos += list(zip(np.tile([x_min, x_max], len(z_pos)), np.tile([y_plane, y_plane], len(z_pos)), np.repeat(z_pos, 2))) + list(zip(np.tile([x_plane, x_plane], len(z_pos)), np.tile([y_min, y_max], len(z_pos)), np.repeat(z_pos, 2)))
            tick_text.append(self.get_tick_format(z_pos, self.limits_source['z'], z_time_interval, self.str_maps['z'], self.state['z_unit']))
            if self.limits_source['z'] == 'date':
                if abs(cam_el) >= 15:
                    tick_text[-1] = np.array([' '.join(val) for val in np.char.split(tick_text[-1], '\n')]) if 0 < (cam_az % 90) <= 45 else np.array([' '.join(reversed(val)) for val in np.char.split(tick_text[-1], '\n')])
                else:
                    tick_text[-1] = np.array([' '.join(reversed(val)) for val in np.char.split(tick_text[-1], '\n')]) if 0 < (cam_az % 90) <= 45 else np.array([' '.join(val) for val in np.char.split(tick_text[-1], '\n')])
            label_text.append(self.get_label(self.state['z_label'], self.limits_source['z'], self.state['z_unit']))
            z_label_offset = (np.ptp(label_scale * self.get_text_bbox(label_text[-1], self.labels_3d._font, self.labels_3d._font._lowres_size, self.label_cache)[:, 1]) + self.axis_text_padding) / 2 if label_text[-1] is not None else 0
            z_tick_offset = np.array([np.ptp(tick_scale * self.get_text_bbox(val, self.ticks_3d._font, self.ticks_3d._font._lowres_size, self.tick_cache)[:, 0]) + self.axis_text_padding for val in tick_text[-1]]) / 2
            z_label_offset += np.max(z_tick_offset) * 2
            label_pos.append(np.array([[x_plane, y_inv, (z_min + z_max) / 2]]) if 45 < (cam_az % 180) <= 135 else np.array([[x_inv, y_plane, (z_min + z_max) / 2]]))
            tick_pos.append(np.column_stack([[x_plane] * len(z_pos), [y_inv] * len(z_pos), z_pos]) if 45 < (cam_az % 180) <= 135 else np.column_stack([[x_inv] * len(z_pos), [y_plane] * len(z_pos), z_pos]))
            for i, val in enumerate(['x', 'y', 'z']):
                label_pos[-1][:, i] = -0.5 + (label_pos[-1][:, i] - self.limits[val][0]) / (self.limits[val][1] - self.limits[val][0])
                tick_pos[-1][:, i] = -0.5 + (tick_pos[-1][:, i] - self.limits[val][0]) / (self.limits[val][1] - self.limits[val][0])
            label_pos[-1], tick_pos[-1] = tr.map(label_pos[-1]), tr.map(tick_pos[-1])
            if 0 < (cam_az % 90) <= 45: # right side is z
                z_sin, z_cos = np.sin(-z_angle % (2 * np.pi)), np.cos(-z_angle % (2 * np.pi))
                tick_pos[-1][:, 0] += z_cos * z_tick_offset
                tick_pos[-1][:, 1] -= z_sin * z_tick_offset
                label_pos[-1][:, 0] += z_cos * z_label_offset
                label_pos[-1][:, 1] -= z_sin * z_label_offset
            else:
                z_angle *= -1
                z_label_angle *= -1
                z_sin, z_cos = np.sin(-z_angle % (2 * np.pi)), np.cos(-z_angle % (2 * np.pi))
                tick_pos[-1][:, 0] -= z_cos * z_tick_offset
                tick_pos[-1][:, 1] += z_sin * z_tick_offset
                label_pos[-1][:, 0] -= z_cos * z_label_offset
                label_pos[-1][:, 1] += z_sin * z_label_offset
            label_angle.append(z_label_angle)
            tick_angle.append(np.repeat(z_angle, len(z_pos)))

            grid_pos = np.array(grid_pos if len(grid_pos) > 0 else [[0, 0, 0]])
            for i, val in enumerate(['x', 'y', 'z']):
                grid_pos[:, i] = -0.5 + (grid_pos[:, i] - self.limits[val][0]) / (self.limits[val][1] - self.limits[val][0])

            self.gridlines.set_data(pos=grid_pos)
            self.labels_3d.text = np.array(['' if label is None else label for label in label_text] if len(label_text) > 0 else [''])
            self.labels_3d.pos = tr.imap(np.vstack(label_pos if len(label_pos) > 0 else [[0, 0, 0]]))[:, :3]
            self.labels_3d.rotation = np.degrees(label_angle) if len(label_angle) > 0 else np.array([0])
            self.ticks_3d.text = np.hstack(tick_text) if len(tick_text) > 0 else np.array([''])
            self.ticks_3d.pos = tr.imap(np.vstack(tick_pos if len(tick_pos) else [[0, 0, 0]]))[:, :3]
            self.ticks_3d.rotation = np.degrees(np.hstack(tick_angle)) if len(tick_angle) > 0 else np.array([0])
