from . import axis_instance
from .._utilities import helper_functions
import numpy as np
import vispy.scene as vpscene
import vispy.util as vputil

class Camera_2D(vpscene.PanZoomCamera):
    def __init__(self, *args, **kwargs):
        self.movement_occurred = False
        self.resize_occurred = False
        super().__init__(*args, **kwargs)

    def view_changed(self):
        self.movement_occurred = True
        super().view_changed()

    def viewbox_mouse_event(self, event):
        event.mouse_event._modifiers = ()
        super().viewbox_mouse_event(event)

class Camera_3D(vpscene.TurntableCamera):
    def __init__(self, *args, **kwargs):
        self.movement_occurred = False
        self.resize_occurred = False
        super().__init__(*args, **kwargs)

    def view_changed(self):
        self.movement_occurred = True
        super().view_changed()

    def viewbox_mouse_event(self, event):
        event.mouse_event._modifiers = ()
        if event.type == 'mouse_move':
            if 1 in event.buttons:
                event.mouse_event._modifiers = (vputil.keys.SHIFT,)
            elif 2 in event.buttons:
                event.mouse_event._buttons = [1]
        super().viewbox_mouse_event(event)

class GridCell(vpscene.Widget):
    def __init__(self, is_last=False, *args, **kwargs):
        self.is_last = is_last
        super().__init__(*args, **kwargs)

    def _prepare_draw(self, view):
        self._update_child_widgets(grid_updated=True)
        if self.is_last:
            self.canvas.update_text()

    def _update_child_widgets(self, grid_updated=False):
        if grid_updated:
            super()._update_child_widgets()

class Canvas(vpscene.SceneCanvas):
    """
    This class is the canvas that all axes and artists are drawn on.

    Parameters
    ----------
    selection_function : method
        The function in the DIVEManager to call when a selection event occurs.
    """
    def __init__(self, selection_function):
        super().__init__(dpi=100)
        self.unfreeze()
        self.grid = None
        self.axes = []
        self.current_axis_group = None
        self.label_font_size = None
        self.tick_font_size = None
        self.labels_2d = vpscene.Text(bold=True)
        self.ticks_2d = vpscene.Text()
        self.current_axis = None
        self.current_button = None
        self.current_mode = 'pan'
        self.selection_function = selection_function
        self.selection_line = vpscene.Line()
        self.selection_line.order = float('-inf')
        self.theme = None
        self.freeze()
        self.events.mouse_press.connect(self.callback_mouse_press)
        self.events.mouse_double_click.connect(self.callback_mouse_double_click)

    def axis_limits_autoscale(self, data_objs, axis_objs, name, current_time, hold_time):
        valid_idx = {}
        all_axes = name is None
        for axis in self.axes:
            if all_axes or name == axis.state['name']:
                axis.autoscale_camera_limits(data_objs, axis_objs[axis.state['name']], valid_idx, current_time, hold_time)

    def axis_limits_reset(self, name):
        all_axes = name is None
        for axis in self.axes:
            if all_axes or name == axis.state['name']:
                axis.reset_camera_limits()

    def callback_mouse_double_click(self, event):
        self.selection_function(clear=True)

    def callback_mouse_move(self, event):
        view = self.current_axis.view
        left, top = view.parent.pos[0] + view.pos[0], view.parent.pos[1] + view.pos[1]
        if self.current_mode == 'lasso':
            vertices = np.clip(event.trail(), [left, top], [left + view.size[0], top + view.size[1]])
            self.selection_line.set_data(pos=np.vstack([vertices, vertices[0]]))
        else:
            if event.press_event is not None:
                initial_pos = event.press_event.pos
                click_pos = np.clip(event.pos, [left, top], [left + view.size[0], top + view.size[1]])
                if self.current_mode in ['zoom', 'rectangle']:
                    self.selection_line.set_data(pos=np.array([[initial_pos[0], initial_pos[1]], [click_pos[0], initial_pos[1]], [click_pos[0], click_pos[1]], [initial_pos[0], click_pos[1]], [initial_pos[0], initial_pos[1]]]))
                elif self.current_mode == 'ellipse':
                    center = [(initial_pos[0] + click_pos[0]) / 2, (initial_pos[1] + click_pos[1]) / 2]
                    theta = np.linspace(0, 2 * np.pi, 100)
                    self.selection_line.set_data(pos=np.array([center[0] + max(1, np.abs(initial_pos[0] - click_pos[0])) / 2 * np.cos(theta), center[1] + max(1, np.abs(initial_pos[1] - click_pos[1])) / 2 * np.sin(theta)]).T)

    def callback_mouse_press(self, event):
        if self.current_button == None:
            visual = self.visual_at(event.pos)
            if isinstance(visual, vpscene.ColorBar):
                for axis in self.axes:
                    if visual is axis.colorbar:
                        axis.cycle_color_key()
                        axis.view.refresh()
                        break
            elif self.current_mode != 'pan' and event.button in [1, 2] and isinstance(visual, ViewBox):
                self.current_button = event.button
                self.events.mouse_move.connect(self.callback_mouse_move)
                self.events.mouse_release.connect(self.callback_mouse_release)
                visual.events.mouse_wheel.disconnect(visual.camera.viewbox_mouse_event)
                for axis in self.axes:
                    if visual is axis.view:
                        self.current_axis = axis
                        break
                self.selection_line.set_data(pos=np.array([[-100, -100]]))
                self.selection_line.parent = self.scene

    def callback_mouse_release(self, event):
        if event.button == self.current_button:
            if len(event.trail()) > 1: # Mouse has moved since initial press
                if self.current_mode == 'zoom':
                    if self.current_button == 1: # Zoom in
                        conv_coords = self.scene.node_transform(self.current_axis.view.scene).map(self.selection_line.pos)[:, :3]
                        self.current_axis.set_camera_limits({'x': [conv_coords[:, 0].min(), conv_coords[:, 0].max()], 'y': [conv_coords[:, 1].min(), conv_coords[:, 1].max()], 'z': [conv_coords[:, 2].min(), conv_coords[:, 2].max()]}, apply_norm=False)
                    elif self.current_button == 2: # Zoom out
                        x_zoom_min, y_zoom_min, x_zoom_max, y_zoom_max = self.selection_line.pos[:, 0].min(), self.selection_line.pos[:, 1].min(), self.selection_line.pos[:, 0].max(), self.selection_line.pos[:, 1].max()
                        if x_zoom_min != x_zoom_max and y_zoom_min != y_zoom_max:
                            view = self.current_axis.view
                            x_view_min, y_view_min = view.pos[0] + view.parent.pos[0], view.pos[1] + view.parent.pos[1]
                            x_view_max, y_view_max = x_view_min + view.size[0], y_view_min + view.size[1]
                            x_scale, y_scale = (x_view_max - x_view_min) / (x_zoom_max - x_zoom_min), (y_view_max - y_view_min) / (y_zoom_max - y_zoom_min)
                            x_scaled_min, x_scaled_max = x_view_min - x_scale * (x_zoom_min - x_view_min), x_view_max + x_scale * (x_view_max - x_zoom_max)
                            y_scaled_min, y_scaled_max = y_view_min - y_scale * (y_zoom_min - y_view_min), y_view_max + y_scale * (y_view_max - y_zoom_max)
                            conv_coords = self.scene.node_transform(view.scene).map([[x_scaled_min, y_scaled_min], [x_scaled_max, y_scaled_max]])[:, :3]
                            self.current_axis.set_camera_limits({'x': [conv_coords[:, 0].min(), conv_coords[:, 0].max()], 'y': [conv_coords[:, 1].min(), conv_coords[:, 1].max()], 'z': [conv_coords[:, 2].min(), conv_coords[:, 2].max()]}, apply_norm=False)
                elif self.current_mode in ['rectangle', 'ellipse', 'lasso']:
                    self.selection_function(clear=False)
            self.events.mouse_move.disconnect(self.callback_mouse_move)
            self.events.mouse_release.disconnect(self.callback_mouse_release)
            self.current_axis.view.events.mouse_wheel.connect(self.current_axis.view.camera.viewbox_mouse_event)
            self.current_axis = self.current_button = self.selection_line.parent = None

    def clear_grid(self):
        if self.grid is not None:
            self.events.mouse_move.disconnect(self.callback_mouse_move)
            self.events.mouse_release.disconnect(self.callback_mouse_release)
            self.central_widget.remove_widget(self.grid)
            self.current_axis = self.current_axis_group = self.current_button = self.labels_2d.parent = self.grid = self.selection_line.parent = self.ticks_2d.parent = None
            self.axes = []
            self.labels_2d.text, self.labels_2d.pos, self.labels_2d.rotation = np.array(['']), np.array([[0, 0]]), 0
            self.ticks_2d.text, self.ticks_2d.pos = np.array(['']), np.array([[0, 0]])

    def clone_axis(self, data_objs, axis_obj, grid_cell, axis, apply_limits_filter):
        new_axis = axis_instance.AxisInstance(data_objs, axis_obj, grid_cell, apply_limits_filter, self.theme, self.label_font_size, self.tick_font_size)
        if isinstance(axis.view.camera, Camera_2D):
            x_min, x_max, y_min, y_max = axis.get_camera_limits_2d()
            new_axis.set_camera_limits({'x': [x_min, x_max], 'y': [y_min, y_max], 'z': [0, 1]}, no_margin=True)
            if axis.current_color_key in [key for key, val in new_axis.limits_source['color'].items() if val != 'str']:
                new_axis.current_color_key = axis.current_color_key
                new_axis.colorbar.cmap = new_axis.current_color_key[0]
        else:
            new_axis.view.camera.set_state(axis.view.camera.get_state())
        return new_axis

    def display_axis(self, data_objs, axis_objs, name, apply_limits_filter):
        if name is not None and self.current_axis_group is None and name in [axis.state['name'] for axis in self.axes]:
            return False
        self.clear_grid()
        if name is not None:
            self.grid = self.central_widget.add_grid()
            self.labels_2d.parent = self.ticks_2d.parent = self.scene
            grid_cell = self.grid.add_widget(GridCell(is_last=True), row=0, col=0, row_span=1, col_span=1)
            self.axes.append(axis_instance.AxisInstance(data_objs, axis_objs[name], grid_cell, apply_limits_filter, self.theme, self.label_font_size, self.tick_font_size))
            self.set_mode(self.current_mode)
        return True

    def display_axis_group(self, data_objs, axis_objs, axis_group_objs, name, apply_limits_filter):
        if name is not None and self.current_axis_group is not None and name == self.current_axis_group['name']:
            return False
        self.clear_grid()
        if name is not None:
            self.grid = self.central_widget.add_grid()
            self.labels_2d.parent = self.ticks_2d.parent = self.scene
            axis_group_obj = axis_group_objs[name]
            self.current_axis_group = axis_group_obj.get_state()
            n_axes = len(axis_group_obj.axis_names)
            for i in range(n_axes):
                axis_obj = axis_objs[axis_group_obj.axis_names[i]]
                grid_cell = self.grid.add_widget(GridCell(is_last=i==n_axes-1), row=axis_group_obj.rows[i], col=axis_group_obj.columns[i], row_span=axis_group_obj.row_spans[i], col_span=axis_group_obj.column_spans[i])
                self.axes.append(axis_instance.AxisInstance(data_objs, axis_obj, grid_cell, apply_limits_filter, self.theme, self.label_font_size, self.tick_font_size))
            n_rows, n_cols = self.grid.grid_size
            if n_rows < axis_group_obj.row_count or n_cols < axis_group_obj.column_count:
                self.grid.add_widget(row=axis_group_obj.row_count-1, col=axis_group_obj.column_count-1)
            self.set_mode(self.current_mode)
        return True

    def edit_axis(self, axis_obj):
        need_update = False
        for axis in self.axes:
            if axis_obj.name == axis.state['name']:
                need_update = True
                axis.state = axis_obj.get_state()
        return need_update

    def edit_axis_group(self, data_objs, axis_objs, axis_group_obj, apply_limits_filter):
        if self.current_axis_group is not None and axis_group_obj.name == self.current_axis_group['name']:
            old_axes = list(zip(self.current_axis_group['axis_names'], self.current_axis_group['rows'], self.current_axis_group['columns']))
            new_axes = list(zip(axis_group_obj.axis_names, axis_group_obj.rows, axis_group_obj.columns))
            unchanged_axes = {old_axis: self.axes[i] for i, old_axis in enumerate(old_axes) if old_axis in new_axes}
            self.clear_grid()
            self.grid = self.central_widget.add_grid()
            self.labels_2d.parent = self.ticks_2d.parent = self.scene
            self.current_axis_group = axis_group_obj.get_state()
            n_axes = len(axis_group_obj.axis_names)
            for i in range(n_axes):
                grid_cell = self.grid.add_widget(GridCell(is_last=i==n_axes-1), row=axis_group_obj.rows[i], col=axis_group_obj.columns[i], row_span=axis_group_obj.row_spans[i], col_span=axis_group_obj.column_spans[i])
                axis_key = (axis_group_obj.axis_names[i], axis_group_obj.rows[i], axis_group_obj.columns[i])
                if axis_key in unchanged_axes:
                    self.axes.append(self.clone_axis(data_objs, axis_objs[axis_group_obj.axis_names[i]], grid_cell, unchanged_axes[axis_key], apply_limits_filter))
                else:
                    self.axes.append(axis_instance.AxisInstance(data_objs, axis_objs[axis_group_obj.axis_names[i]], grid_cell, apply_limits_filter, self.theme, self.label_font_size, self.tick_font_size))
            n_rows, n_cols = self.grid.grid_size
            if n_rows < axis_group_obj.row_count or n_cols < axis_group_obj.column_count:
                self.grid.add_widget(row=axis_group_obj.row_count-1, col=axis_group_obj.column_count-1)
            self.set_mode(self.current_mode)
            return True
        return False

    def get_legend(self, data_objs, axis_objs):
        entries, merged_entries = [], {}
        for axis in self.axes:
            entries += axis.get_artist_legend(data_objs, axis_objs[axis.state['name']])
        for label, icon, subentries in entries:
            merged_entries[(label, icon)] = merged_entries.get((label, icon), []) + subentries
        legend = [(key[0], key[1], sorted(set(merged_entries[key]), key=lambda s: helper_functions.natural_order(s[0]))) for key in merged_entries]
        legend.sort(key=lambda s: helper_functions.natural_order(s[0]))
        return legend

    def recreate_grid_cell(self, data_objs, axis_obj, apply_limits_filter):
        need_update = False
        n_axes = len(self.axes)
        for i in range(n_axes):
            if self.axes[i].state['name'] == axis_obj.name:
                need_update = True
                self.grid.remove_widget(self.axes[i].view.parent)
                self.axes[i].view.parent.parent = None
                if self.current_axis_group is None:
                    grid_cell = self.grid.add_widget(GridCell(is_last=True), row=0, col=0, row_span=1, col_span=1)
                else:
                    grid_cell = self.grid.add_widget(GridCell(is_last=i==n_axes-1), row=self.current_axis_group['rows'][i], col=self.current_axis_group['columns'][i], row_span=self.current_axis_group['row_spans'][i], col_span=self.current_axis_group['column_spans'][i])
                self.axes[i] = self.clone_axis(data_objs, axis_obj, grid_cell, self.axes[i], apply_limits_filter)
        self.set_mode(self.current_mode)
        return need_update

    def remove_axis(self, data_objs, axis_objs, axis_group_objs, name, apply_limits_filter):
        need_update = False
        if self.current_axis_group is None and name in [axis.state['name'] for axis in self.axes]:
            self.clear_grid()
        elif self.current_axis_group is not None and name in self.current_axis_group['axis_names']:
            self.edit_axis_group(data_objs, axis_objs, axis_group_objs[self.current_axis_group['name']], apply_limits_filter)
            need_update = True
        return need_update

    def remove_axis_group(self, name):
        need_update = False
        if self.current_axis_group is not None and name == self.current_axis_group['name']:
            self.clear_grid()
            need_update = True
        return need_update

    def select_points(self, data_objs, axis_objs, current_time, hold_time):
        selected = self.current_axis.get_artist_selected(data_objs, axis_objs[self.current_axis.state['name']], current_time, hold_time, self.selection_line.pos)
        for data_name in selected:
            data_obj = data_objs[data_name]
            if self.current_button == 1: # Left click
                data_obj.apply_selection(selected[data_name] if data_obj.selection is None else np.logical_or(data_obj.selection, selected[data_name]))
            elif self.current_button == 2: # Right click
                if data_obj.selection is None:
                    return
                data_obj.apply_selection(np.logical_and(data_obj.selection, ~selected[data_name]))
        for data_obj in data_objs.values():
            if data_obj.selection is None:
                data_obj.apply_selection(None)

    def set_font_sizes(self, label_size, tick_size):
        self.label_font_size = self.labels_2d.font_size = label_size
        self.tick_font_size = self.ticks_2d.font_size = tick_size
        for axis in self.axes:
            axis.set_font_sizes(label_size, tick_size)

    def set_mode(self, mode):
        self.current_mode = mode
        if self.current_mode == 'pan':
            for axis in self.axes:
                axis.view.events.mouse_press.connect(axis.view.camera.viewbox_mouse_event)
        else:
            for axis in self.axes:
                axis.view.events.mouse_press.disconnect(axis.view.camera.viewbox_mouse_event)

    def set_theme(self, axis_objs, theme):
        """
        Set the theme to use for the canvas and all axes currently being displayed.

        Parameters
        ----------
        theme : str
            The theme to use.
        """
        self.theme = theme
        self.bgcolor = 'k' if theme == 'dark' else 'w'
        color = 'w' if theme == 'dark' else 'k'
        self.labels_2d.color = color
        self.ticks_2d.color = color
        self.selection_line.set_data(color=color)
        for axis in self.axes:
            axis.set_theme(axis_objs[axis.state['name']], theme)

    def update_filters(self, data_objs, axis_objs, apply_limits_filter):
        for axis in self.axes:
            axis.filter_limits(data_objs, axis_objs[axis.state['name']], apply_limits_filter)

    def update_axes(self, data_objs, axis_objs, current_time, hold_time, timezone, unit_reg, time_updated):
        valid_idx = {}
        for axis in self.axes:
            if not time_updated:
                axis.view.refresh()
            axis.update_artists(data_objs, axis_objs[axis.state['name']], valid_idx, current_time, hold_time, timezone, unit_reg, time_updated)

    def update_text(self):
        """
        This functions updates all axis titles, labels, and ticks (except for 3D axis labels and ticks).
        """
        label_text, label_pos, label_rotation, tick_text, tick_pos = [], [], [], [], []
        need_update = False
        for axis in self.axes:
            need_update |= axis.view.camera.movement_occurred | axis.view.camera.resize_occurred
            axis.view.camera.movement_occurred = axis.view.camera.resize_occurred = False
        if need_update:
            for axis in self.axes:
                grid_left, grid_top, grid_width, grid_height = axis.view.parent.pos[0], axis.view.parent.pos[1], axis.view.parent.size[0], axis.view.parent.size[1]
                axis_left, axis_top, axis_width, axis_height = axis.view.pos[0], axis.view.pos[1], axis.view.size[0], axis.view.size[1]
                if axis.current_color_key is not None:
                    label_pos.append([grid_left + grid_width - axis.grid_info['color_label_offset'] / 2, grid_top + axis_top + axis_height / 2])
                    colorbar_label = axis.get_label(axis.current_color_key[1], axis.limits_source['color'][axis.current_color_key], axis.current_color_key[2])
                    label_text.append('' if colorbar_label is None else colorbar_label)
                    label_rotation.append(90)
                    min_color, max_color = axis.limits['color'][axis.current_color_key]
                    colorbar_top, colorbar_bottom = grid_top + axis.colorbar.pos[1] - axis.colorbar.size[0] / 2, grid_top + axis.colorbar.pos[1] + axis.colorbar.size[0] / 2
                    color_x = grid_left + axis.colorbar.pos[0] + axis.colorbar.size[1] / 2 + axis.grid_info['color_tick_offset'] / 2
                    color_y = colorbar_top + (max_color - axis.grid_info['color_pos']) * (colorbar_bottom - colorbar_top) / (max_color - min_color)
                    tick_pos.append(np.column_stack([color_x, color_y]))
                    tick_text.append(axis.grid_info['color_text'])
                if axis.state['title'] is not None:
                    label_text.append(axis.state['title'])
                    label_pos.append([grid_left + axis_left + axis_width / 2, grid_top + axis.grid_info['title_offset'] / 2])
                    label_rotation.append(0)
                if isinstance(axis.view.camera, Camera_2D):
                    rect = axis.view.camera.rect
                    tr = axis.view.scene.node_transform(self.scene)

                    x_label = axis.get_label(axis.state['x_label'], axis.limits_source['x'], axis.state['x_unit'])
                    if x_label is not None:
                        label_text.append(x_label)
                        label_pos.append([grid_left + axis_left + axis_width / 2, grid_top + grid_height - axis.grid_info['x_label_offset'] / 2])
                        label_rotation.append(0)
                    x_tick_pos = tr.map(np.column_stack([axis.grid_info['x_pos'], [rect.bottom] * len(axis.grid_info['x_pos'])]))[:, :2]
                    x_tick_pos[:, 1] += axis.grid_info['x_tick_offset'] / 2
                    tick_pos.append(x_tick_pos)
                    tick_text.append(axis.grid_info['x_text'])

                    y_label = axis.get_label(axis.state['y_label'], axis.limits_source['y'], axis.state['y_unit'])
                    if y_label is not None:
                        label_text.append(y_label)
                        label_pos.append([grid_left + axis.grid_info['y_label_offset'] / 2, grid_top + axis_top + axis_height / 2])
                        label_rotation.append(-90)
                    y_tick_pos = tr.map(np.column_stack([[rect.left] * len(axis.grid_info['y_pos']), axis.grid_info['y_pos']]))[:, :2]
                    y_tick_pos[:, 0] -= axis.grid_info['y_tick_offset'] / 2
                    tick_pos.append(y_tick_pos)
                    tick_text.append(axis.grid_info['y_text'])
            if len(label_text) > 0:
                self.labels_2d.text = np.array(label_text)
                self.labels_2d.pos = np.vstack(label_pos)
                self.labels_2d.rotation = np.array(label_rotation)
            else:
                self.labels_2d.text = np.array([''])
                self.labels_2d.pos = np.array([[0, 0]])
                self.labels_2d.rotation = 0
            if len(tick_text) > 0:
                self.ticks_2d.text = np.hstack(tick_text)
                self.ticks_2d.pos = np.vstack(tick_pos)
            else:
                self.ticks_2d.text = np.array([''])
                self.ticks_2d.pos = np.array([[0, 0]])

class ViewBox(vpscene.ViewBox):
    def __init__(self, axis, *args, **kwargs):
        self.axis = axis
        self.grid_size = None
        self.custom_pos = (0, 0)
        self.custom_size = (1, 1)
        super().__init__(*args, **kwargs)

    def refresh(self):
        self.grid_size = None

    @vpscene.ViewBox.rect.setter
    def rect(self, r):
        if self.grid_size is None or r.size[0] != self.grid_size[0] or r.size[1] != self.grid_size[1]:
            self.camera.resize_occurred = True
        self.grid_size = r.size
        if (self.camera.movement_occurred and isinstance(self.camera, Camera_2D)) or self.camera.resize_occurred:
            # Get spacing for axis labels and ticks
            left, right, top, bottom = self.axis.get_spacing()
            self.custom_pos, self.custom_size = (left, top), (r.size[0] - left - right, r.size[1] - top - bottom)
        r.pos, r.size = self.custom_pos, self.custom_size
        vpscene.ViewBox.rect.fset(self, r)
        if self.camera.movement_occurred or self.camera.resize_occurred:
            self.axis.update_grid()