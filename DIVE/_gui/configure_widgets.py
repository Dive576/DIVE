from . import custom_qt
import importlib
import vispy.app as vpapp
import vispy.io as vpio
import vispy.visuals as vpvisuals
qt = vpapp.use_app().backend_name
try:
    qtwidgets = importlib.import_module('{}.QtWidgets'.format(qt))
except:
    pass
del qt

class ArrowWidget(qtwidgets.QWidget):
    def __init__(self, data_objs, axis_type, artist):
        super().__init__()
        self.setLayout(qtwidgets.QFormLayout())

        self.data_objs = data_objs

        self.visible_val, self.draw_order, self.legend_text = add_common_widgets(self.layout(), artist['visible'], artist['draw_order'], artist['legend_text'])

        self.selectable = qtwidgets.QCheckBox()
        self.selectable.setChecked(artist['selectable'])
        self.layout().addRow('Selectable:', self.selectable)
        self.data_name = qtwidgets.QComboBox()
        self.data_name.currentTextChanged.connect(self.set_field_names)
        self.layout().addRow('Data Name:', self.data_name)
        self.label_field = add_optional_combobox(self.layout(), 'Label Field:', artist['label_field'] is not None)
        self.label_size = add_spinbox(self.layout(), 'Label Size:', 0.0, float('inf'), artist['label_size'])

        pos_group = qtwidgets.QGroupBox('Position')
        pos_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(pos_group)
        self.x_field = qtwidgets.QComboBox()
        pos_group.layout().addRow('X Field:', self.x_field)
        self.y_field = qtwidgets.QComboBox()
        pos_group.layout().addRow('Y Field:', self.y_field)
        if axis_type == '3d':
            self.z_field = qtwidgets.QComboBox()
            pos_group.layout().addRow('Z Field:', self.z_field)
        else:
            self.z_field = None

        line_group = qtwidgets.QGroupBox('Line')
        line_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(line_group)
        self.line_width = add_spinbox(line_group.layout(), 'Width:', 0.0, float('inf'), artist['line_width'])
        self.line_color, self.line_color_field, self.line_colormap, self.line_color_label, self.line_color_unit_from, self.line_color_unit_to = add_color_widgets(line_group.layout(), artist['line_color'], artist['line_color_field'], artist['line_colormap'], artist['line_color_label'], artist['line_color_unit'])

        arrow_group = qtwidgets.QGroupBox('Arrow')
        arrow_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(arrow_group)
        self.arrow_shape = qtwidgets.QComboBox()
        self.arrow_shape.addItems(sorted(vpvisuals.line.arrow.ARROW_TYPES))
        self.arrow_shape.setCurrentText(artist['arrow_shape'])
        arrow_group.layout().addRow('Arrow Shape:', self.arrow_shape)
        self.arrow_spacing = qtwidgets.QDoubleSpinBox()
        self.arrow_spacing.setRange(0.0, float('inf'))
        self.arrow_spacing.setValue(artist['arrow_spacing'])
        self.arrow_spacing.setDecimals(0)
        arrow_group.layout().addRow('Arrow Spacing:', self.arrow_spacing)
        self.show_last_arrow = qtwidgets.QCheckBox()
        self.show_last_arrow.setChecked(artist['show_last_arrow'])
        arrow_group.layout().addRow('Show Last Arrow:', self.show_last_arrow)
        self.arrow_size = add_spinbox(arrow_group.layout(), 'Size:', 0.0, float('inf'), artist['arrow_size'])
        self.arrow_color, self.arrow_color_field, self.arrow_colormap, self.arrow_color_label, self.arrow_color_unit_from, self.arrow_color_unit_to = add_color_widgets(arrow_group.layout(), artist['arrow_color'], artist['arrow_color_field'], artist['arrow_colormap'], artist['arrow_color_label'], artist['arrow_color_unit'])

        self.data_name.addItems(list(self.data_objs))
        if artist['data_name'] is not None:
            self.data_name.setCurrentText(artist['data_name'])
            self.label_field.setCurrentText(artist['label_field'])
            self.x_field.setCurrentText(artist['x_field'])
            self.y_field.setCurrentText(artist['y_field'])
            self.line_color_field.setCurrentText(artist['line_color_field'])
            self.arrow_color_field.setCurrentText(artist['arrow_color_field'])
            if self.z_field is not None:
                self.z_field.setCurrentText(artist['z_field'])

    def get_values(self):
        return {'artist_type': 'arrow',
                'visible': self.visible_val.isChecked(),
                'draw_order': self.draw_order.value(),
                'legend_text': self.legend_text.text() if self.legend_text.isEnabled() else None,
                'selectable': self.selectable.isChecked(),
                'data_name': self.data_name.currentText(),
                'label_field': self.label_field.currentText() if self.label_field.isEnabled() else None,
                'label_size': self.label_size.value(),
                'x_field': self.x_field.currentText(),
                'y_field': self.y_field.currentText(),
                'z_field': None if self.z_field is None else self.z_field.currentText(),
                'line_width': self.line_width.value(),
                'line_color': self.line_color.get_color(),
                'line_color_field': self.line_color_field.currentText() if self.line_color_field.isEnabled() else None,
                'line_colormap': self.line_colormap.currentText(),
                'line_color_label': self.line_color_label.text() if self.line_color_label.isEnabled() else None,
                'line_color_unit': [self.line_color_unit_from.text(), self.line_color_unit_to.text()] if self.line_color_unit_from.isEnabled() else None,
                'arrow_shape': self.arrow_shape.currentText(),
                'arrow_spacing': int(self.arrow_spacing.value()),
                'show_last_arrow': self.show_last_arrow.isChecked(),
                'arrow_size': self.arrow_size.value(),
                'arrow_color': self.arrow_color.get_color(),
                'arrow_color_field': self.arrow_color_field.currentText() if self.arrow_color_field.isEnabled() else None,
                'arrow_colormap': self.arrow_colormap.currentText(),
                'arrow_color_label': self.arrow_color_label.text() if self.arrow_color_label.isEnabled() else None,
                'arrow_color_unit': [self.arrow_color_unit_from.text(), self.arrow_color_unit_to.text()] if self.arrow_color_unit_from.isEnabled() else None}

    def set_field_names(self, text):
        data_names = list(self.data_objs[text].data)
        for field in ['label_field', 'x_field', 'y_field', 'line_color_field', 'arrow_color_field']:
            combo = getattr(self, field)
            combo.clear()
            combo.addItems(data_names)
        if self.z_field is not None:
            self.z_field.clear()
            self.z_field.addItems(data_names)

    @staticmethod
    def get_default_values():
        return dict(visible=True, draw_order=0, legend_text=None, selectable=True, data_name=None, label_field=None, label_size=10, x_field=None, y_field=None, z_field=None, line_width=1, line_color='r', line_color_field=None, line_colormap='viridis', line_color_label=None, line_color_unit=None, arrow_shape='stealth', arrow_spacing=0, show_last_arrow=True, arrow_size=10, arrow_color='g', arrow_color_field=None, arrow_colormap='viridis', arrow_color_label=None, arrow_color_unit=None)

class AxisWidget(qtwidgets.QWidget):
    def __init__(self, axis):
        super().__init__()
        self.setLayout(qtwidgets.QFormLayout())

        self.title = add_optional_line_edit(self.layout(), 'Title:', axis['title'])

        self.time_autoscale = qtwidgets.QCheckBox()
        self.time_autoscale.setChecked(axis['time_autoscale'])
        self.layout().addRow('Time Autoscale:', self.time_autoscale)

        x_group = qtwidgets.QGroupBox('X-Axis')
        x_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(x_group)
        self.x_grid = qtwidgets.QCheckBox()
        self.x_grid.setChecked(axis['x_grid'])
        x_group.layout().addRow('Show Grid:', self.x_grid)
        self.x_label = add_optional_line_edit(x_group.layout(), 'Label:', axis['x_label'])
        self.x_unit_from, self.x_unit_to = add_unit_widgets(x_group.layout(), 'Units:', axis['x_unit'])

        y_group = qtwidgets.QGroupBox('Y-Axis')
        y_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(y_group)
        self.y_grid = qtwidgets.QCheckBox()
        self.y_grid.setChecked(axis['y_grid'])
        y_group.layout().addRow('Show Grid:', self.y_grid)
        self.y_label = add_optional_line_edit(y_group.layout(), 'Label:', axis['y_label'])
        self.y_unit_from, self.y_unit_to = add_unit_widgets(y_group.layout(), 'Units:', axis['y_unit'])

        z_group = qtwidgets.QGroupBox('Z-Axis')
        z_group.setLayout(qtwidgets.QFormLayout())
        z_group.setVisible(axis['axis_type'] == '3d')
        self.layout().addRow(z_group)
        self.z_grid = qtwidgets.QCheckBox()
        self.z_grid.setChecked(axis['z_grid'])
        z_group.layout().addRow('Show Grid:', self.z_grid)
        self.z_label = add_optional_line_edit(z_group.layout(), 'Label:', axis['z_label'])
        self.z_unit_from, self.z_unit_to = add_unit_widgets(z_group.layout(), 'Units:', axis['z_unit'])

    def get_values(self):
        return {'axis_type': '3d' if self.z_grid.parent().isVisible() else '2d',
                'title': self.title.text() if self.title.isEnabled() else None,
                'time_autoscale': self.time_autoscale.isChecked(),
                'x_grid': self.x_grid.isChecked(),
                'x_label': self.x_label.text() if self.x_label.isEnabled() else None,
                'x_unit': [self.x_unit_from.text(), self.x_unit_to.text()] if self.x_unit_from.isEnabled() else None,
                'y_grid': self.y_grid.isChecked(),
                'y_label': self.y_label.text() if self.y_label.isEnabled() else None,
                'y_unit': [self.y_unit_from.text(), self.y_unit_to.text()] if self.y_unit_from.isEnabled() else None,
                'z_grid': self.z_grid.isChecked(),
                'z_label': self.z_label.text() if self.z_label.isEnabled() else None,
                'z_unit': [self.z_unit_from.text(), self.z_unit_to.text()] if self.z_unit_from.isEnabled() else None}

    @staticmethod
    def get_default_values():
        return dict(title=None, time_autoscale=False, x_grid=True, x_label=None, x_unit=None, y_grid=True, y_label=None, y_unit=None, z_grid=True, z_label=None, z_unit=None)

class BoxWidget(qtwidgets.QWidget):
    def __init__(self, data_objs, axis_type, artist):
        super().__init__()
        self.setLayout(qtwidgets.QFormLayout())

        self.data_objs = data_objs

        self.visible_val, self.draw_order, self.legend_text = add_common_widgets(self.layout(), artist['visible'], artist['draw_order'], artist['legend_text'])
        self.data_name = add_optional_combobox(self.layout(), 'Data Name:', artist['data_name'] is not None)
        self.data_name.currentTextChanged.connect(self.set_field_names)

        self.face_hbox = qtwidgets.QHBoxLayout()
        for face in ['Positive X', 'Negative X', 'Positive Y', 'Negative Y', 'Positive Z', 'Negative Z']:
            check = qtwidgets.QCheckBox(face)
            face_sign, face_text = face.split()
            check.setChecked((face_text.lower() if face_sign == 'Negative' else face_text.upper()) in artist['faces'])
            self.face_hbox.addWidget(check)
        self.face_hbox.addStretch()
        self.layout().addRow('Faces:', self.face_hbox)

        pos_group = qtwidgets.QGroupBox('Position')
        pos_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(pos_group)
        self.x_pos = add_spinbox(pos_group.layout(), 'X Position:', float('-inf'), float('inf'), artist['x_pos'])
        self.x_pos_field = add_optional_combobox(pos_group.layout(), 'X Position Field:', artist['x_pos_field'] is not None)
        self.y_pos = add_spinbox(pos_group.layout(), 'Y Position:', float('-inf'), float('inf'), artist['y_pos'])
        self.y_pos_field = add_optional_combobox(pos_group.layout(), 'Y Position Field:', artist['y_pos_field'] is not None)
        self.z_pos = add_spinbox(pos_group.layout(), 'Z Position:', float('-inf'), float('inf'), artist['z_pos'])
        self.z_pos_field = add_optional_combobox(pos_group.layout(), 'Z Position Field:', artist['z_pos_field'] is not None)
        self.width_val = add_spinbox(pos_group.layout(), 'Width:', 0.0, float('inf'), artist['width'])
        self.width_field = add_optional_combobox(pos_group.layout(), 'Width Field:', artist['width_field'] is not None)
        self.height_val = add_spinbox(pos_group.layout(), 'Height:', 0.0, float('inf'), artist['height'])
        self.height_field = add_optional_combobox(pos_group.layout(), 'Height Field:', artist['height_field'] is not None)
        self.depth_val = add_spinbox(pos_group.layout(), 'Depth:', 0.0, float('inf'), artist['depth'])
        self.depth_field = add_optional_combobox(pos_group.layout(), 'Depth Field:', artist['depth_field'] is not None)
        color_group = qtwidgets.QGroupBox('Color')
        color_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(color_group)
        self.color, self.color_field, self.colormap, self.color_label, self.color_unit_from, self.color_unit_to = add_color_widgets(color_group.layout(), artist['color'], artist['color_field'], artist['colormap'], artist['color_label'], artist['color_unit'])

        self.data_name.addItems(list(self.data_objs))
        if artist['data_name'] is not None:
            self.data_name.setCurrentText(artist['data_name'])
            self.x_pos_field.setCurrentText(artist['x_pos_field'])
            self.y_pos_field.setCurrentText(artist['y_pos_field'])
            self.z_pos_field.setCurrentText(artist['z_pos_field'])
            self.width_field.setCurrentText(artist['width_field'])
            self.height_field.setCurrentText(artist['height_field'])
            self.depth_field.setCurrentText(artist['depth_field'])
            self.color_field.setCurrentText(artist['color_field'])

    def get_values(self):
        faces = ''
        for i in range(6):
            check = self.face_hbox.itemAt(i).widget()
            if check.isChecked():
                face_sign, face_text = check.text().split()
                faces += face_text.lower() if face_sign == 'Negative' else face_text.upper()
        return {'artist_type': 'box',
                'visible': self.visible_val.isChecked(),
                'draw_order': self.draw_order.value(),
                'legend_text': self.legend_text.text() if self.legend_text.isEnabled() else None,
                'data_name': self.data_name.currentText() if self.data_name.isEnabled() else None,
                'faces': faces,
                'x_pos': self.x_pos.value(),
                'x_pos_field': self.x_pos_field.currentText() if self.data_name.isEnabled() and self.x_pos_field.isEnabled() else None,
                'y_pos': self.y_pos.value(),
                'y_pos_field': self.y_pos_field.currentText() if self.data_name.isEnabled() and self.y_pos_field.isEnabled() else None,
                'z_pos': self.z_pos.value(),
                'z_pos_field': self.z_pos_field.currentText() if self.data_name.isEnabled() and self.z_pos_field.isEnabled() else None,
                'width': self.width_val.value(),
                'width_field': self.width_field.currentText() if self.data_name.isEnabled() and self.width_field.isEnabled() else None,
                'height': self.height_val.value(),
                'height_field': self.height_field.currentText() if self.data_name.isEnabled() and self.height_field.isEnabled() else None,
                'depth': self.depth_val.value(),
                'depth_field': self.depth_field.currentText() if self.data_name.isEnabled() and self.depth_field.isEnabled() else None,
                'color': self.color.get_color(),
                'color_field': self.color_field.currentText() if self.data_name.isEnabled() and self.color_field.isEnabled() else None,
                'colormap': self.colormap.currentText(),
                'color_label': self.color_label.text() if self.color_label.isEnabled() else None,
                'color_unit': [self.color_unit_from.text(), self.color_unit_to.text()] if self.color_unit_from.isEnabled() else None}

    def set_field_names(self, text):
        data_names = list(self.data_objs[text].data)
        for field in ['x_pos_field', 'y_pos_field', 'z_pos_field', 'width_field', 'height_field', 'depth_field', 'color_field',]:
            combo = getattr(self, field)
            combo.clear()
            combo.addItems(data_names)

    @staticmethod
    def get_default_values():
        return dict(visible=True, draw_order=0, legend_text=None, data_name=None, faces='XxYyZz', x_pos=0, x_pos_field=None, y_pos=0, y_pos_field=None, z_pos=0, z_pos_field=None, width=1, width_field=None, height=1, height_field=None, depth=1, depth_field=None, color='g', color_field=None, colormap='viridis', color_label=None, color_unit=None)

class EllipseWidget(qtwidgets.QWidget):
    def __init__(self, data_objs, axis_type, artist):
        super().__init__()
        self.setLayout(qtwidgets.QFormLayout())

        self.data_objs = data_objs

        self.visible_val, self.draw_order, self.legend_text = add_common_widgets(self.layout(), artist['visible'], artist['draw_order'], artist['legend_text'])
        self.data_name = add_optional_combobox(self.layout(), 'Data Name:', artist['data_name'] is not None)
        self.data_name.currentTextChanged.connect(self.set_field_names)
        self.start_angle = add_spinbox(self.layout(), 'Start Angle:', float('-inf'), float('inf'), artist['start_angle'])
        self.start_angle_field = add_optional_combobox(self.layout(), 'Start Angle Field:', artist['start_angle_field'] is not None)
        self.span_angle = add_spinbox(self.layout(), 'Span Angle:', float('-inf'), float('inf'), artist['span_angle'])
        self.span_angle_field = add_optional_combobox(self.layout(), 'Span Angle Field:', artist['span_angle_field'] is not None)

        pos_group = qtwidgets.QGroupBox('Position')
        pos_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(pos_group)
        self.x_pos = add_spinbox(pos_group.layout(), 'X Position:', float('-inf'), float('inf'), artist['x_pos'])
        self.x_pos_field = add_optional_combobox(pos_group.layout(), 'X Position Field:', artist['x_pos_field'] is not None)
        self.y_pos = add_spinbox(pos_group.layout(), 'Y Position:', float('-inf'), float('inf'), artist['y_pos'])
        self.y_pos_field = add_optional_combobox(pos_group.layout(), 'Y Position Field:', artist['y_pos_field'] is not None)
        self.x_radius = add_spinbox(pos_group.layout(), 'X Radius:', 0.0, float('inf'), artist['x_radius'])
        self.x_radius_field = add_optional_combobox(pos_group.layout(), 'X Radius Field:', artist['x_radius_field'] is not None)
        self.y_radius = add_spinbox(pos_group.layout(), 'Y Radius:', 0.0, float('inf'), artist['y_radius'])
        self.y_radius_field = add_optional_combobox(pos_group.layout(), 'Y Radius Field:', artist['y_radius_field'] is not None)
        color_group = qtwidgets.QGroupBox('Color')
        color_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(color_group)
        self.color, self.color_field, self.colormap, self.color_label, self.color_unit_from, self.color_unit_to = add_color_widgets(color_group.layout(), artist['color'], artist['color_field'], artist['colormap'], artist['color_label'], artist['color_unit'])
        edge_group = qtwidgets.QGroupBox('Ellipse Edge')
        edge_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(edge_group)
        self.edge_width = add_spinbox(edge_group.layout(), 'Width:', 0.0, float('inf'), artist['edge_width'])
        self.edge_width_field = add_optional_combobox(edge_group.layout(), 'Width Field:', artist['edge_width_field'] is not None)
        self.edge_color, self.edge_color_field, self.edge_colormap, self.edge_color_label, self.edge_color_unit_from, self.edge_color_unit_to = add_color_widgets(edge_group.layout(), artist['edge_color'], artist['edge_color_field'], artist['edge_colormap'], artist['edge_color_label'], artist['edge_color_unit'])

        self.data_name.addItems(list(self.data_objs))
        if artist['data_name'] is not None:
            self.data_name.setCurrentText(artist['data_name'])
            self.start_angle_field.setCurrentText(artist['start_angle_field'])
            self.span_angle_field.setCurrentText(artist['span_angle_field'])
            self.x_pos_field.setCurrentText(artist['x_pos_field'])
            self.y_pos_field.setCurrentText(artist['y_pos_field'])
            self.x_radius_field.setCurrentText(artist['x_radius_field'])
            self.y_radius_field.setCurrentText(artist['y_radius_field'])
            self.color_field.setCurrentText(artist['color_field'])
            self.edge_width_field.setCurrentText(artist['edge_width_field'])
            self.edge_color_field.setCurrentText(artist['edge_color_field'])

    def get_values(self):
        return {'artist_type': 'ellipse',
                'visible': self.visible_val.isChecked(),
                'draw_order': self.draw_order.value(),
                'legend_text': self.legend_text.text() if self.legend_text.isEnabled() else None,
                'data_name': self.data_name.currentText() if self.data_name.isEnabled() else None,
                'start_angle': self.start_angle.value(),
                'start_angle_field': self.start_angle_field.currentText() if self.data_name.isEnabled() and self.start_angle_field.isEnabled() else None,
                'span_angle': self.span_angle.value(),
                'span_angle_field': self.span_angle_field.currentText() if self.data_name.isEnabled() and self.span_angle_field.isEnabled() else None,
                'x_pos': self.x_pos.value(),
                'x_pos_field': self.x_pos_field.currentText() if self.data_name.isEnabled() and self.x_pos_field.isEnabled() else None,
                'y_pos': self.y_pos.value(),
                'y_pos_field': self.y_pos_field.currentText() if self.data_name.isEnabled() and self.y_pos_field.isEnabled() else None,
                'x_radius': self.x_radius.value(),
                'x_radius_field': self.x_radius_field.currentText() if self.data_name.isEnabled() and self.x_radius_field.isEnabled() else None,
                'y_radius': self.y_radius.value(),
                'y_radius_field': self.y_radius_field.currentText() if self.data_name.isEnabled() and self.y_radius_field.isEnabled() else None,
                'color': self.color.get_color(),
                'color_field': self.color_field.currentText() if self.data_name.isEnabled() and self.color_field.isEnabled() else None,
                'colormap': self.colormap.currentText(),
                'color_label': self.color_label.text() if self.color_label.isEnabled() else None,
                'color_unit': [self.color_unit_from.text(), self.color_unit_to.text()] if self.color_unit_from.isEnabled() else None,
                'edge_width': self.edge_width.value(),
                'edge_width_field': self.edge_width_field.currentText() if self.data_name.isEnabled() and self.edge_width_field.isEnabled() else None,
                'edge_color': self.edge_color.get_color(),
                'edge_color_field': self.edge_color_field.currentText() if self.data_name.isEnabled() and self.edge_color_field.isEnabled() else None,
                'edge_colormap': self.edge_colormap.currentText(),
                'edge_color_label': self.edge_color_label.text() if self.edge_color_label.isEnabled() else None,
                'edge_color_unit': [self.edge_color_unit_from.text(), self.edge_color_unit_to.text()] if self.edge_color_unit_from.isEnabled() else None}

    def set_field_names(self, text):
        data_names = list(self.data_objs[text].data)
        for field in ['start_angle_field', 'span_angle_field', 'x_pos_field', 'y_pos_field', 'x_radius_field', 'y_radius_field', 'color_field', 'edge_width_field', 'edge_color_field']:
            combo = getattr(self, field)
            combo.clear()
            combo.addItems(data_names)

    @staticmethod
    def get_default_values():
        return dict(visible=True, draw_order=0, legend_text=None, data_name=None, start_angle=0, start_angle_field=None, span_angle=360, span_angle_field=None, x_pos=0, x_pos_field=None, y_pos=0, y_pos_field=None, x_radius=0.5, x_radius_field=None, y_radius=0.5, y_radius_field=None, color='g', color_field=None, colormap='viridis', color_label=None, color_unit=None, edge_width=0, edge_width_field=None, edge_color='g', edge_color_field=None, edge_colormap='viridis', edge_color_label=None, edge_color_unit=None)

class ImageWidget(qtwidgets.QWidget):
    def __init__(self, data_objs, axis_type, artist):
        super().__init__()
        self.setLayout(qtwidgets.QFormLayout())

        self.data_objs = data_objs

        self.visible_val, self.draw_order, self.legend_text = add_common_widgets(self.layout(), artist['visible'], artist['draw_order'], artist['legend_text'])
        self.data_name = qtwidgets.QComboBox()
        self.data_name.currentTextChanged.connect(self.set_field_names)
        self.layout().addRow('Data Name:', self.data_name)
        self.interpolation = qtwidgets.QComboBox()
        self.interpolation.addItems(sorted([interp_name.lower() for interp_name in vpio.load_spatial_filters()[1]]))
        self.interpolation.setCurrentText(artist['interpolation'])
        self.layout().addRow('Interpolation:', self.interpolation)
        pos_group = qtwidgets.QGroupBox('Position')
        pos_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(pos_group)
        self.x_pos = add_spinbox(pos_group.layout(), 'X Position:', float('-inf'), float('inf'), artist['x_pos'])
        self.x_pos_field = add_optional_combobox(pos_group.layout(), 'X Position Field:', artist['x_pos_field'] is not None)
        self.y_pos = add_spinbox(pos_group.layout(), 'Y Position:', float('-inf'), float('inf'), artist['y_pos'])
        self.y_pos_field = add_optional_combobox(pos_group.layout(), 'Y Position Field:', artist['y_pos_field'] is not None)
        self.width_val = add_spinbox(pos_group.layout(), 'Width:', 0.0, float('inf'), artist['width'])
        self.width_field = add_optional_combobox(pos_group.layout(), 'Width Field:', artist['width_field'] is not None)
        self.height_val = add_spinbox(pos_group.layout(), 'Height:', 0.0, float('inf'), artist['height'])
        self.height_field = add_optional_combobox(pos_group.layout(), 'Height Field:', artist['height_field'] is not None)
        color_group = qtwidgets.QGroupBox('Color')
        color_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(color_group)
        _, self.color_field, self.colormap, self.color_label, self.color_unit_from, self.color_unit_to = add_color_widgets(color_group.layout(), None, artist['color_field'], artist['colormap'], artist['color_label'], artist['color_unit'])

        self.data_name.addItems(list(self.data_objs))
        if artist['data_name'] is not None:
            self.data_name.setCurrentText(artist['data_name'])
            self.x_pos_field.setCurrentText(artist['x_pos_field'])
            self.y_pos_field.setCurrentText(artist['y_pos_field'])
            self.width_field.setCurrentText(artist['width_field'])
            self.height_field.setCurrentText(artist['height_field'])
            self.color_field.setCurrentText(artist['color_field'])

    def get_values(self):
        return {'artist_type': 'image',
                'visible': self.visible_val.isChecked(),
                'draw_order': self.draw_order.value(),
                'legend_text': self.legend_text.text() if self.legend_text.isEnabled() else None,
                'data_name': self.data_name.currentText(),
                'interpolation': self.interpolation.currentText(),
                'x_pos': self.x_pos.value(),
                'x_pos_field': self.x_pos_field.currentText() if self.x_pos_field.isEnabled() else None,
                'y_pos': self.y_pos.value(),
                'y_pos_field': self.y_pos_field.currentText() if self.y_pos_field.isEnabled() else None,
                'width': self.width_val.value(),
                'width_field': self.width_field.currentText() if self.width_field.isEnabled() else None,
                'height': self.height_val.value(),
                'height_field': self.height_field.currentText() if self.height_field.isEnabled() else None,
                'color_field': self.color_field.currentText(),
                'colormap': self.colormap.currentText(),
                'color_label': self.color_label.text() if self.color_label.isEnabled() else None,
                'color_unit': [self.color_unit_from.text(), self.color_unit_to.text()] if self.color_unit_from.isEnabled() else None}

    def set_field_names(self, text):
        data_names = list(self.data_objs[text].data)
        for field in ['x_pos_field', 'y_pos_field', 'width_field', 'height_field', 'color_field']:
            combo = getattr(self, field)
            combo.clear()
            combo.addItems(data_names)

    @staticmethod
    def get_default_values():
        return dict(visible=True, draw_order=0, legend_text=None, data_name=None, interpolation='Nearest', x_pos=0, x_pos_field=None, y_pos=0, y_pos_field=None, width=1, width_field=None, height=1, height_field=None, color_field=None, colormap='viridis', color_label=None, color_unit=None)

class InfiniteLineWidget(qtwidgets.QWidget):
    def __init__(self, data_objs, axis_type, artist):
        super().__init__()
        self.setLayout(qtwidgets.QFormLayout())

        self.data_objs = data_objs

        self.visible_val, self.draw_order, self.legend_text = add_common_widgets(self.layout(), artist['visible'], artist['draw_order'], artist['legend_text'])
        self.data_name = add_optional_combobox(self.layout(), 'Data Name:', artist['data_name'] is not None)
        self.data_name.currentTextChanged.connect(self.set_field_names)
        pos_group = qtwidgets.QGroupBox('Position')
        pos_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(pos_group)
        self.is_vertical = qtwidgets.QCheckBox()
        self.is_vertical.setChecked(artist['is_vertical'])
        pos_group.layout().addRow('Is Vertical:', self.is_vertical)
        self.pos_val = add_spinbox(pos_group.layout(), 'Position:', float('-inf'), float('inf'), artist['pos'])
        self.pos_field = add_optional_combobox(pos_group.layout(), 'Position Field:', artist['pos_field'] is not None)
        color_group = qtwidgets.QGroupBox('Color')
        color_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(color_group)
        self.color, self.color_field, self.colormap, self.color_label, self.color_unit_from, self.color_unit_to = add_color_widgets(color_group.layout(), artist['color'], artist['color_field'], artist['colormap'], artist['color_label'], artist['color_unit'])

        self.data_name.addItems(list(self.data_objs))
        if artist['data_name'] is not None:
            self.data_name.setCurrentText(artist['data_name'])
            self.pos_field.setCurrentText(artist['pos_field'])
            self.color_field.setCurrentText(artist['color_field'])

    def get_values(self):
        return {'artist_type': 'infinite line',
                'visible': self.visible_val.isChecked(),
                'draw_order': self.draw_order.value(),
                'legend_text': self.legend_text.text() if self.legend_text.isEnabled() else None,
                'data_name': self.data_name.currentText() if self.data_name.isEnabled() else None,
                'is_vertical': self.is_vertical.isChecked(),
                'pos': self.pos_val.value(),
                'pos_field': self.pos_field.currentText() if self.data_name.isEnabled() and self.pos_field.isEnabled() else None,
                'color': self.color.get_color(),
                'color_field': self.color_field.currentText() if self.data_name.isEnabled() and self.color_field.isEnabled() else None,
                'colormap': self.colormap.currentText(),
                'color_label': self.color_label.text() if self.color_label.isEnabled() else None,
                'color_unit': [self.color_unit_from.text(), self.color_unit_to.text()] if self.color_unit_from.isEnabled() else None}

    def set_field_names(self, text):
        data_names = list(self.data_objs[text].data)
        for field in ['pos_field', 'color_field']:
            combo = getattr(self, field)
            combo.clear()
            combo.addItems(data_names)

    @staticmethod
    def get_default_values():
        return dict(visible=True, draw_order=0, legend_text=None, data_name=None, is_vertical=True, pos=0, pos_field=None, color='r', color_field=None, colormap='viridis', color_label=None, color_unit=None)

class PolygonWidget(qtwidgets.QWidget):
    def __init__(self, data_objs, axis_type, artist):
        super().__init__()
        self.setLayout(qtwidgets.QFormLayout())

        self.data_objs = data_objs

        self.visible_val, self.draw_order, self.legend_text = add_common_widgets(self.layout(), artist['visible'], artist['draw_order'], artist['legend_text'])
        self.data_name = qtwidgets.QComboBox()
        self.data_name.currentTextChanged.connect(self.set_field_names)
        self.layout().addRow('Data Name:', self.data_name)
        self.x_field = qtwidgets.QComboBox()
        self.layout().addRow('X Field:', self.x_field)
        self.y_field = qtwidgets.QComboBox()
        self.layout().addRow('Y Field:', self.y_field)

        color_group = qtwidgets.QGroupBox('Color')
        color_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(color_group)
        self.color, self.color_field, self.colormap, self.color_label, self.color_unit_from, self.color_unit_to = add_color_widgets(color_group.layout(), artist['color'], artist['color_field'], artist['colormap'], artist['color_label'], artist['color_unit'])
        edge_group = qtwidgets.QGroupBox('Rectangle Edge')
        edge_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(edge_group)
        self.edge_width = add_spinbox(edge_group.layout(), 'Width:', 0.0, float('inf'), artist['edge_width'])
        self.edge_width_field = add_optional_combobox(edge_group.layout(), 'Width Field:', artist['edge_width_field'] is not None)
        self.edge_color, self.edge_color_field, self.edge_colormap, self.edge_color_label, self.edge_color_unit_from, self.edge_color_unit_to = add_color_widgets(edge_group.layout(), artist['edge_color'], artist['edge_color_field'], artist['edge_colormap'], artist['edge_color_label'], artist['edge_color_unit'])

        self.data_name.addItems(list(self.data_objs))
        if artist['data_name'] is not None:
            self.data_name.setCurrentText(artist['data_name'])
            self.x_field.setCurrentText(artist['x_field'])
            self.y_field.setCurrentText(artist['y_field'])
            self.color_field.setCurrentText(artist['color_field'])
            self.edge_width_field.setCurrentText(artist['edge_width_field'])
            self.edge_color_field.setCurrentText(artist['edge_color_field'])

    def get_values(self):
        return {'artist_type': 'polygon',
                'visible': self.visible_val.isChecked(),
                'draw_order': self.draw_order.value(),
                'legend_text': self.legend_text.text() if self.legend_text.isEnabled() else None,
                'data_name': self.data_name.currentText(),
                'x_field': self.x_field.currentText(),
                'y_field': self.y_field.currentText(),
                'color': self.color.get_color(),
                'color_field': self.color_field.currentText() if self.color_field.isEnabled() else None,
                'colormap': self.colormap.currentText(),
                'color_label': self.color_label.text() if self.color_label.isEnabled() else None,
                'color_unit': [self.color_unit_from.text(), self.color_unit_to.text()] if self.color_unit_from.isEnabled() else None,
                'edge_width': self.edge_width.value(),
                'edge_width_field': self.edge_width_field.currentText() if self.edge_width_field.isEnabled() else None,
                'edge_color': self.edge_color.get_color(),
                'edge_color_field': self.edge_color_field.currentText() if self.edge_color_field.isEnabled() else None,
                'edge_colormap': self.edge_colormap.currentText(),
                'edge_color_label': self.edge_color_label.text() if self.edge_color_label.isEnabled() else None,
                'edge_color_unit': [self.edge_color_unit_from.text(), self.edge_color_unit_to.text()] if self.edge_color_unit_from.isEnabled() else None}

    def set_field_names(self, text):
        data_names = list(self.data_objs[text].data)
        for field in ['x_field', 'y_field', 'color_field', 'edge_width_field', 'edge_color_field']:
            combo = getattr(self, field)
            combo.clear()
            combo.addItems(data_names)

    @staticmethod
    def get_default_values():
        return dict(visible=True, draw_order=0, legend_text=None, data_name=None, x_field=None, y_field=None, color='g', color_field=None, colormap='viridis', color_label=None, color_unit=None, edge_width=0, edge_width_field=None, edge_color='g', edge_color_field=None, edge_colormap='viridis', edge_color_label=None, edge_color_unit=None)

class RectangleWidget(qtwidgets.QWidget):
    def __init__(self, data_objs, axis_type, artist):
        super().__init__()
        self.setLayout(qtwidgets.QFormLayout())

        self.data_objs = data_objs

        self.visible_val, self.draw_order, self.legend_text = add_common_widgets(self.layout(), artist['visible'], artist['draw_order'], artist['legend_text'])
        self.data_name = add_optional_combobox(self.layout(), 'Data Name:', artist['data_name'] is not None)
        self.data_name.currentTextChanged.connect(self.set_field_names)

        pos_group = qtwidgets.QGroupBox('Position')
        pos_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(pos_group)
        self.x_pos = add_spinbox(pos_group.layout(), 'X Position:', float('-inf'), float('inf'), artist['x_pos'])
        self.x_pos_field = add_optional_combobox(pos_group.layout(), 'X Position Field:', artist['x_pos_field'] is not None)
        self.y_pos = add_spinbox(pos_group.layout(), 'Y Position:', float('-inf'), float('inf'), artist['y_pos'])
        self.y_pos_field = add_optional_combobox(pos_group.layout(), 'Y Position Field:', artist['y_pos_field'] is not None)
        self.width_val = add_spinbox(pos_group.layout(), 'Width:', 0.0, float('inf'), artist['width'])
        self.width_field = add_optional_combobox(pos_group.layout(), 'Width Field:', artist['width_field'] is not None)
        self.height_val = add_spinbox(pos_group.layout(), 'Height:', 0.0, float('inf'), artist['height'])
        self.height_field = add_optional_combobox(pos_group.layout(), 'Height Field:', artist['height_field'] is not None)
        color_group = qtwidgets.QGroupBox('Color')
        color_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(color_group)
        self.color, self.color_field, self.colormap, self.color_label, self.color_unit_from, self.color_unit_to = add_color_widgets(color_group.layout(), artist['color'], artist['color_field'], artist['colormap'], artist['color_label'], artist['color_unit'])
        edge_group = qtwidgets.QGroupBox('Rectangle Edge')
        edge_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(edge_group)
        self.edge_width = add_spinbox(edge_group.layout(), 'Width:', 0.0, float('inf'), artist['edge_width'])
        self.edge_width_field = add_optional_combobox(edge_group.layout(), 'Width Field:', artist['edge_width_field'] is not None)
        self.edge_color, self.edge_color_field, self.edge_colormap, self.edge_color_label, self.edge_color_unit_from, self.edge_color_unit_to = add_color_widgets(edge_group.layout(), artist['edge_color'], artist['edge_color_field'], artist['edge_colormap'], artist['edge_color_label'], artist['edge_color_unit'])

        self.data_name.addItems(list(self.data_objs))
        if artist['data_name'] is not None:
            self.data_name.setCurrentText(artist['data_name'])
            self.x_pos_field.setCurrentText(artist['x_pos_field'])
            self.y_pos_field.setCurrentText(artist['y_pos_field'])
            self.width_field.setCurrentText(artist['width_field'])
            self.height_field.setCurrentText(artist['height_field'])
            self.color_field.setCurrentText(artist['color_field'])
            self.edge_width_field.setCurrentText(artist['edge_width_field'])
            self.edge_color_field.setCurrentText(artist['edge_color_field'])

    def get_values(self):
        return {'artist_type': 'rectangle',
                'visible': self.visible_val.isChecked(),
                'draw_order': self.draw_order.value(),
                'legend_text': self.legend_text.text() if self.legend_text.isEnabled() else None,
                'data_name': self.data_name.currentText() if self.data_name.isEnabled() else None,
                'x_pos': self.x_pos.value(),
                'x_pos_field': self.x_pos_field.currentText() if self.data_name.isEnabled() and self.x_pos_field.isEnabled() else None,
                'y_pos': self.y_pos.value(),
                'y_pos_field': self.y_pos_field.currentText() if self.data_name.isEnabled() and self.y_pos_field.isEnabled() else None,
                'width': self.width_val.value(),
                'width_field': self.width_field.currentText() if self.data_name.isEnabled() and self.width_field.isEnabled() else None,
                'height': self.height_val.value(),
                'height_field': self.height_field.currentText() if self.data_name.isEnabled() and self.height_field.isEnabled() else None,
                'color': self.color.get_color(),
                'color_field': self.color_field.currentText() if self.data_name.isEnabled() and self.color_field.isEnabled() else None,
                'colormap': self.colormap.currentText(),
                'color_label': self.color_label.text() if self.color_label.isEnabled() else None,
                'color_unit': [self.color_unit_from.text(), self.color_unit_to.text()] if self.color_unit_from.isEnabled() else None,
                'edge_width': self.edge_width.value(),
                'edge_width_field': self.edge_width_field.currentText() if self.data_name.isEnabled() and self.edge_width_field.isEnabled() else None,
                'edge_color': self.edge_color.get_color(),
                'edge_color_field': self.edge_color_field.currentText() if self.data_name.isEnabled() and self.edge_color_field.isEnabled() else None,
                'edge_colormap': self.edge_colormap.currentText(),
                'edge_color_label': self.edge_color_label.text() if self.edge_color_label.isEnabled() else None,
                'edge_color_unit': [self.edge_color_unit_from.text(), self.edge_color_unit_to.text()] if self.edge_color_unit_from.isEnabled() else None}

    def set_field_names(self, text):
        data_names = list(self.data_objs[text].data)
        for field in ['x_pos_field', 'y_pos_field', 'width_field', 'height_field', 'color_field', 'edge_width_field', 'edge_color_field']:
            combo = getattr(self, field)
            combo.clear()
            combo.addItems(data_names)

    @staticmethod
    def get_default_values():
        return dict(visible=True, draw_order=0, legend_text=None, data_name=None, x_pos=0, x_pos_field=None, y_pos=0, y_pos_field=None, width=1, width_field=None, height=1, height_field=None, color='g', color_field=None, colormap='viridis', color_label=None, color_unit=None, edge_width=0, edge_width_field=None, edge_color='g', edge_color_field=None, edge_colormap='viridis', edge_color_label=None, edge_color_unit=None)

class ScatterWidget(qtwidgets.QWidget):
    def __init__(self, data_objs, axis_type, artist):
        super().__init__()
        self.setLayout(qtwidgets.QFormLayout())

        self.data_objs = data_objs

        self.visible_val, self.draw_order, self.legend_text = add_common_widgets(self.layout(), artist['visible'], artist['draw_order'], artist['legend_text'])
        self.selectable = qtwidgets.QCheckBox()
        self.selectable.setChecked(artist['selectable'])
        self.layout().addRow('Selectable:', self.selectable)
        self.data_name = qtwidgets.QComboBox()
        self.data_name.currentTextChanged.connect(self.set_field_names)
        self.layout().addRow('Data Name:', self.data_name)
        self.label_field = add_optional_combobox(self.layout(), 'Label Field:', artist['label_field'] is not None)
        self.label_size = add_spinbox(self.layout(), 'Label Size:', 0.0, float('inf'), artist['label_size'])

        pos_group = qtwidgets.QGroupBox('Position')
        pos_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(pos_group)
        self.x_field = qtwidgets.QComboBox()
        pos_group.layout().addRow('X Field:', self.x_field)
        self.y_field = qtwidgets.QComboBox()
        pos_group.layout().addRow('Y Field:', self.y_field)
        if axis_type == '3d':
            self.z_field = qtwidgets.QComboBox()
            pos_group.layout().addRow('Z Field:', self.z_field)
        else:
            self.z_field = None

        line_group = qtwidgets.QGroupBox('Line')
        line_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(line_group)
        self.line_width = add_spinbox(line_group.layout(), 'Width:', 0.0, float('inf'), artist['line_width'])
        self.line_color, self.line_color_field, self.line_colormap, self.line_color_label, self.line_color_unit_from, self.line_color_unit_to = add_color_widgets(line_group.layout(), artist['line_color'], artist['line_color_field'], artist['line_colormap'], artist['line_color_label'], artist['line_color_unit'])

        marker_group = qtwidgets.QGroupBox('Marker')
        marker_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(marker_group)
        self.marker = qtwidgets.QComboBox()
        self.marker.addItems(sorted(vpvisuals.marker_types))
        self.marker.setCurrentText(artist['marker'])
        marker_group.layout().addRow('Marker:', self.marker)
        self.marker_size = add_spinbox(marker_group.layout(), 'Size:', 0.0, float('inf'), artist['marker_size'])
        self.marker_color, self.marker_color_field, self.marker_colormap, self.marker_color_label, self.marker_color_unit_from, self.marker_color_unit_to = add_color_widgets(marker_group.layout(), artist['marker_color'], artist['marker_color_field'], artist['marker_colormap'], artist['marker_color_label'], artist['marker_color_unit'])

        edge_group = qtwidgets.QGroupBox('Marker Edge')
        edge_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(edge_group)
        self.edge_width = add_spinbox(edge_group.layout(), 'Width:', 0.0, float('inf'), artist['edge_width'])
        self.edge_color, self.edge_color_field, self.edge_colormap, self.edge_color_label, self.edge_color_unit_from, self.edge_color_unit_to = add_color_widgets(edge_group.layout(), artist['edge_color'], artist['edge_color_field'], artist['edge_colormap'], artist['edge_color_label'], artist['edge_color_unit'])

        self.data_name.addItems(list(self.data_objs))
        if artist['data_name'] is not None:
            self.data_name.setCurrentText(artist['data_name'])
            self.label_field.setCurrentText(artist['label_field'])
            self.x_field.setCurrentText(artist['x_field'])
            self.y_field.setCurrentText(artist['y_field'])
            self.line_color_field.setCurrentText(artist['line_color_field'])
            self.marker_color_field.setCurrentText(artist['marker_color_field'])
            self.edge_color_field.setCurrentText(artist['edge_color_field'])
            if self.z_field is not None:
                self.z_field.setCurrentText(artist['z_field'])

    def get_values(self):
        return {'artist_type': 'scatter',
                'visible': self.visible_val.isChecked(),
                'draw_order': self.draw_order.value(),
                'legend_text': self.legend_text.text() if self.legend_text.isEnabled() else None,
                'selectable': self.selectable.isChecked(),
                'data_name': self.data_name.currentText(),
                'label_field': self.label_field.currentText() if self.label_field.isEnabled() else None,
                'label_size': self.label_size.value(),
                'x_field': self.x_field.currentText(),
                'y_field': self.y_field.currentText(),
                'z_field': None if self.z_field is None else self.z_field.currentText(),
                'line_width': self.line_width.value(),
                'line_color': self.line_color.get_color(),
                'line_color_field': self.line_color_field.currentText() if self.line_color_field.isEnabled() else None,
                'line_colormap': self.line_colormap.currentText(),
                'line_color_label': self.line_color_label.text() if self.line_color_label.isEnabled() else None,
                'line_color_unit': [self.line_color_unit_from.text(), self.line_color_unit_to.text()] if self.line_color_unit_from.isEnabled() else None,
                'marker': self.marker.currentText(),
                'marker_size': self.marker_size.value(),
                'marker_color': self.marker_color.get_color(),
                'marker_color_field': self.marker_color_field.currentText() if self.marker_color_field.isEnabled() else None,
                'marker_colormap': self.marker_colormap.currentText(),
                'marker_color_label': self.marker_color_label.text() if self.marker_color_label.isEnabled() else None,
                'marker_color_unit': [self.marker_color_unit_from.text(), self.marker_color_unit_to.text()] if self.marker_color_unit_from.isEnabled() else None,
                'edge_width': self.edge_width.value(),
                'edge_color': self.edge_color.get_color(),
                'edge_color_field': self.edge_color_field.currentText() if self.edge_color_field.isEnabled() else None,
                'edge_colormap': self.edge_colormap.currentText(),
                'edge_color_label': self.edge_color_label.text() if self.edge_color_label.isEnabled() else None,
                'edge_color_unit': [self.edge_color_unit_from.text(), self.edge_color_unit_to.text()] if self.edge_color_unit_from.isEnabled() else None}

    def set_field_names(self, text):
        data_names = list(self.data_objs[text].data)
        for field in ['label_field', 'x_field', 'y_field', 'line_color_field', 'marker_color_field', 'edge_color_field']:
            combo = getattr(self, field)
            combo.clear()
            combo.addItems(data_names)
        if self.z_field is not None:
            self.z_field.clear()
            self.z_field.addItems(data_names)

    @staticmethod
    def get_default_values():
        return dict(visible=True, draw_order=0, legend_text=None, selectable=True, data_name=None, label_field=None, label_size=10, x_field=None, y_field=None, z_field=None, line_width=1, line_color='r', line_color_field=None, line_colormap='viridis', line_color_label=None, line_color_unit=None, marker='o', marker_size=10, marker_color='g', marker_color_field=None, marker_colormap='viridis', marker_color_label=None, marker_color_unit=None, edge_width=0, edge_color='g', edge_color_field=None, edge_colormap='viridis', edge_color_label=None, edge_color_unit=None)

class SurfaceWidget(qtwidgets.QWidget):
    def __init__(self, data_objs, axis_type, artist):
        super().__init__()
        self.setLayout(qtwidgets.QFormLayout())

        self.data_objs = data_objs

        self.visible_val, self.draw_order, self.legend_text = add_common_widgets(self.layout(), artist['visible'], artist['draw_order'], artist['legend_text'])
        self.data_name = qtwidgets.QComboBox()
        self.data_name.currentTextChanged.connect(self.set_field_names)
        self.layout().addRow('Data Name:', self.data_name)
        pos_group = qtwidgets.QGroupBox('Position')
        pos_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(pos_group)
        self.x_field = qtwidgets.QComboBox()
        pos_group.layout().addRow('X Field:', self.x_field)
        self.y_field = qtwidgets.QComboBox()
        pos_group.layout().addRow('Y Field:', self.y_field)
        self.z_field = qtwidgets.QComboBox()
        pos_group.layout().addRow('Z Field:', self.z_field)
        color_group = qtwidgets.QGroupBox('Color')
        color_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(color_group)
        self.color, self.color_field, self.colormap, self.color_label, self.color_unit_from, self.color_unit_to = add_color_widgets(color_group.layout(), artist['color'], artist['color_field'], artist['colormap'], artist['color_label'], artist['color_unit'])

        self.data_name.addItems(list(self.data_objs))
        if artist['data_name'] is not None:
            self.data_name.setCurrentText(artist['data_name'])
            self.x_field.setCurrentText(artist['x_field'])
            self.y_field.setCurrentText(artist['y_field'])
            self.z_field.setCurrentText(artist['z_field'])
            self.color_field.setCurrentText(artist['color_field'])

    def get_values(self):
        return {'artist_type': 'surface',
                'visible': self.visible_val.isChecked(),
                'draw_order': self.draw_order.value(),
                'legend_text': self.legend_text.text() if self.legend_text.isEnabled() else None,
                'data_name': self.data_name.currentText(),
                'x_field': self.x_field.currentText(),
                'y_field': self.y_field.currentText(),
                'z_field': self.z_field.currentText(),
                'color': self.color.get_color(),
                'color_field': self.color_field.currentText() if self.color_field.isEnabled() else None,
                'colormap': self.colormap.currentText(),
                'color_label': self.color_label.text() if self.color_label.isEnabled() else None,
                'color_unit': [self.color_unit_from.text(), self.color_unit_to.text()] if self.color_unit_from.isEnabled() else None}

    def set_field_names(self, text):
        data_names = list(self.data_objs[text].data)
        for field in ['x_field', 'y_field', 'z_field', 'color_field']:
            combo = getattr(self, field)
            combo.clear()
            combo.addItems(data_names)

    @staticmethod
    def get_default_values():
        return dict(visible=True, draw_order=0, legend_text=None, data_name=None, x_field=None, y_field=None, z_field=None, color='g', color_field=None, colormap='viridis', color_label=None, color_unit=None)

class TextWidget(qtwidgets.QWidget):
    def __init__(self, data_objs, axis_type, artist):
        super().__init__()
        self.setLayout(qtwidgets.QFormLayout())

        self.data_objs = data_objs

        self.visible_val, self.draw_order, self.legend_text = add_common_widgets(self.layout(), artist['visible'], artist['draw_order'], artist['legend_text'])
        self.data_name = qtwidgets.QComboBox()
        self.data_name.currentTextChanged.connect(self.set_field_names)
        self.layout().addRow('Data Name:', self.data_name)
        self.text_field = qtwidgets.QComboBox()
        self.layout().addRow('Text Field:', self.text_field)

        pos_group = qtwidgets.QGroupBox('Position')
        pos_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(pos_group)
        self.x_field = qtwidgets.QComboBox()
        pos_group.layout().addRow('X Field:', self.x_field)
        self.y_field = qtwidgets.QComboBox()
        pos_group.layout().addRow('Y Field:', self.y_field)
        if axis_type == '3d':
            self.z_field = qtwidgets.QComboBox()
            pos_group.layout().addRow('Z Field:', self.z_field)
        else:
            self.z_field = None

        appearance_group = qtwidgets.QGroupBox('Appearance')
        appearance_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(appearance_group)
        self.x_anchor = qtwidgets.QComboBox()
        self.x_anchor.addItems(['left', 'center', 'right'])
        self.x_anchor.setCurrentText(artist['x_anchor'])
        appearance_group.layout().addRow('X Anchor:', self.x_anchor)
        self.y_anchor = qtwidgets.QComboBox()
        self.y_anchor.addItems(['top', 'center', 'bottom'])
        self.y_anchor.setCurrentText(artist['y_anchor'])
        appearance_group.layout().addRow('Y Anchor:', self.y_anchor)
        self.font_size = add_spinbox(appearance_group.layout(), 'Font Size:', 0.0, float('inf'), artist['font_size'])
        self.bold = qtwidgets.QCheckBox()
        self.bold.setChecked(artist['bold'])
        appearance_group.layout().addRow('Bold:', self.bold)
        self.italic = qtwidgets.QCheckBox()
        self.italic.setChecked(artist['italic'])
        appearance_group.layout().addRow('Italic:', self.italic)

        color_group = qtwidgets.QGroupBox('Color')
        color_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addRow(color_group)
        self.color, self.color_field, self.colormap, self.color_label, self.color_unit_from, self.color_unit_to = add_color_widgets(color_group.layout(), artist['color'], artist['color_field'], artist['colormap'], artist['color_label'], artist['color_unit'])

        self.data_name.addItems(list(self.data_objs))
        if artist['data_name'] is not None:
            self.data_name.setCurrentText(artist['data_name'])
            self.text_field.setCurrentText(artist['text_field'])
            self.x_field.setCurrentText(artist['x_field'])
            self.y_field.setCurrentText(artist['y_field'])
            self.color_field.setCurrentText(artist['color_field'])
            if self.z_field is not None:
                self.z_field.setCurrentText(artist['z_field'])

    def get_values(self):
        return {'artist_type': 'text',
                'visible': self.visible_val.isChecked(),
                'draw_order': self.draw_order.value(),
                'legend_text': self.legend_text.text() if self.legend_text.isEnabled() else None,
                'data_name': self.data_name.currentText(),
                'text_field': self.text_field.currentText(),
                'x_field': self.x_field.currentText(),
                'y_field': self.y_field.currentText(),
                'z_field': None if self.z_field is None else self.z_field.currentText(),
                'x_anchor': self.x_anchor.currentText(),
                'y_anchor': self.y_anchor.currentText(),
                'font_size': self.font_size.value(),
                'bold': self.bold.isChecked(),
                'italic': self.italic.isChecked(),
                'color': self.color.get_color(),
                'color_field': self.color_field.currentText() if self.color_field.isEnabled() else None,
                'colormap': self.colormap.currentText(),
                'color_label': self.color_label.text() if self.color_label.isEnabled() else None,
                'color_unit': [self.color_unit_from.text(), self.color_unit_to.text()] if self.color_unit_from.isEnabled() else None}

    def set_field_names(self, text):
        data_names = list(self.data_objs[text].data)
        for field in ['text_field', 'x_field', 'y_field', 'color_field']:
            combo = getattr(self, field)
            combo.clear()
            combo.addItems(data_names)
        if self.z_field is not None:
            self.z_field.clear()
            self.z_field.addItems(data_names)

    @staticmethod
    def get_default_values():
        return dict(visible=True, draw_order=0, legend_text=None, data_name=None, text_field=None, x_field=None, y_field=None, z_field=None, x_anchor='center', y_anchor='center', font_size=12, bold=False, italic=False, color='black', color_field=None, colormap='viridis', color_label=None, color_unit=None)

def add_color_widgets(layout, color, color_field, colormap, color_label, color_unit):
    if color is None:
        color_widget = None
        color_field_widget = qtwidgets.QComboBox()
        layout.addRow('Color Field:', color_field_widget)
    else:
        color_widget = custom_qt.ColorButton(color)
        layout.addRow('Color:', color_widget)
        color_field_widget = add_optional_combobox(layout, 'Color Field:', color_field is not None)
    colormap_widget = custom_qt.ColormapCombo()
    colormap_widget.setCurrentText(colormap)
    layout.addRow('Colormap:', colormap_widget)
    color_label_widget = add_optional_line_edit(layout, 'Color Label:', color_label)
    color_unit_from, color_unit_to = add_unit_widgets(layout, 'Color Units:', color_unit)
    return color_widget, color_field_widget, colormap_widget, color_label_widget, color_unit_from, color_unit_to

def add_common_widgets(layout, visible, draw_order, legend_text):
    visible_check = qtwidgets.QCheckBox()
    visible_check.setChecked(visible)
    layout.addRow('Visible:', visible_check)
    draw_spin_box = add_spinbox(layout, 'Draw Order:', float('-inf'), float('inf'), draw_order)
    legend_line_edit = add_optional_line_edit(layout, 'Legend Text:', legend_text)
    return visible_check, draw_spin_box, legend_line_edit

def add_optional_combobox(layout, label, checked):
    hbox = qtwidgets.QHBoxLayout()
    layout.addRow(label, hbox)
    use_combo = qtwidgets.QCheckBox()
    use_combo.toggled.connect(lambda checked: combo.setEnabled(checked))
    hbox.addWidget(use_combo, 0)
    combo = qtwidgets.QComboBox()
    combo.setEnabled(False)
    hbox.addWidget(combo, 1)
    use_combo.setChecked(checked)
    return combo

def add_optional_line_edit(layout, label, text):
    hbox = qtwidgets.QHBoxLayout()
    layout.addRow(label, hbox)
    use_line_edit = qtwidgets.QCheckBox()
    use_line_edit.toggled.connect(lambda checked: line_edit.setEnabled(checked))
    hbox.addWidget(use_line_edit, 0)
    line_edit = qtwidgets.QLineEdit('' if text is None else text)
    line_edit.setEnabled(False)
    hbox.addWidget(line_edit, 1)
    use_line_edit.setChecked(text is not None)
    return line_edit

def add_spinbox(layout, label, min_val, max_val, value):
    spin_box = qtwidgets.QDoubleSpinBox()
    spin_box.setDecimals(6)
    spin_box.setRange(min_val, max_val)
    spin_box.setValue(value)
    layout.addRow(label, spin_box)
    return spin_box

def add_unit_widgets(layout, label, unit):
    hbox = qtwidgets.QHBoxLayout()
    layout.addRow(label, hbox)
    convert_units = qtwidgets.QCheckBox()
    convert_units.toggled.connect(lambda checked: set_unit_state(unit_from, unit_to, checked))
    hbox.addWidget(convert_units, 0)
    unit_from = qtwidgets.QLineEdit('' if unit is None else unit[0])
    unit_from.setEnabled(False)
    hbox.addWidget(unit_from, 1)
    hbox.addWidget(qtwidgets.QLabel('to'), 0)
    unit_to = qtwidgets.QLineEdit('' if unit is None else unit[1])
    unit_to.setEnabled(False)
    hbox.addWidget(unit_to, 1)
    convert_units.setChecked(unit is not None)
    return unit_from, unit_to

def create_artist_widget(data_objs, axis_type, artist):
    artist_type = artist['artist_type']
    if artist_type == 'arrow':
        return ArrowWidget(data_objs, axis_type, artist)
    elif artist_type == 'box':
        return BoxWidget(data_objs, axis_type, artist)
    elif artist_type == 'ellipse':
        return EllipseWidget(data_objs, axis_type, artist)
    elif artist_type == 'image':
        return ImageWidget(data_objs, axis_type, artist)
    elif artist_type == 'infinite line':
        return InfiniteLineWidget(data_objs, axis_type, artist)
    elif artist_type == 'polygon':
        return PolygonWidget(data_objs, axis_type, artist)
    elif artist_type == 'rectangle':
        return RectangleWidget(data_objs, axis_type, artist)
    elif artist_type == 'scatter':
        return ScatterWidget(data_objs, axis_type, artist)
    elif artist_type == 'surface':
        return SurfaceWidget(data_objs, axis_type, artist)
    elif artist_type == 'text':
        return TextWidget(data_objs, axis_type, artist)

def get_artist_defaults(artist_type):
    if artist_type == 'arrow':
        return ArrowWidget.get_default_values()
    elif artist_type == 'box':
        return BoxWidget.get_default_values()
    elif artist_type == 'ellipse':
        return EllipseWidget.get_default_values()
    elif artist_type == 'image':
        return ImageWidget.get_default_values()
    elif artist_type == 'infinite line':
        return InfiniteLineWidget.get_default_values()
    elif artist_type == 'polygon':
        return PolygonWidget.get_default_values()
    elif artist_type == 'rectangle':
        return RectangleWidget.get_default_values()
    elif artist_type == 'scatter':
        return ScatterWidget.get_default_values()
    elif artist_type == 'surface':
        return SurfaceWidget.get_default_values()
    elif artist_type == 'text':
        return TextWidget.get_default_values()

def set_unit_state(from_unit, to_unit, enabled):
    from_unit.setEnabled(enabled)
    to_unit.setEnabled(enabled)