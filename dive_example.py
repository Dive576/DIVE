from DIVE import DIVEWidget
from PyQt5.QtWidgets import QApplication
import numpy as np
import pandas as pd

if __name__ == '__main__':
    n_1d = 2000
    n_2d = 60
    np.random.seed(1234)

    # Create a Qt application
    app = QApplication.instance() if QApplication.instance() else QApplication([])
    app.setQuitOnLastWindowClosed(True)

    # Initialize the DIVE GUI
    widget = DIVEWidget()
    widget.set_settings(marking='DIVE Example', marking_color='g', gui_theme='dark')

    # Generate example data
    x = np.linspace(-np.pi, np.pi, n_1d)
    y = np.zeros(n_1d)
    y[::2] = np.sin(x[::2])
    y[1::2] = np.cos(x[1::2])
    type_vals = np.full(n_1d, 'sin')
    type_vals[1::2] = 'cos'
    data_1d = pd.DataFrame({'x': x, 'y': y, 'z': np.arange(n_1d), 'type': type_vals, 'time_tz': pd.date_range('1/1/2020', periods=n_1d, freq='1S', tz='US/Pacific')})
    data_2d = pd.DataFrame({'x': [np.array([1, 2, 2, 1, 0, 0])] * n_2d, 'y': [np.array([2, 1, 0, -1, 0, 1])] * n_2d, 'z': pd.Series([np.random.randint(0, 101, (5, 10)) for i in range(n_2d)]), 'time': pd.date_range('1/1/2020', periods=n_2d, freq='1S', tz='US/Pacific')})
    surface_data = pd.DataFrame({'x': [np.arange(5)], 'y': [np.arange(5)], 'z': [np.random.randint(10, 200, (5, 5))]})

    # Add data objects
    widget.add_data(name='1D', data=data_1d, id_field='type', time_field='time_tz')
    widget.add_data(name='2D', data=data_2d, time_field='time')
    widget.add_data(name='surface', data=surface_data)

    # Add example filters
    widget.add_filter_custom(name='example_custom', values={'1D': np.ones(n_1d, dtype='bool')})
    widget.add_filter_id(name='example_id', values={'1D': ['sin']}, enabled=False)
    widget.add_filter_value(name='example_value', data_names=['1D', '2D'], filters=['AND', ['>=', '1D', 'x', 0], ['OR', ['<=', '1D', 'time_tz', pd.Timestamp('1/1/2020 00:10:00', tz='UTC')], ['==', '1D', 'type', 'cos']]], enabled=False)

    # Add axes and an axis group
    widget.add_axis(name='X vs Y', axis_type='2d', title='2D Axis Example', x_label='X-Axis', y_label='Y-Axis')
    widget.add_axis(name='X vs Y vs Z', axis_type='3d', title='3D Axis Example')
    widget.add_axis(name='Time vs Height', axis_type='2d', title='Autoscale Example', x_label='Time', y_label='Height', time_autoscale=True)
    widget.add_axis(name='Str vs Time vs Num', axis_type='3d', title='Multi Data Type Example', x_label='Str Axis', y_label='Time Axis', z_label='Numeric Axis', z_unit=['km', 'm'])
    widget.add_axis_group(name='Example Axis Group', row_count=3, column_count=3, axis_names=['Time vs Height', 'X vs Y', 'Str vs Time vs Num'], rows=[0, 1, 1], columns=[0, 0, 1], row_spans=[1, 2, 2], column_spans=[3, 1, 2])

    # Add example artists
    widget.add_scatter_artist(axis_name='X vs Y', name='Scatter Example', data_name='1D', x_field='x', y_field='y', label_field='type', legend_text='1D', marker_color_field='type', marker_colormap='tab10', marker_color_label='Type', line_color_field='time_tz', line_colormap='jet', line_color_label='Time')
    widget.add_image_artist(axis_name='X vs Y', name='Image Example', data_name='2D', x_pos=-2, y_pos=0, color_field='z', colormap='viridis', color_label='Image Vals', color_unit=['celsius', 'fahrenheit'])
    widget.add_infinite_line_artist(axis_name='X vs Y', name='Infinite Line Example', data_name='1D', pos_field='x', is_vertical=True)
    widget.add_polygon_artist(axis_name='X vs Y', name='Polygon Artist', data_name='2D', x_field='x', y_field='y')
    widget.add_surface_artist(axis_name='X vs Y vs Z', name='Surface Example', data_name='surface', x_field='x', y_field='y', z_field='z', color_field='z')
    widget.add_arrow_artist(axis_name='Time vs Height', name='Arrow Example', data_name='1D', x_field='time_tz', y_field='z', label_field='type', legend_text='1D Arrow', arrow_spacing=2, arrow_color_field='time_tz', arrow_colormap='jet', arrow_color_label='Time', line_color_field='type', line_color_label='Type', line_colormap='tab10')
    widget.add_scatter_artist(axis_name='Str vs Time vs Num', name='3D Scatter Example', data_name='1D', x_field='type', y_field='time_tz', z_field='z', legend_text='1D')
    
    # Add example table rows
    widget.add_table_row(index=None, data_name='1D', field_name='x', label='X Value', operation='sum', color_criteria=[('<', -500, 'r')])
    widget.add_table_row(index=None, data_name='1D', field_name='y', label='Y Value', operation='mean', color_criteria=[('>=', 0, 'orange')])
    widget.add_table_row(index=None, data_name='1D', field_name='z', label='Z Value', operation='latest', color_criteria=[('>', 1000, 'yellow')])
    widget.add_table_row(index=None, data_name='1D', field_name='type', label='Type', operation='latest', color_criteria=[('==', 'sin', 'red'), ('==', 'cos', 'green')])
    widget.add_table_row(index=None, data_name='1D', field_name='time_tz', label='Time', operation='latest', color_criteria=[('change', None, 'b')])

    # Display one of the axes that was added
    widget.display_axis('X vs Y')

    # Display the DIVE GUI
    widget.show()
    app.exec()