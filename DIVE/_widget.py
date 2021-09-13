from ._components.dive_manager import DIVEManager as _DIVEManager
import importlib as _importlib
import vispy as _vp
qt = _vp.app.use_app().backend_name
try:
    _qtcore = _importlib.import_module('{}.QtCore'.format(qt))
    _qtwidgets = _importlib.import_module('{}.QtWidgets'.format(qt))
except:
    pass
else:
    del qt

class DIVEWidget(_qtwidgets.QWidget):
    """
    The main Qt widget for DIVE.

    Parameters
    ----------
    unit_reg : None, pint.UnitRegistry (Default: None)
        The unit registry to use for unit conversions.
        If None, the default UnitRegistry in pint will be used.
        Only valid if the "pint" module has been installed.
    *args
        Any parameters that are accepted by a QWidget.
    **kwargs
        Any keyword parameters that are accepted by a QWidget.

    Signals
    -------
    current_time_changed
        This signal is sent whenever the current time changes in DIVE.
    """
    current_time_changed = _qtcore.pyqtSignal() if hasattr(_qtcore, 'pyqtSignal') else _qtcore.Signal()

    def __init__(self, unit_reg=None, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.setWindowTitle('Data Interface for Visual Exploration')
        self._dive_manager = _DIVEManager(self, unit_reg)

    def add_arrow_artist(self, axis_name, name, data_name, x_field, y_field, z_field=None, label_field=None, label_size=10, visible=True, draw_order=0, legend_text=None, selectable=True,
                         line_width=1, line_color='r', line_color_field=None, line_colormap='viridis', line_color_label=None, line_color_unit=None,
                         arrow_shape='stealth', arrow_spacing=0, show_last_arrow=True, arrow_size=10,
                         arrow_color='g', arrow_color_field=None, arrow_colormap='viridis', arrow_color_label=None, arrow_color_unit=None):
        """
        Add an arrow artist to an axis in DIVE.

        Parameters
        ----------
        axis_name : str
            The name of the axis that this artist should be added to.
        name : str
            The name of this artist.
        data_name : str
            The name of the data object to use for this artist.
        x_field : str
            The name of the field in the data object that contains the x coordinates for this artist.
        y_field : str
            The name of the field in the data object that contains the y coordinates for this artist.
        z_field : None, str (Default: None)
            The name of the field in the data object that contains the z coordinates for this artist.
            If None, this artist will be two-dimensional.
        label_field : None, str (Default: None)
            The name of the field in the data object that contains labels for each data point.
            If None, labels will not be shown.
        label_size : numeric (Default: 10)
            The font size to use for labels.
        visible : bool (Default: True)
            Toggle whether this artist is visible.
        draw_order : numeric (Default: 0)
            The number used to determine the draw order for this artist.
            Artists with small "draw_order" values are drawn before artists with large "draw_order" values.
        legend_text : None, str (Default: None)
            The label to display in the legend for this artist.
            If None, this artist will not appear in the legend.
        selectable : bool (Default: True)
            Toggle whether this artist is selectable.
        line_width : numeric (Default: 1)
            The width of the lines.
            If 0, lines are not shown.
        line_color : str (Default: "r")
            The color to use for the lines.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "line_color_field" is None.
        line_color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the lines.
        line_colormap: str (Default: "viridis")
            The name of the colormap to use for the lines.
            Only used if "line_color_field" is not None.
        line_color_label: None, str (Default: None)
            The label to use for line color values on the colorbar.
            Only used if "line_color_field" is not None.
        line_color_unit: None, array (Default: None)
            The unit to use for line color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "line_color_field" is not None.
        arrow_shape: str (Default: "stealth")
            The shape to use for the arrow heads.
        arrow_spacing: int (Default: 0)
            The number of data points between each arrow head.
            If 0, arrow heads will only be shown for the last data point.
        show_last_arrow: bool (Default: True)
            Toggle display of last arrow head even if "arrow_spacing" would exclude it.
            Only used if "arrow_spacing" is not 0.
        arrow_size: numeric (Default: 10)
            The size of the arrow heads.
        arrow_color : str (Default: "g")
            The color to use for the arrow heads.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "arrow_color_field" is None.
        arrow_color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the arrow heads.
        arrow_colormap: str (Default: "viridis")
            The name of the colormap to use for the arrow heads.
            Only used if "arrow_color_field" is not None.
        arrow_color_label: None, str (Default: None)
            The label to use for arrow head color values on the colorbar.
            Only used if "arrow_color_field" is not None.
        arrow_color_unit: None, array (Default: None)
            The unit to use for arrow head color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "arrow_color_field" is not None.

        Notes
        -----
        If the data object has an ID field, lines will only connect points with the same ID.

        When multiple color fields are in use in an axis (either in a single artist or across multiple artists),
        all color fields that have the same colormap, color_label, and color_unit will share the same colorbar.

        All colorbar values that aren't numeric or timestamps (with tz),
        will instead be displayed in the legend (as long as "legend_text" is not None).

        It is possible to cycle through the colorbars in an axis by clicking on the colorbar.
        """
        self._dive_manager.add_artist(axis_name, 'arrow', dict(name=name, data_name=data_name, x_field=x_field, y_field=y_field, z_field=z_field, label_field=label_field, label_size=label_size, visible=visible, draw_order=draw_order, legend_text=legend_text, selectable=selectable,
                                                               line_width=line_width, line_color=line_color, line_color_field=line_color_field, line_colormap=line_colormap, line_color_label=line_color_label, line_color_unit=line_color_unit,
                                                               arrow_shape=arrow_shape, arrow_spacing=arrow_spacing, show_last_arrow=show_last_arrow, arrow_size=arrow_size,
                                                               arrow_color=arrow_color, arrow_color_field=arrow_color_field, arrow_colormap=arrow_colormap, arrow_color_label=arrow_color_label, arrow_color_unit=arrow_color_unit))

    def add_axis(self, name, axis_type, title=None, x_grid=True, y_grid=True, z_grid=True, x_label=None, y_label=None, z_label=None, x_unit=None, y_unit=None, z_unit=None, time_autoscale=False):
        """
        Add an axis to DIVE.

        Parameters
        ----------
        name : str
            The name to use for this axis.
        axis_type : str
            The type of view this axis provides.
            Allowed values are: "2d", "3d"
        title : None, str (Default: None)
            The title to show above this axis.
        x_grid : bool (Default: True)
            Toggle whether the x-axis grid lines are displayed.
        y_grid : bool (Default: True)
            Toggle whether the y-axis grid lines are displayed.
        z_grid : bool (Default: True)
            Toggle whether the z-axis grid lines are displayed.
        x_label : None, str (Default: None)
            The label to show for the x-axis.
        y_label : None, str (Default: None)
            The label to show for the y-axis.
        z_label : None, str (Default: None)
            The label to show for the z-axis.
        x_unit : None, array (Default: None)
            The unit to use for the x-axis.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
        y_unit : None, str (Default: None)
            The unit to use for the y-axis.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
        z_unit : None, str (Default: None)
            The unit to use for the z-axis.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
        time_autoscale : bool (Default: False)
            Toggle whether the axis limits should be scaled to fit the current
            data values when the current time value is updated in DIVE.

        Notes
        -----
        If the "pint" module hasn't been installed, the unit parameters will be ignored.
        """
        self._dive_manager.add_axis(dict(name=name, axis_type=axis_type, title=title, x_grid=x_grid, y_grid=y_grid, z_grid=z_grid, x_label=x_label, y_label=y_label, z_label=z_label, x_unit=x_unit, y_unit=y_unit, z_unit=z_unit, time_autoscale=time_autoscale))

    def add_axis_group(self, name, row_count, column_count, axis_names, rows, columns, row_spans, column_spans):
        """
        Add an axis group to DIVE.

        Parameters
        ----------
        name : str
            The name to use for this axis group.
        row_count : int
            The number of rows that this axis group should have.
        column_count : int
            The number of columns that this axis group should have.
        axis_names : array
            The names of the axes that this axis group should display.
        rows : array
            The row indices for the axes specified by "axis_names".
        columns : array
            The column indices for the axes specified by "axis_names".
        row_spans : array
            The number of rows that the axes specified by "axis_names" should span.
        column_spans : array
            The number of columns that the axes specified by "axis_names" should span.
        """
        self._dive_manager.add_axis_group(dict(name=name, row_count=row_count, column_count=column_count, axis_names=axis_names, rows=rows, columns=columns, row_spans=row_spans, column_spans=column_spans))

    def add_box_artist(self, axis_name, name, data_name=None, visible=True, draw_order=0, legend_text=None, x_pos=0, x_pos_field=None, y_pos=0, y_pos_field=None, z_pos=0, z_pos_field=None, width=1, width_field=None, height=1, height_field=None, depth=1, depth_field=None, color='g', color_field=None, colormap='viridis', color_label=None, color_unit=None, faces='XxYyZz'):
        """
        Add a box artist to an axis in DIVE.

        Parameters
        ----------
        axis_name : str
            The name of the axis that this artist should be added to.
        name : str
            The name of this artist.
        data_name : None, str (Default: None)
            The name of the data object to use for this artist.
        visible : bool (Default: True)
            Toggle whether this artist is visible.
        draw_order : numeric (Default: 0)
            The number used to determine the draw order for this artist.
            Artists with small "draw_order" values are drawn before artists with large "draw_order" values.
        legend_text : None, str (Default: None)
            The label to display in the legend for this artist.
            If None, this artist will not appear in the legend.
        x_pos : numeric (Default: 0)
            The position of the box center along the x-axis.
        x_pos_field : None, str (Default: None)
            The name of the field in the data object that contains the positions of the box center along the x-axis.
        y_pos : numeric (Default: 0)
            The position of the box center along the y-axis.
        y_pos_field : None, str (Default: None)
            The name of the field in the data object that contains the positions of the box center along the y-axis.
        z_pos : numeric (Default: 0)
            The position of the box center along the z-axis.
        z_pos_field : None, str (Default: None)
            The name of the field in the data object that contains the positions of the box center along the z-axis.
        width : numeric (Default: 1)
            The width of the box.
        width_field : None, str (Default: None)
            The name of the field in the data object that contains width values of the box.
        height : numeric (Default: 1)
            The height of the box.
        height_field : None, str (Default: None)
            The name of the field in the data object that contains height values of the box.
        depth : numeric (Default: 1)
            The depth of the box.
        depth_field : None, str (Default: None)
            The name of the field in the data object that contains depth values of the box.
        color : str (Default: "g")
            The color to use for the box.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "color_field" is None.
        color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the box.
        colormap: str (Default: "viridis")
            The name of the colormap to use for the box.
            Only used if "color_field" is not None.
        color_label: None, str (Default: None)
            The label to use for box color values on the colorbar.
            Only used if "color_field" is not None.
        color_unit: None, array (Default: None)
            The unit to use for box color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "color_field" is not None.
        faces : str (Default: 'XxYyZz')
            The faces of the box to display. Accepts lowercase and uppercase combinations of 'x', 'y', and 'z'.
            Lowercase indicates negative side and uppercase indicates positive side.

        Notes
        -----
        When multiple color fields are in use in an axis (either in a single artist or across multiple artists),
        all color fields that have the same colormap, color_label, and color_unit will share the same colorbar.

        All colorbar values that aren't numeric or timestamps (with tz),
        will instead be displayed in the legend (as long as "legend_text" is not None).

        It is possible to cycle through the colorbars in an axis by clicking on the colorbar.
        """
        self._dive_manager.add_artist(axis_name, 'box', dict(name=name, data_name=data_name, visible=visible, draw_order=draw_order, legend_text=legend_text, x_pos=x_pos, x_pos_field=x_pos_field, y_pos=y_pos, y_pos_field=y_pos_field, z_pos=z_pos, z_pos_field=z_pos_field, width=width, width_field=width_field, height=height, height_field=height_field, depth=depth, depth_field=depth_field, color=color, color_field=color_field, colormap=colormap, color_label=color_label, color_unit=color_unit, faces=faces))

    def add_data(self, name, data, id_field=None, time_field=None, selection=None):
        """
        Add a data object to DIVE.

        Parameters
        ----------
        name : str
            The name to use for this data object.
        data : pandas.DataFrame
            The data to store in this data object.
            All column names must be strings.
        id_field : None, str (Default: None)
            The name of the field in "data" that contains the ID for each row.
        time_field : None, str (Default: None)
            The name of the field in "data" that contains the timestamp for each row.
            There are two valid types of time values in DIVE: numeric (not complex) and pandas.Timestamp with tz.
            The timestamps must be monotonic increasing.
        selection : None, array (Default: None)
            The indices in "data" that should be selected.

        Notes
        -----
        If the time value data type is not consistent across all data objects (excluding None),
        then the animation controls will not be available in DIVE.
        """
        self._dive_manager.add_data(dict(name=name, data=data, id_field=id_field, time_field=time_field, selection=selection))

    def add_ellipse_artist(self, axis_name, name, data_name=None, visible=True, draw_order=0, legend_text=None, start_angle=0, start_angle_field=None, span_angle=360, span_angle_field=None, x_pos=0, x_pos_field=None, y_pos=0, y_pos_field=None, edge_width=0, edge_width_field=None, x_radius=0.5, x_radius_field=None, y_radius=0.5, y_radius_field=None, color='g', color_field=None, colormap='viridis', color_label=None, color_unit=None, edge_color='g', edge_color_field=None, edge_colormap='viridis', edge_color_label=None, edge_color_unit=None):
        """
        Add an ellipse artist to an axis in DIVE.

        Parameters
        ----------
        axis_name : str
            The name of the axis that this artist should be added to.
        name : str
            The name of this artist.
        data_name : None, str (Default: None)
            The name of the data object to use for this artist.
        visible : bool (Default: True)
            Toggle whether this artist is visible.
        draw_order : numeric (Default: 0)
            The number used to determine the draw order for this artist.
            Artists with small "draw_order" values are drawn before artists with large "draw_order" values.
        legend_text : None, str (Default: None)
            The label to display in the legend for this artist.
            If None, this artist will not appear in the legend.
        start_angle : numeric (Default: 0)
            The counter clockwise starting angle of the ellipse in degrees.
        start_angle_field : None, str (Default: None)
            The name of the field in the data object that contains counter clockwise starting angles of the ellipse in degrees.
        span_angle : numeric (Default: 360)
            The angular region of the ellipse to display in degrees.
        span_angle_field : None, str (Default: None)
            The name of the field in the data object that contains angular regions of the ellipse to display in degrees.
        x_pos : numeric (Default: 0)
            The position of the ellipse center along the x-axis.
        x_pos_field : None, str (Default: None)
            The name of the field in the data object that contains the positions of the ellipse center along the x-axis.
        y_pos : numeric (Default: 0)
            The position of the ellipse center along the y-axis.
        y_pos_field : None, str (Default: None)
            The name of the field in the data object that contains the positions of the ellipse center along the y-axis.
        edge_width : numeric (Default: 0)
            The width of the ellipse edges.
            If 0, the ellipse edges are not shown.
        edge_width_field : None, str (Default: None)
            The name of the field in the data object that contains width values of the ellipse edges.
        x_radius : numeric (Default: 1)
            The radius of the ellipse along the x-axis.
        x_radius_field : None, str (Default: None)
            The name of the field in the data object that contains radius values of the ellipse along the x-axis.
        y_radius : numeric (Default: 1)
            The radius of the ellipse along the y-axis.
        y_radius_field : None, str (Default: None)
            The name of the field in the data object that contains radius values of the ellipse along the y-axis.
        color : str (Default: "g")
            The color to use for the ellipse.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "color_field" is None.
        color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the ellipse.
        colormap: str (Default: "viridis")
            The name of the colormap to use for the ellipse.
            Only used if "color_field" is not None.
        color_label: None, str (Default: None)
            The label to use for ellipse color values on the colorbar.
            Only used if "color_field" is not None.
        color_unit: None, array (Default: None)
            The unit to use for ellipse color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "color_field" is not None.
        edge_color : str (Default: "g")
            The color to use for the ellipse edges.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "edge_color_field" is None.
        edge_color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the ellipse edges.
        edge_colormap: str (Default: "viridis")
            The name of the colormap to use for the ellipse edges.
            Only used if "edge_color_field" is not None.
        edge_color_label: None, str (Default: None)
            The label to use for ellipse edge color values on the colorbar.
            Only used if "edge_color_field" is not None.
        edge_color_unit: None, array (Default: None)
            The unit to use for ellipse edge color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "edge_color_field" is not None.

        Notes
        -----
        When multiple color fields are in use in an axis (either in a single artist or across multiple artists),
        all color fields that have the same colormap, color_label, and color_unit will share the same colorbar.

        All colorbar values that aren't numeric or timestamps (with tz),
        will instead be displayed in the legend (as long as "legend_text" is not None).

        It is possible to cycle through the colorbars in an axis by clicking on the colorbar.
        """
        self._dive_manager.add_artist(axis_name, 'ellipse', dict(name=name, data_name=data_name, visible=visible, draw_order=draw_order, legend_text=legend_text, start_angle=start_angle, start_angle_field=start_angle_field, span_angle=span_angle, span_angle_field=span_angle_field, x_pos=x_pos, x_pos_field=x_pos_field, y_pos=y_pos, y_pos_field=y_pos_field, edge_width=edge_width, edge_width_field=edge_width_field, x_radius=x_radius, x_radius_field=x_radius_field, y_radius=y_radius, y_radius_field=y_radius_field, color=color, color_field=color_field, colormap=colormap, color_label=color_label, color_unit=color_unit, edge_color=edge_color, edge_color_field=edge_color_field, edge_colormap=edge_colormap, edge_color_label=edge_color_label, edge_color_unit=edge_color_unit))

    def add_filter_custom(self, name, values, enabled=True):
        """
        Add a custom filter group to DIVE.

        Parameters
        ----------
        name : str
            The name to use for this custom filter group.
        values : dict
            The indices to use in this custom filter group.
            Each dictionary key should be the name of a data object
            and each dictionary value should be an array of boolean values.
        enabled : bool (Default: True)
            Toggle usage of this custom filter group.
        """
        self._dive_manager.add_filter('custom', dict(name=name, values=values, enabled=enabled))

    def add_filter_id(self, name, values, enabled=True):
        """
        Add an ID filter group to DIVE.

        Parameters
        ----------
        name : str
            The name of to use for this ID filter group.
        values : dict
            The indices to use in this ID filter group.
            Each dictionary key should be the name of a data object
            and each dictionary value should be an array of ID values.
        enabled : bool (Default: True)
            Toggle usage of this ID filter group.
        """
        self._dive_manager.add_filter('ID', dict(name=name, values=values, enabled=enabled))

    def add_filter_value(self, name, data_names, filters=['AND'], id_filter=None, enabled=True):
        """
        Add a value filter group to DIVE.

        Parameters
        ----------
        name : str
            The name to use for this value filter group.
        data_names : array
            The names of the data objects to apply this value filter group to.
        filters : array (Default: ["AND"])
            The filters to apply to each data object specified by "data_names".
            Filtering involves two kinds of items: filter items and logical items.
            Filter items are an array with the format: [comparison_op, data_name, field_name, comparison_value]
            Allowed values for the comparison_op are: ">", ">=", "==", "!=", "<=", "<"
            Logical items are an array with the format: [logical_op, ...]
            Allowed values for the logical_op are: "AND", "OR"
            Both types of items can be added after the logical_op and the logical_op will be applied to the results of all of the subitems.
        id_filter : None, str (Default: None)
            The value specifying whether the output of this value filter group should be used to filter each data's ID field.
            If None, ID filtering will not occur.
            If "any match", a data ID value is kept if at least one occurrence of it is in the value filter groups's output.
            If "all match", a data ID value is kept if all occurrences of it are in the value filter groups's output.
            If "any mismatch", a data ID value is kept if at least one occurrence of it was filtered out.
            If "all mismatch", a data ID value is kept if all occurrences of it were filtered out.
        enabled : bool (Default: True)
            Toggle usage of this value filter group.
        """
        self._dive_manager.add_filter('value', dict(name=name, data_names=data_names, filters=filters, id_filter=id_filter, enabled=enabled))

    def add_image_artist(self, axis_name, name, data_name, color_field, visible=True, draw_order=0, legend_text=None, x_pos=0, x_pos_field=None, y_pos=0, y_pos_field=None, width=1, width_field=None, height=1, height_field=None, colormap='viridis', color_label=None, color_unit=None, interpolation='Nearest'):
        """
        Add an image artist to an axis in DIVE.

        Parameters
        ----------
        axis_name : str
            The name of the axis that this artist should be added to.
        name : str
            The name of this artist.
        data_name : str
            The name of the data object to use for this artist.
        color_field: str
            The name of the field in the data object that contains color values for the image.
            Every value in this field must be a 2D numpy.ndarray.
        visible : bool (Default: True)
            Toggle whether this artist is visible.
        draw_order : numeric (Default: 0)
            The number used to determine the draw order for this artist.
            Artists with small "draw_order" values are drawn before artists with large "draw_order" values.
        legend_text : None, str (Default: None)
            The label to display in the legend for this artist.
            If None, this artist will not appear in the legend.
        x_pos : numeric (Default: 0)
            The position of the image center along the x-axis.
        x_pos_field : None, str (Default: None)
            The name of the field in the data object that contains the positions of the image center along the x-axis.
        y_pos : numeric (Default: 0)
            The position of the image center along the y-axis.
        y_pos_field : None, str (Default: None)
            The name of the field in the data object that contains the positions of the image center along the y-axis.
        width : numeric (Default: 1)
            The width of the image.
        width_field : None, str (Default: None)
            The name of the field in the data object that contains width values of the image.
        height : numeric (Default: 1)
            The height of the image.
        height_field : None, str (Default: None)
            The name of the field in the data object that contains height values of the image.
        colormap: str (Default: "viridis")
            The name of the colormap to use for the image.
            Only used if "color_field" is not None.
        color_label: None, str (Default: None)
            The label to use for image color values on the colorbar.
            Only used if "color_field" is not None.
        color_unit: None, array (Default: None)
            The unit to use for image color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "color_field" is not None.
        interpolation : str (Default: "Nearest")
            The interpolation method to use for the image.
            Allowed values are: 'Bessel', 'Bicubic', 'Bilinear', 'Blackman', 'CatRom', 'Gaussian', 'Hamming', 'Hanning', 'Hermite', 'Kaiser', 'Lanczos', 'Mitchell', 'Nearest', 'Quadric', 'Sinc', 'Spline16', 'Spline36'

        Notes
        -----
        When multiple color fields are in use in an axis (either in a single artist or across multiple artists),
        all color fields that have the same colormap, color_label, and color_unit will share the same colorbar.

        All colorbar values that aren't numeric or timestamps (with tz),
        will instead be displayed in the legend (as long as "legend_text" is not None).

        It is possible to cycle through the colorbars in an axis by clicking on the colorbar.
        """
        self._dive_manager.add_artist(axis_name, 'image', dict(name=name, data_name=data_name, color_field=color_field, visible=visible, draw_order=draw_order, legend_text=legend_text, x_pos=x_pos, x_pos_field=x_pos_field, y_pos=y_pos, y_pos_field=y_pos_field, width=width, width_field=width_field, height=height, height_field=height_field, colormap=colormap, color_label=color_label, color_unit=color_unit, interpolation=interpolation))

    def add_infinite_line_artist(self, axis_name, name, data_name=None, visible=True, draw_order=0, legend_text=None, pos=0, pos_field=None, color='r', color_field=None, colormap='viridis', color_label=None, color_unit=None, is_vertical=True):
        """
        Add an infinite line artist to an axis in DIVE.

        Parameters
        ----------
        axis_name : str
            The name of the axis that this artist should be added to.
        name : str
            The name of this artist.
        data_name : None, str (Default: None)
            The name of the data object to use for this artist.
        visible : bool (Default: True)
            Toggle whether this artist is visible.
        draw_order : numeric (Default: 0)
            The number used to determine the draw order for this artist.
            Artists with small "draw_order" values are drawn before artists with large "draw_order" values.
        legend_text : None, str (Default: None)
            The label to display in the legend for this artist.
            If None, this artist will not appear in the legend.
        pos : numeric (Default: 0)
            The position of the line along the x/y-axis.
        pos_field : None, str (Default: None)
            The name of the field in the data object that contains the positions of the line along the x/y-axis.
        color : str (Default: "r")
            The color to use for the line.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "color_field" is None.
        color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the line.
        colormap: str (Default: "viridis")
            The name of the colormap to use for the line.
            Only used if "color_field" is not None.
        color_label: None, str (Default: None)
            The label to use for line color values on the colorbar.
            Only used if "color_field" is not None.
        color_unit: None, array (Default: None)
            The unit to use for line color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "color_field" is not None.
        is_vertical : bool (Default: True)
            Toggle whether the line is vertical (on the x-axis).

        Notes
        -----
        When multiple color fields are in use in an axis (either in a single artist or across multiple artists),
        all color fields that have the same colormap, color_label, and color_unit will share the same colorbar.

        All colorbar values that aren't numeric or timestamps (with tz),
        will instead be displayed in the legend (as long as "legend_text" is not None).

        It is possible to cycle through the colorbars in an axis by clicking on the colorbar.
        """
        self._dive_manager.add_artist(axis_name, 'infinite line', dict(name=name, data_name=data_name, visible=visible, draw_order=draw_order, legend_text=legend_text, pos=pos, pos_field=pos_field, color=color, color_field=color_field, colormap=colormap, color_label=color_label, color_unit=color_unit, is_vertical=is_vertical))

    def add_polygon_artist(self, axis_name, name, data_name, x_field, y_field, visible=True, draw_order=0, legend_text=None, edge_width=0, edge_width_field=None, color='g', color_field=None, colormap='viridis', color_label=None, color_unit=None, edge_color='g', edge_color_field=None, edge_colormap='viridis', edge_color_label=None, edge_color_unit=None):
        """
        Add a polygon artist to an axis in DIVE.

        Parameters
        ----------
        axis_name : str
            The name of the axis that this artist should be added to.
        name : str
            The name of this artist.
        data_name : str
            The name of the data object to use for this artist.
        x_field : str
            The name of the field in the data object that contains the x coordinates for this artist.
            Every value in this field must be a 1D numpy.ndarray.
        y_field : str
            The name of the field in the data object that contains the y coordinates for this artist.
            Every value in this field must be a 1D numpy.ndarray.
        visible : bool (Default: True)
            Toggle whether this artist is visible.
        draw_order : numeric (Default: 0)
            The number used to determine the draw order for this artist.
            Artists with small "draw_order" values are drawn before artists with large "draw_order" values.
        legend_text : None, str (Default: None)
            The label to display in the legend for this artist.
            If None, this artist will not appear in the legend.
        edge_width : numeric (Default: 0)
            The width of the polygon edges.
            If 0, the polygon edges are not shown.
        edge_width_field : None, str (Default: None)
            The name of the field in the data object that contains width values of the polygon edges.
        color : str (Default: "g")
            The color to use for the polygon.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "color_field" is None.
        color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the polygon.
        colormap: str (Default: "viridis")
            The name of the colormap to use for the polygon.
            Only used if "color_field" is not None.
        color_label: None, str (Default: None)
            The label to use for polygon color values on the colorbar.
            Only used if "color_field" is not None.
        color_unit: None, array (Default: None)
            The unit to use for polygon color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "color_field" is not None.
        edge_color : str (Default: "g")
            The color to use for the polygon edges.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "edge_color_field" is None.
        edge_color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the polygon edges.
        edge_colormap: str (Default: "viridis")
            The name of the colormap to use for the polygon edges.
            Only used if "edge_color_field" is not None.
        edge_color_label: None, str (Default: None)
            The label to use for polygon edge color values on the colorbar.
            Only used if "edge_color_field" is not None.
        edge_color_unit: None, array (Default: None)
            The unit to use for polygon edge color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "edge_color_field" is not None.

        Notes
        -----
        When multiple color fields are in use in an axis (either in a single artist or across multiple artists),
        all color fields that have the same colormap, color_label, and color_unit will share the same colorbar.

        All colorbar values that aren't numeric or timestamps (with tz),
        will instead be displayed in the legend (as long as "legend_text" is not None).

        It is possible to cycle through the colorbars in an axis by clicking on the colorbar.
        """
        self._dive_manager.add_artist(axis_name, 'polygon', dict(name=name, data_name=data_name, x_field=x_field, y_field=y_field, visible=visible, draw_order=draw_order, legend_text=legend_text, edge_width=edge_width, edge_width_field=edge_width_field, color=color, color_field=color_field, colormap=colormap, color_label=color_label, color_unit=color_unit, edge_color=edge_color, edge_color_field=edge_color_field, edge_colormap=edge_colormap, edge_color_label=edge_color_label, edge_color_unit=edge_color_unit))

    def add_rectangle_artist(self, axis_name, name, data_name=None, visible=True, draw_order=0, legend_text=None, x_pos=0, x_pos_field=None, y_pos=0, y_pos_field=None, edge_width=0, edge_width_field=None, width=1, width_field=None, height=1, height_field=None, color='g', color_field=None, colormap='viridis', color_label=None, color_unit=None, edge_color='g', edge_color_field=None, edge_colormap='viridis', edge_color_label=None, edge_color_unit=None):
        """
        Add a rectangle artist to an axis in DIVE.

        Parameters
        ----------
        axis_name : str
            The name of the axis that this artist should be added to.
        name : str
            The name of this artist.
        data_name : None, str (Default: None)
            The name of the data object to use for this artist.
        visible : bool (Default: True)
            Toggle whether this artist is visible.
        draw_order : numeric (Default: 0)
            The number used to determine the draw order for this artist.
            Artists with small "draw_order" values are drawn before artists with large "draw_order" values.
        legend_text : None, str (Default: None)
            The label to display in the legend for this artist.
            If None, this artist will not appear in the legend.
        x_pos : numeric (Default: 0)
            The position of the rectangle center along the x-axis.
        x_pos_field : None, str (Default: None)
            The name of the field in the data object that contains the positions of the rectangle center along the x-axis.
        y_pos : numeric (Default: 0)
            The position of the rectangle center along the y-axis.
        y_pos_field : None, str (Default: None)
            The name of the field in the data object that contains the positions of the rectangle center along the y-axis.
        edge_width : numeric (Default: 0)
            The width of the rectangle edges.
            If 0, the rectangle edges are not shown.
        edge_width_field : None, str (Default: None)
            The name of the field in the data object that contains width values of the rectangle edges.
        width : numeric (Default: 1)
            The width of the rectangle.
        width_field : None, str (Default: None)
            The name of the field in the data object that contains width values of the rectangle.
        height : numeric (Default: 1)
            The height of the rectangle.
        height_field : None, str (Default: None)
            The name of the field in the data object that contains height values of the rectangle.
        color : str (Default: "g")
            The color to use for the rectangle.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "color_field" is None.
        color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the rectangle.
        colormap: str (Default: "viridis")
            The name of the colormap to use for the rectangle.
            Only used if "color_field" is not None.
        color_label: None, str (Default: None)
            The label to use for rectangle color values on the colorbar.
            Only used if "color_field" is not None.
        color_unit: None, array (Default: None)
            The unit to use for rectangle color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "color_field" is not None.
        edge_color : str (Default: "g")
            The color to use for the rectangle edges.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "edge_color_field" is None.
        edge_color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the rectangle edges.
        edge_colormap: str (Default: "viridis")
            The name of the colormap to use for the rectangle edges.
            Only used if "edge_color_field" is not None.
        edge_color_label: None, str (Default: None)
            The label to use for rectangle edge color values on the colorbar.
            Only used if "edge_color_field" is not None.
        edge_color_unit: None, array (Default: None)
            The unit to use for rectangle edge color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "edge_color_field" is not None.

        Notes
        -----
        When multiple color fields are in use in an axis (either in a single artist or across multiple artists),
        all color fields that have the same colormap, color_label, and color_unit will share the same colorbar.

        All colorbar values that aren't numeric or timestamps (with tz),
        will instead be displayed in the legend (as long as "legend_text" is not None).

        It is possible to cycle through the colorbars in an axis by clicking on the colorbar.
        """
        self._dive_manager.add_artist(axis_name, 'rectangle', dict(name=name, data_name=data_name, visible=visible, draw_order=draw_order, legend_text=legend_text, x_pos=x_pos, x_pos_field=x_pos_field, y_pos=y_pos, y_pos_field=y_pos_field, edge_width=edge_width, edge_width_field=edge_width_field, width=width, width_field=width_field, height=height, height_field=height_field, color=color, color_field=color_field, colormap=colormap, color_label=color_label, color_unit=color_unit, edge_color=edge_color, edge_color_field=edge_color_field, edge_colormap=edge_colormap, edge_color_label=edge_color_label, edge_color_unit=edge_color_unit))

    def add_scatter_artist(self, axis_name, name, data_name, x_field, y_field, z_field=None, label_field=None, label_size=10, visible=True, draw_order=0, legend_text=None, selectable=True,
                           line_width=1, line_color='r', line_color_field=None, line_colormap='viridis', line_color_label=None, line_color_unit=None,
                           marker='o', marker_size=10, marker_color='g', marker_color_field=None, marker_colormap='viridis', marker_color_label=None, marker_color_unit=None,
                           edge_width=0, edge_color='g', edge_color_field=None, edge_colormap='viridis', edge_color_label=None, edge_color_unit=None):
        """
        Add a scatter artist to an axis in DIVE.

        Parameters
        ----------
        axis_name : str
            The name of the axis that this artist should be added to.
        name : str
            The name of this artist.
        data_name : str
            The name of the data object to use for this artist.
        x_field : str
            The name of the field in the data object that contains the x coordinates for this artist.
        y_field : str
            The name of the field in the data object that contains the y coordinates for this artist.
        z_field : None, str (Default: None)
            The name of the field in the data object that contains the z coordinates for this artist.
            If None, this artist will be two-dimensional.
        label_field : None, str (Default: None)
            The name of the field in the data object that contains labels for each data point.
            If None, labels will not be shown.
        label_size : numeric (Default: 10)
            The font size to use for labels.
        visible : bool (Default: True)
            Toggle whether this artist is visible.
        draw_order : numeric (Default: 0)
            The number used to determine the draw order for this artist.
            Artists with small "draw_order" values are drawn before artists with large "draw_order" values.
        legend_text : None, str (Default: None)
            The label to display in the legend for this artist.
            If None, this artist will not appear in the legend.
        selectable : bool (Default: True)
            Toggle whether this artist is selectable.
        line_width : numeric (Default: 1)
            The width of the lines.
            If 0, lines are not shown.
        line_color : str (Default: "r")
            The color to use for the lines.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "line_color_field" is None.
        line_color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the lines.
        line_colormap: str (Default: "viridis")
            The name of the colormap to use for the lines.
            Only used if "line_color_field" is not None.
        line_color_label: None, str (Default: None)
            The label to use for line color values on the colorbar.
            Only used if "line_color_field" is not None.
        line_color_unit: None, array (Default: None)
            The unit to use for line color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "line_color_field" is not None.
        marker: str (Default: "o")
            The shape to use for the markers.
        marker_size: numeric (Default: 10)
            The size of the markers.
            If 0, markers are not shown.
        marker_color : str (Default: "g")
            The color to use for the markers.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "marker_color_field" is None.
        marker_color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the markers.
        marker_colormap: str (Default: "viridis")
            The name of the colormap to use for the markers.
            Only used if "marker_color_field" is not None.
        marker_color_label: None, str (Default: None)
            The label to use for marker color values on the colorbar.
            Only used if "marker_color_field" is not None.
        marker_color_unit: None, array (Default: None)
            The unit to use for marker color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "marker_color_field" is not None.
        edge_width : numeric (Default: 1)
            The width of the marker edges.
            If 0, marker edges are not shown.
        edge_color : str (Default: "r")
            The color to use for the marker edges.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "edge_color_field" is None.
        edge_color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the marker edges.
        edge_colormap: str (Default: "viridis")
            The name of the colormap to use for the marker edges.
            Only used if "edge_color_field" is not None.
        edge_color_label: None, str (Default: None)
            The label to use for marker edge color values on the colorbar.
            Only used if "edge_color_field" is not None.
        edge_color_unit: None, array (Default: None)
            The unit to use for marker edge color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "edge_color_field" is not None.

        Notes
        -----
        If the data object has an ID field, lines will only connect points with the same ID.

        When multiple color fields are in use in an axis (either in a single artist or across multiple artists),
        all color fields that have the same colormap, color_label, and color_unit will share the same colorbar.

        All colorbar values that aren't numeric or timestamps (with tz),
        will instead be displayed in the legend (as long as "legend_text" is not None).

        It is possible to cycle through the colorbars in an axis by clicking on the colorbar.
        """
        self._dive_manager.add_artist(axis_name, 'scatter', dict(name=name, data_name=data_name, x_field=x_field, y_field=y_field, z_field=z_field, label_field=label_field, label_size=label_size, visible=visible, draw_order=draw_order, legend_text=legend_text, selectable=selectable,
                                                                 line_width=line_width, line_color=line_color, line_color_field=line_color_field, line_colormap=line_colormap, line_color_label=line_color_label, line_color_unit=line_color_unit,
                                                                 marker=marker, marker_size=marker_size, marker_color=marker_color, marker_color_field=marker_color_field, marker_colormap=marker_colormap, marker_color_label=marker_color_label, marker_color_unit=marker_color_unit,
                                                                 edge_width=edge_width, edge_color=edge_color, edge_color_field=edge_color_field, edge_colormap=edge_colormap, edge_color_label=edge_color_label, edge_color_unit=edge_color_unit))

    def add_surface_artist(self, axis_name, name, data_name, x_field, y_field, z_field, visible=True, draw_order=0, legend_text=None, color='g', color_field=None, colormap='viridis', color_label=None, color_unit=None):
        """
        Add a surface artist to an axis in DIVE.

        Parameters
        ----------
        axis_name : str
            The name of the axis that this artist should be added to.
        name : str
            The name of this artist.
        data_name : str
            The name of the data object to use for this artist.
        x_field : str
            The name of the field in the data object that contains the x coordinates for this artist.
            Every value in this field must be a 1D numpy.ndarray.
        y_field : str
            The name of the field in the data object that contains the y coordinates for this artist.
            Every value in this field must be a 1D numpy.ndarray.
        z_field : str
            The name of the field in the data object that contains the z coordinates for this artist.
            Every value in this field must be a 2D numpy.ndarray.
        visible : bool (Default: True)
            Toggle whether this artist is visible.
        draw_order : numeric (Default: 0)
            The number used to determine the draw order for this artist.
            Artists with small "draw_order" values are drawn before artists with large "draw_order" values.
        legend_text : None, str (Default: None)
            The label to display in the legend for this artist.
            If None, this artist will not appear in the legend.
        color : str (Default: "g")
            The color to use for the surface.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "color_field" is None.
        color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the surface.
        colormap: str (Default: "viridis")
            The name of the colormap to use for the surface.
            Only used if "color_field" is not None.
        color_label: None, str (Default: None)
            The label to use for surface color values on the colorbar.
            Only used if "color_field" is not None.
        color_unit: None, array (Default: None)
            The unit to use for surface color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "color_field" is not None.

        Notes
        -----
        When multiple color fields are in use in an axis (either in a single artist or across multiple artists),
        all color fields that have the same colormap, color_label, and color_unit will share the same colorbar.

        All colorbar values that aren't numeric or timestamps (with tz),
        will instead be displayed in the legend (as long as "legend_text" is not None).

        It is possible to cycle through the colorbars in an axis by clicking on the colorbar.
        """
        self._dive_manager.add_artist(axis_name, 'surface', dict(name=name, data_name=data_name, x_field=x_field, y_field=y_field, z_field=z_field, visible=visible, draw_order=draw_order, legend_text=legend_text, color=color, color_field=color_field, colormap=colormap, color_label=color_label, color_unit=color_unit))

    def add_table_row(self, data_name, field_name, label, operation, color_criteria=[], blend_colors=False, index=None):
        """
        Add a table row to DIVE.

        Parameters
        ----------
        data_name : str
            The name of the data object to use for this row.
        field_name : str
            The name of the field in the data object to use for this row.
        label : str
            The label to use for this row.
        operation : str
            The operation to perform on the data field.
            There are two kinds of operations: "latest" and any pandas function that can be applied to a pandas.Series (sum, mean, min, max, ...).
            If "latest", the most recent value in the data field will be shown. If there aren't any time values in the data object,
            the last value in the data field will be shown.
        color_criteria : array (Default: [])
            The criteria to use for setting the row color.
            Each element of the array should be an array with the format: [comparison_op, comparison_value, color_str]
            The comparison_op specifies how the row's value should be compared to the comparison_value.
            Allowed values for the comparison_op are: ">", ">=", "==", "!=", "<=", "<", "change"
            If comparison_op is "change", the color_str will be applied every time the row value changes and the comparision_value will be ignored.
            The comparison_op can only be "change" when the data object has a time field and "operation" is "latest".
        blend_colors : bool (Default: False)
            Toggle blending of row colors if multiple color criteria are True at the same time.
        index : None, int (Default: None)
            The index in the table to insert this row.
            If None, this row will be appended to the table.
        """
        self._dive_manager.add_table_row(dict(data_name=data_name, field_name=field_name, label=label, operation=operation, color_criteria=color_criteria, blend_colors=blend_colors, index=index))

    def add_text_artist(self, axis_name, name, data_name, text_field, x_field, y_field, z_field=None, visible=True, draw_order=0, legend_text=None, x_anchor='center', y_anchor='center', font_size=12, bold=False, italic=False, color='black', color_field=None, colormap='viridis', color_label=None, color_unit=None):
        """
        Add a text artist to an axis in DIVE.

        Parameters
        ----------
        axis_name : str
            The name of the axis that this artist should be added to.
        name : str
            The name of this artist.
        data_name : str
            The name of the data object to use for this artist.
        text_field : str
            The name of the field in the data object that contains the text values for this artist.
        x_field : str
            The name of the field in the data object that contains the x coordinates for this artist.
        y_field : str
            The name of the field in the data object that contains the y coordinates for this artist.
        z_field : None, str (Default: None)
            The name of the field in the data object that contains the z coordinates for this artist.
            If None, this artist will be two-dimensional.
        visible : bool (Default: True)
            Toggle whether this artist is visible.
        draw_order : numeric (Default: 0)
            The number used to determine the draw order for this artist.
            Artists with small "draw_order" values are drawn before artists with large "draw_order" values.
        legend_text : None, str (Default: None)
            The label to display in the legend for this artist.
            If None, this artist will not appear in the legend.
        x_anchor : str (Default: "center")
            The horizontal anchor for the text.
            Allowed values are: "left", "center", "right"
        y_anchor : str (Default: "center")
            The vertical anchor for the text.
            Allowed values are: "top", "center", "bottom"
        font_size : numeric (Default: 12)
            The font size to use for the text.
        bold : bool (Default: False)
            Toggle whether text is bold.
        italic : bool (Default: False)
            Toggle whether text is italicized.
        color : str (Default: "black")
            The color to use for the text.
            It must be either a hex string (such as "#ff0000") or the name of a CSS color.
            Only used if "color_field" is None.
        color_field: None, str (Default: None)
            The name of the field in the data object that contains color values for the text.
        colormap: str (Default: "viridis")
            The name of the colormap to use for the text.
            Only used if "color_field" is not None.
        color_label: None, str (Default: None)
            The label to use for text color values on the colorbar.
            Only used if "color_field" is not None.
        color_unit: None, array (Default: None)
            The unit to use for text color values on the colorbar.
            If array, it must have the format: [from_unit, to_unit]
            Only "pint" units are valid.
            Only used if "color_field" is not None.

        Notes
        -----
        When multiple color fields are in use in an axis (either in a single artist or across multiple artists),
        all color fields that have the same colormap, color_label, and color_unit will share the same colorbar.

        All colorbar values that aren't numeric or timestamps (with tz),
        will instead be displayed in the legend (as long as "legend_text" is not None).

        It is possible to cycle through the colorbars in an axis by clicking on the colorbar.
        """
        self._dive_manager.add_artist(axis_name, 'text', dict(name=name, data_name=data_name, text_field=text_field, x_field=x_field, y_field=y_field, z_field=z_field, visible=visible, draw_order=draw_order, legend_text=legend_text, x_anchor=x_anchor, y_anchor=y_anchor, font_size=font_size, bold=bold, italic=italic, color=color, color_field=color_field, colormap=colormap, color_label=color_label, color_unit=color_unit))

    def axis_limits_autoscale(self, name=None):
        """
        Autoscale the limits of the specified axis/axes in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the axis to autoscale.
            If None, the limits of every axis in DIVE will be autoscaled.
        """
        self._dive_manager.axis_limits_autoscale(name)

    def axis_limits_reset(self, name=None):
        """
        Reset the limits of the specified axis/axes in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the axis to reset.
            If None, the limits of every axis in DIVE will be reset.
        """
        self._dive_manager.axis_limits_reset(name)

    def display_axis(self, name=None):
        """
        Display an axis in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the axis to display.
            If None, no axis will be displayed.
        """
        self._dive_manager.display_axis(name)

    def display_axis_group(self, name=None):
        """
        Display an axis group in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the axis group to display.
            If None, no axis group will be displayed.
        """
        self._dive_manager.display_axis_group(name)

    def edit_artist(self, axis_name, name, **kwargs):
        """
        Edit an artist in DIVE.

        Parameters
        ----------
        axis_name : str
            The name of the axis that has the artist to be edited.
        name : str
            The name of the artist to edit.
        **kwargs
            Any of the parameters accepted by the function used to add the artist (except "name").
        """
        self._dive_manager.edit_artist(axis_name, name, kwargs)

    def edit_axis(self, name, **kwargs):
        """
        Edit an axis in DIVE.

        Parameters
        ----------
        name : str
            The name of the axis to edit.
        **kwargs
            Any of the parameters accepted by add_axis (except "name" and "axis_type").
        """
        self._dive_manager.edit_axis(name, kwargs)

    def edit_axis_group(self, name, **kwargs):
        """
        Edit an axis group in DIVE.

        Parameters
        ----------
        name : str
            The name of the axis group to edit.
        **kwargs
            Any of the parameters accepted by add_axis_group (except "name").
        """
        self._dive_manager.edit_axis_group(name, kwargs)

    def edit_data(self, name, **kwargs):
        """
        Edit a data object in DIVE.

        Parameters
        ----------
        name : str
            The name of the data object to edit.
        **kwargs
            Any of the parameters accepted by add_data (except "name").
        """
        self._dive_manager.edit_data(name, kwargs)

    def edit_filter_custom(self, name, **kwargs):
        """
        Edit a custom filter group in DIVE.

        Parameters
        ----------
        name : str
            The name of the custom filter group to edit.
        **kwargs
            Any of the parameters accepted by add_filter_custom (except "name").
        """
        self._dive_manager.edit_filter('custom', name, kwargs)

    def edit_filter_id(self, name, **kwargs):
        """
        Edit an ID filter group in DIVE.

        Parameters
        ----------
        name : str
            The name of the ID filter group to edit.
        **kwargs
            Any of the parameters accepted by add_filter_id (except "name").
        """
        self._dive_manager.edit_filter('ID', name, kwargs)

    def edit_filter_value(self, name, **kwargs):
        """
        Edit a value filter group in DIVE.

        Parameters
        ----------
        name : str
            The name of the value filter group to edit.
        **kwargs
            Any of the parameters accepted by add_filter_value (except "name").
        """
        self._dive_manager.edit_filter('value', name, kwargs)

    def edit_table_row(self, row_index, **kwargs):
        """
        Edit a table row in DIVE.

        Parameters
        ----------
        row_index : int
            The index of the table row to edit.
        **kwargs
            Any of the parameters accepted by add_table_row.
        """
        self._dive_manager.edit_table_row(row_index, kwargs)

    def get_animation_direction(self):
        """
        Return the direction of the animation in DIVE.

        Returns
        -------
        bool
            Is the animation set to run in reverse.
        """
        return self._dive_manager.get_animation_direction()

    def get_animation_state(self):
        """
        Return the state of the animation in DIVE.

        Returns
        -------
        bool
            Is the animation running.
        """
        return self._dive_manager.get_animation_state()

    def get_artist(self, axis_name=None, name=None):
        """
        Return the parameters of the specified artist(s) in DIVE.

        Parameters
        ----------
        axis_name : None, str (Default: None)
            The name of the axis containing the artist(s).
            If None, a dict containing the parameters of every artist
            in every axis will be returned.
        name : None, str (Default: None)
            The name of the artist to get parameters for.
            If None, a list containing the parameters of every artist
            in the specified axis will be returned.

        Returns
        -------
        None, dict, list
            The parameters of the specified artist(s).
            Will be None if "axis_name" or "name" is invalid.
        """
        return self._dive_manager.get_artist(axis_name, name)

    def get_axis(self, name=None):
        """
        Return the parameters of the specified axis/axes in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the axis to get parameters for.
            If None, a list containing the parameters of every axis
            in DIVE will be returned.

        Returns
        -------
        None, dict, list
            The parameters of the specified axis/axes.
            Will be None if "name" is invalid.
        """
        return self._dive_manager.get_axis(name)

    def get_axis_group(self, name=None):
        """
        Return the parameters of the specified axis group(s) in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the axis group to get parameters for.
            If None, a list containing the parameters of every axis
            group in DIVE will be returned.

        Returns
        -------
        None, dict, list
            The parameters of the specified axis group(s).
            Will be None if "name" is invalid.
        """
        return self._dive_manager.get_axis_group(name)

    def get_current_time(self):
        """
        Return the current time of the animation in DIVE.

        Returns
        -------
        None, numeric, pandas.Timestamp with tz
            The current time.
        """
        return self._dive_manager.get_current_time()

    def get_data(self, name=None):
        """
        Return the parameters of the specified data object(s) in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the data object to get parameters for.
            If None, a list containing the parameters of every data object
            in DIVE will be returned.

        Returns
        -------
        None, dict, list
            The parameters of the specified data object(s).
            Will be None if "name" is invalid.
        """
        return self._dive_manager.get_data(name)

    def get_filter_custom(self, name=None):
        """
        Return the parameters of the specified custom filter group(s) in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the custom filter group to get parameters for.
            If None, a list containing the parameters of every custom filter group
            in DIVE will be returned.

        Returns
        -------
        None, dict, list
            The parameters of the specified custom filter group(s).
            Will be None if "name" is invalid.
        """
        return self._dive_manager.get_filter('custom', name)

    def get_filter_id(self, name=None):
        """
        Return the parameters of the specified ID filter group(s) in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the ID filter group to get parameters for.
            If None, a list containing the parameters of every ID filter group
            in DIVE will be returned.

        Returns
        -------
        None, dict, list
            The parameters of the specified ID filter group(s).
            Will be None if "name" is invalid.
        """
        return self._dive_manager.get_filter('ID', name)

    def get_filter_value(self, name=None):
        """
        Return the parameters of the specified value filter group(s) in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the value filter group to get parameters for.
            If None, a list containing the parameters of every value filter group
            in DIVE will be returned.

        Returns
        -------
        None, dict, list
            The parameters of the specified value filter group(s).
            Will be None if "name" is invalid.
        """
        return self._dive_manager.get_filter('value', name)

    def get_filter_custom_indices(self, name=None):
        """
        Return the indices of the specified custom filter group(s) in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the custom filter group to get indices for.
            If None, a list containing the indices for every custom filter group
            in DIVE will be returned.

        Returns
        -------
        None, dict, list
            The indices of the specified custom filter group(s).
            Will be None if "name" is invalid.
        """
        return self._dive_manager.get_filter_indices('custom', name)

    def get_filter_id_indices(self, name=None):
        """
        Return the indices of the specified ID filter group(s) in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the ID filter group to get indices for.
            If None, a list containing the indices for every ID filter group
            in DIVE will be returned.

        Returns
        -------
        None, dict, list
            The indices of the specified ID filter group(s).
            Will be None if "name" is invalid.
        """
        return self._dive_manager.get_filter_indices('ID', name)

    def get_filter_indices(self):
        """
        Return the combined indices of every enabled filter group in DIVE.

        Returns
        -------
        dict
            The combined indices of every enabled filter group in DIVE.
        """
        return self._dive_manager.get_filter_indices(None, None)

    def get_filter_value_indices(self, name=None):
        """
        Return the indices of the specified value filter group(s) in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the value filter group to get indices for.
            If None, a list containing the indices for every value filter group
            in DIVE will be returned.

        Returns
        -------
        None, dict, list
            The indices of the specified value filter group(s).
            Will be None if "name" is invalid.
        """
        return self._dive_manager.get_filter_indices('value', name)

    def get_interact_mode(self):
        """
        Return the plotting canvas interaction mode in DIVE.

        Returns
        -------
        str
            The plotting canvas interaction mode in DIVE.
        """
        return self._dive_manager.get_interact_mode()

    def get_recording_state(self):
        """
        Return the recording state in DIVE.

        Returns
        -------
        bool
            Is a recording in progress.
        """
        return self._dive_manager.get_recording_state()

    def get_settings(self):
        """
        Return the settings in DIVE.

        Returns
        -------
        dict
            The settings in DIVE.
        """
        return self._dive_manager.get_settings()

    def get_table_row(self, index=None):
        """
        Return the parameters of table rows in DIVE.

        Parameters
        ----------
        index : None, int (Default: None)
            The index of the table row to get parameters for.
            If None, a list containing the parameters of every table row
            in DIVE will be returned.

        Returns
        -------
        None, dict, list
            The parameters of the specified table row(s).
            Will be None if "index" is invalid.
        """
        return self._dive_manager.get_table_row(index)

    def get_time_limits(self):
        """
        Return the time limits of the animation in DIVE.

        Returns
        -------
        None, numeric, pandas.Timestamp with tz
            The minimum time.
        None, numeric, pandas.Timestamp with tz
            The maximum time.
        """
        return self._dive_manager.get_time_limits()

    def record_video(self, file_path, start_time, stop_time, fps=None):
        """
        Record a .mp4 video of the DIVE window for a period of time.

        Parameters
        ----------
        file_path : str
            The path (including the file name) to where the video should be saved.
        start_time : numeric, pandas.Timestamp with tz
            The time value that the recording should start from.
        stop_time : numeric, pandas.Timestamp with tz
            The time value that the recording should stop at.
        fps : None, int (Default: None)
            The number of frames per second that the video should have.
            If None, the fps in DIVE's settings will be used.

        Notes
        -----
        If the "opencv-python" module hasn't been installed, this function won't do anything.
        """
        self._dive_manager.record_video(file_path, start_time, stop_time, fps)

    def remove_artist(self, axis_name=None, name=None):
        """
        Remove an artist in DIVE.

        Parameters
        ----------
        axis_name : None, str (Default: None)
            The name of the axis that has the artist to be removed.
            If None, all artists in all axes will be removed.
        name : None, str (Default: None)
            The name of the artist to remove.
            If None, all artists in the specified axis will be removed.
        """
        self._dive_manager.remove_artist(axis_name, name)

    def remove_axis(self, name=None):
        """
        Remove an axis in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the axis to remove.
            If None, all axes will be removed.
        """
        self._dive_manager.remove_axis(name)

    def remove_axis_group(self, name=None):
        """
        Remove an axis group in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the axis group to remove.
            If None, all axis groups will be removed.
        """
        self._dive_manager.remove_axis_group(name)

    def remove_data(self, name=None):
        """
        Remove a data object in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the data object to remove.
            If None, all data objects will be removed.
        """
        self._dive_manager.remove_data(name)

    def remove_filter_custom(self, name=None):
        """
        Remove a custom filter group in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the custom filter group to remove.
            If None, all custom filter groups will be removed.
        """
        self._dive_manager.remove_filter('custom', name)

    def remove_filter_id(self, name=None):
        """
        Remove an ID filter group in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the ID filter group to remove.
            If None, all ID filter groups will be removed.
        """
        self._dive_manager.remove_filter('ID', name)

    def remove_filter_value(self, name=None):
        """
        Remove a value filter group in DIVE.

        Parameters
        ----------
        name : None, str (Default: None)
            The name of the value filter group to remove.
            If None, all value filter groups will be removed.
        """
        self._dive_manager.remove_filter('value', name)

    def remove_table_row(self, index=None):
        """
        Remove a table row in DIVE.

        Parameters
        ----------
        index : None, int (Default: None)
            The index of the table row to remove.
            If None, all table rows will be removed.
        """
        self._dive_manager.remove_table_row(index)

    def set_animation_direction(self, reverse):
        """
        Set the direction of the animation in DIVE.

        Parameters
        ----------
        reverse : bool
            Toggle whether the animation should run in reverse.
        """
        self._dive_manager.set_animation_direction(reverse)

    def set_animation_state(self, running):
        """
        Set the state of the animation in DIVE.

        Parameters
        ----------
        running : bool
            Toggle whether the animation should be running.
        """
        self._dive_manager.set_animation_state(running)

    def set_current_time(self, time):
        """
        Set the current time of the animation in DIVE.

        Parameters
        ----------
        time : numeric, pandas.Timestamp with tz
            The time value to use.
        """
        self._dive_manager.set_current_time(time)

    def set_interact_mode(self, mode):
        """
        Set the plotting canvas interaction mode in DIVE.

        Parameters
        ----------
        mode : str
            The plotting canvas interaction mode to use.
            Allowed values are: "pan", "zoom", "rectangle", "ellipse", "lasso"
        """
        self._dive_manager.set_interact_mode(mode)

    def set_settings(self, **kwargs):
        """
        Set the settings in DIVE.

        Parameters
        ----------
        **kwargs
            time_step : numeric
                The number of seconds that the animation should increment for each frame of the animation.
            fps : int
                The number of frames per second that the animation should try to run at.
            hold_time : numeric
                The number of seconds of data prior to the current time that should be displayed for all artists.
                If 0, all data up to the current time will be displayed.
            table_change_time : numeric
                The number of seconds that the table should keep a row color changed if it's "color_criteria" is set to "change".
            timezone : str
                The timezone to use for all time values in DIVE.
                Only "pytz" timezones are valid.
            clock_size : numeric
                The font size to use for the clock below the plotting canvas in DIVE.
            marking : str
                The text to use for the marking below the plotting canvas in DIVE.
            marking_color : str
                The text color to use for the marking below the plotting canvas in DIVE.
            marking_size : numeric
                The font size to use for the marking below the plotting canvas in DIVE.
            gui_theme : str
                The theme to use for DIVE's GUI.
                Allowed values are: "default", "light", "dark"
            canvas_theme : str
                The theme to use for the plotting canvas in DIVE.
                Allowed values are: "light", "dark"
            axis_label_size : numeric
                The font size to use for axis labels.
            axis_tick_size : numeric
                The font size to use for axis ticks.
            apply_limits_filter : bool
                Toggle whether limits (axis, colorbar, time) should be calculated using the current filtered data.
            and_filters : bool
                Toggle whether filter groups in DIVE should be merged using AND.
                If False, filter groups will be merged using OR.

        Notes
        -----
        If the "qdarkstyle" module hasn't been installed, "gui_theme" will be ignored.
        """
        self._dive_manager.set_settings(kwargs)

    def take_screenshot(self, file_path):
        """
        Save a .png image of the DIVE window.

        Parameters
        ----------
        file_path : str
            The path (including the file name) to where the image should be saved.
        """
        self._dive_manager.take_screenshot(file_path)

    def toggle_toolbar(self, reset=True, autoscale=True, pan=True, zoom=True, selection=True, display_axis=True, config_axes=True, config_axis_groups=True, config_data=True, config_table_rows=True, filter_data=True, settings=True, inspect_data=True, screenshot=True, record=True):
        """
        Toggle the visibility of the toolbar buttons in DIVE.

        Parameters
        ----------
        reset : bool (Default: True)
            Toggle the visibility of the "Reset Axis Limits" button.
        autoscale : bool (Default: True)
            Toggle the visibility of the "Autoscale Axis Limits" button.
        pan : bool (Default: True)
            Toggle the visibility of the "Pan" button.
        zoom : bool (Default: True)
            Toggle the visibility of the "Zoom" button.
        selection : bool (Default: True)
            Toggle the visibility of the selection button and its menu.
        display_axis : bool (Default: True)
            Toggle the visibility of the "Display Axis" button.
        config_axes : bool (Default: True)
            Toggle the visibility of the "Configure Axes/Artists" menu option.
        config_axis_groups : bool (Default: True)
            Toggle the visibility of the "Configure Axis Groups" menu option.
        config_data : bool (Default: True)
            Toggle the visibility of the "Configure Data Selection" menu option.
        config_table_rows : bool (Default: True)
            Toggle the visibility of the "Configure Table Rows" menu option.
        filter_data : bool (Default: True)
            Toggle the visibility of the "Filter Data" button.
        settings : bool (Default: True)
            Toggle the visibility of the "Settings" button.
        inspect_data : bool (Default: True)
            Toggle the visibility of the "Inspect Data" button.
        screenshot : bool (Default: True)
            Toggle the visibility of the "Take Screenshot" button.
        record : bool (Default: True)
            Toggle the visibility of the "Record Video" button.
        """
        self._dive_manager.toggle_toolbar(dict(reset=reset, autoscale=autoscale, pan=pan, zoom=zoom, selection=selection, display_axis=display_axis, config_axes=config_axes, config_axis_groups=config_axis_groups, config_data=config_data, config_table_rows=config_table_rows, filter_data=filter_data, settings=settings, inspect_data=inspect_data, screenshot=screenshot, record=record))
