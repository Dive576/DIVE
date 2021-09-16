from . import dive_axis, dive_axis_group, dive_data, dive_filters, dive_table_row
from .._gui import custom_qt, dialogs
from .._plotting import custom_vispy
from .._utilities import helper_functions
import importlib
import numpy as np
import pandas as pd
import pathlib
import pytz
import vispy as vp
import vispy.app as vpapp
import vispy.color as vpcolor
qt = vpapp.use_app().backend_name
try:
    qtcore = importlib.import_module('{}.QtCore'.format(qt))
    qtgui = importlib.import_module('{}.QtGui'.format(qt))
    qtwidgets = importlib.import_module('{}.QtWidgets'.format(qt))
except:
    pass
del qt
try:
    import cv2
except:
    pass
try:
    import pint
except:
    pass
try:
    import qdarkstyle
except:
    pass

class DIVEManager:
    """
    This class manages the GUI for DIVE and handles all function calls from the DIVEWidget.

    Parameters
    ----------
    widget : DIVEWidget
        The DIVEWidget to be managed.
    """
    def __init__(self, widget, unit_reg):
        vp.use(gl='gl2')
        self.widget = widget
        self.widget.setLayout(qtwidgets.QVBoxLayout())
        if 'pint' in globals():
            self.unit_reg = unit_reg if isinstance(unit_reg, pint.UnitRegistry) else pint.UnitRegistry()
        else:
            self.unit_reg = None

        self.axes = {}
        self.axis_groups = {}
        self.data = {}
        self.table_rows = []

        self.filters = dive_filters.DIVEFilters()
        self.timer = qtcore.QTimer()
        self.timer.timeout.connect(self.callback_timer)
        self.reverse_animation = self.recording = False
        self.min_time = self.max_time = self.current_time = None
        self.settings = {'time_step': 1.0,
                         'fps': 10,
                         'hold_time': 30.0,
                         'table_change_time': 5.0,
                         'timezone': 'UTC',
                         'clock_size': 10,
                         'marking': '',
                         'marking_color': '#7f7f7f',
                         'marking_size': 14,
                         'gui_theme': 'light',
                         'canvas_theme': 'light',
                         'axis_label_size': 14,
                         'axis_tick_size': 10,
                         'apply_limits_filter': True,
                         'and_filters': True}
        if 'qdarkstyle' not in globals():
            self.settings['gui_theme'] = 'default'

        # Setup the toolbar
        self.toolbar = qtwidgets.QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.layout().setContentsMargins(0, 0, 0, 0)
        self.widget.layout().addWidget(self.toolbar, 0)
        self.reset_button = qtwidgets.QToolButton()
        self.reset_button.setPopupMode(qtwidgets.QToolButton.MenuButtonPopup)
        self.reset_button.setDefaultAction(qtwidgets.QAction('Reset Axis Limits', self.reset_button))
        self.reset_button.clicked.connect(lambda: self.callback_reset(self.reset_button.defaultAction()))
        self.reset_button.triggered.connect(self.callback_reset)
        self.toolbar.addWidget(self.reset_button)
        self.autoscale_button = qtwidgets.QToolButton()
        self.autoscale_button.setPopupMode(qtwidgets.QToolButton.MenuButtonPopup)
        self.autoscale_button.setDefaultAction(qtwidgets.QAction('Autoscale Axis Limits', self.autoscale_button))
        self.autoscale_button.clicked.connect(lambda: self.callback_autoscale(self.autoscale_button.defaultAction()))
        self.autoscale_button.triggered.connect(self.callback_autoscale)
        self.toolbar.addWidget(self.autoscale_button)
        self.toolbar.addSeparator()
        self.toolbar_group = qtwidgets.QActionGroup(self.toolbar)
        self.toolbar_group.setExclusionPolicy(qtwidgets.QActionGroup.ExclusionPolicy.Exclusive)
        self.toolbar_group.triggered[qtwidgets.QAction].connect(self.callback_toolbar_group)
        self.toolbar.addAction(qtwidgets.QAction('Pan', self.toolbar_group, checkable=True, checked=True))
        self.toolbar.addAction(qtwidgets.QAction('Zoom', self.toolbar_group, checkable=True))
        selection_button = qtwidgets.QToolButton()
        selection_button.setPopupMode(qtwidgets.QToolButton.MenuButtonPopup)
        selection_button.addAction(qtwidgets.QAction('Rectangle Selection', self.toolbar_group, checkable=True))
        selection_button.addAction(qtwidgets.QAction('Ellipse Selection', self.toolbar_group, checkable=True))
        selection_button.addAction(qtwidgets.QAction('Lasso Selection', self.toolbar_group, checkable=True))
        selection_button.setDefaultAction(selection_button.actions()[0])
        selection_button.triggered.connect(lambda action: selection_button.setDefaultAction(action))
        self.toolbar.addWidget(selection_button)
        self.toolbar.addSeparator()
        axis_action = qtwidgets.QAction('Display Axis', self.toolbar)
        axis_action.triggered.connect(self.callback_axis)
        self.toolbar.addAction(axis_action)
        configure_button = qtwidgets.QToolButton()
        configure_button.setStyleSheet('QToolButton::menu-indicator { image: none; }')
        configure_button.setToolTip('Configure Objects')
        configure_button.setPopupMode(qtwidgets.QToolButton.InstantPopup)
        configure_button.addAction(qtwidgets.QAction('Configure Axes/Artists', configure_button))
        configure_button.addAction(qtwidgets.QAction('Configure Axis Groups', configure_button))
        configure_button.addAction(qtwidgets.QAction('Configure Data Selection', configure_button))
        configure_button.addAction(qtwidgets.QAction('Configure Table Rows', configure_button))
        configure_button.triggered.connect(self.callback_configure)
        self.toolbar.addWidget(configure_button)
        filter_action = qtwidgets.QAction('Filter Data', self.toolbar)
        filter_action.triggered.connect(self.callback_filter)
        self.toolbar.addAction(filter_action)
        settings_action = qtwidgets.QAction('Settings', self.toolbar)
        settings_action.triggered.connect(self.callback_settings)
        self.toolbar.addAction(settings_action)
        self.toolbar.addSeparator()
        data_inspect_action = qtwidgets.QAction('Inspect Data', self.toolbar)
        data_inspect_action.triggered.connect(lambda _: self.callback_data_inspect())
        self.toolbar.addAction(data_inspect_action)
        self.toolbar.addSeparator()
        screenshot_action = qtwidgets.QAction('Take Screenshot', self.toolbar)
        screenshot_action.triggered.connect(self.callback_screenshot)
        self.toolbar.addAction(screenshot_action)
        if 'cv2' in globals():
            record_action = qtwidgets.QAction('Record Video', self.toolbar)
            record_action.triggered.connect(self.callback_record)
            self.toolbar.addAction(record_action)

        # Setup the widgets that are visible when taking a screenshot or recording a video
        self.picture_widget = qtwidgets.QWidget()
        self.picture_widget.setLayout(qtwidgets.QVBoxLayout())
        self.picture_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.widget.layout().addWidget(self.picture_widget, 1)

        splitter = qtwidgets.QSplitter()
        self.picture_widget.layout().addWidget(splitter, 1)

        self.legend = custom_qt.CompactTreeWidget()
        self.legend.setFocusPolicy(qtcore.Qt.NoFocus)
        self.legend.setSelectionMode(qtwidgets.QAbstractItemView.NoSelection)
        self.legend.setIconSize(qtcore.QSize(32, 32))
        splitter.addWidget(self.legend)

        self.canvas = custom_vispy.Canvas(self.callback_selection)
        splitter.addWidget(self.canvas.native)

        self.table = custom_qt.CompactTableWidget(0, 1)
        self.table.horizontalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(qtwidgets.QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(qtcore.Qt.NoFocus)
        self.table.setSelectionMode(qtwidgets.QAbstractItemView.NoSelection)
        self.table.cellDoubleClicked.connect(lambda iRow, _: self.callback_data_inspect(self.table_rows[iRow]))
        splitter.addWidget(self.table)
        splitter.setSizes([splitter.size().width() * 0.1, splitter.size().width() * 0.8, splitter.size().width() * 0.1])

        text_hbox = qtwidgets.QHBoxLayout()
        self.picture_widget.layout().addLayout(text_hbox, 0)

        self.clock = qtwidgets.QLabel('')
        self.clock.setMinimumSize(1, 1)
        self.clock.setFont(qtgui.QFont(self.clock.font().family(), pointSize=min(self.settings['clock_size'], 2147483647)))
        text_hbox.addWidget(self.clock, 1)

        self.marking = qtwidgets.QLabel(self.settings['marking'])
        self.marking.setMinimumSize(1, 1)
        self.marking.setFont(qtgui.QFont(self.marking.font().family(), pointSize=min(self.settings['marking_size'], 2147483647)))
        self.marking.setStyleSheet('QLabel{{color: {}}}'.format(self.settings['marking_color']))
        text_hbox.addWidget(self.marking, 0)

        # Setup the widgets that control the animation
        self.control_bar = qtwidgets.QStackedWidget()
        self.widget.layout().addWidget(self.control_bar, 0)

        time_widget = qtwidgets.QWidget()
        time_widget.setLayout(qtwidgets.QHBoxLayout())
        time_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.control_bar.addWidget(time_widget)

        self.time_slider = qtwidgets.QSlider(qtcore.Qt.Horizontal)
        self.time_slider.setStyle(custom_qt.SliderStyle(self.time_slider.style()))
        self.time_slider.valueChanged.connect(self.callback_time_slider)
        time_widget.layout().addWidget(self.time_slider)

        self.date_edit = custom_qt.TimeEdit()
        self.date_edit.returnPressed.connect(self.callback_date_edit)
        time_widget.layout().addWidget(self.date_edit)

        self.pause_button = qtwidgets.QPushButton()
        self.pause_button.setFixedWidth(75)
        self.pause_button.clicked.connect(lambda: self.set_animation_state(not self.timer.isActive()))
        time_widget.layout().addWidget(self.pause_button)

        self.reverse_button = qtwidgets.QPushButton()
        self.reverse_button.setFixedWidth(75)
        self.reverse_button.clicked.connect(lambda: self.set_animation_direction(not self.reverse_animation))
        time_widget.layout().addWidget(self.reverse_button)

        # Setup the widgets that are used when recording a video
        video_widget = qtwidgets.QWidget()
        video_widget.setLayout(qtwidgets.QHBoxLayout())
        video_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.control_bar.addWidget(video_widget)

        self.progress_bar = qtwidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        video_widget.layout().addWidget(self.progress_bar)

        self.cancel_recording_button = qtwidgets.QPushButton('Cancel')
        self.cancel_recording_button.clicked.connect(lambda: setattr(self, 'recording', False))
        video_widget.layout().addWidget(self.cancel_recording_button)

        # Hide the animation control widgets
        self.set_control_visible()
        # Hide the legend and table widgets
        self.set_splitter_visible()
        # Set font sizes for the canvas
        self.set_font_sizes()
        # Apply the default theme
        self.set_theme()

    def align_data_selection(self):
        has_selection = any([self.data[data_name].selection is not None for data_name in self.data])
        for data_obj in self.data.values():
            if data_obj.selection is None and has_selection:
                data_obj.apply_selection(None)

    def get_hold_time(self):
        if isinstance(self.min_time, pd.Timestamp):
            return pd.Timedelta.max if self.settings['hold_time'] == 0 else pd.Timedelta(self.settings['hold_time'], unit='S')
        else:
            return pd.Timedelta.max.total_seconds() if self.settings['hold_time'] == 0 else self.settings['hold_time']

    def get_time_step(self):
        return pd.Timedelta(self.settings['time_step'], unit='S') if isinstance(self.min_time, pd.Timestamp) else self.settings['time_step']

    def grab_picture(self):
        """
        Return an image of the widgets that are visible when taking a screenshot or recording a video.

        Returns
        -------
        QPixmap
            The image data for the picture_widget.
        """
        pixmap = self.picture_widget.grab()
        canvas_pixmap = qtgui.QPixmap.fromImage(self.canvas.native.grabFramebuffer())
        painter = qtgui.QPainter(pixmap)
        painter.setCompositionMode(qtgui.QPainter.CompositionMode_Source)
        painter.drawPixmap(self.canvas.native.pos(), canvas_pixmap)
        painter.end()
        return pixmap

    def set_clock(self):
        """
        Set the clock to the current time range.
        """
        if self.current_time is None:
            self.clock.setText('')
        else:
            start_time = helper_functions.safe_time_math(self.current_time, self.get_hold_time(), add=False)
            if start_time < self.min_time:
                start_time = self.min_time
            start_str = helper_functions.strftime(start_time)
            if isinstance(self.current_time, pd.Timestamp):
                if self.current_time.date() != start_time.date():
                    end_str = helper_functions.strftime(self.current_time, include_tz=True)
                else:
                    end_str = helper_functions.strftime(self.current_time, include_date=False, include_tz=True)
            else:
                end_str = helper_functions.strftime(self.current_time)
            self.clock.setText('Time: {} to {}'.format(start_str, end_str))

    def set_control_visible(self):
        """
        Set the visibility of the widgets that control the animation.
        """
        visible = self.min_time is not None
        if 'cv2' in globals():
            self.toolbar.actions()[-1].setEnabled(visible) # The record video button
        self.control_bar.setVisible(visible)

    def set_font_sizes(self):
        self.canvas.set_font_sizes(self.settings['axis_label_size'], self.settings['axis_tick_size'])

    def set_splitter_visible(self):
        self.legend.setVisible(self.legend.topLevelItemCount() > 0)
        self.table.setVisible(self.table.rowCount() > 0)

    def set_theme(self):
        """
        Set the current theme for the GUI widgets and the canvas.
        """
        resource_path = pathlib.Path(__file__).absolute().parent.parent / '_resources'
        if self.settings['gui_theme'] == 'light':
            stylesheet = qdarkstyle.load_stylesheet(palette=qdarkstyle.light.palette.LightPalette)
        elif self.settings['gui_theme'] == 'dark':
            stylesheet = qdarkstyle.load_stylesheet(palette=qdarkstyle.dark.palette.DarkPalette)
        else:
            stylesheet = ''
        self.widget.setStyleSheet(stylesheet)
        # Prevent stylesheet from not being applied if set before widget is shown
        if not self.widget.isVisible():
            qtwidgets.QApplication.processEvents()
        self.canvas.set_theme(self.axes, self.settings['canvas_theme'])

        # Update button icons
        theme = 'light' if self.settings['gui_theme'] == 'default' else self.settings['gui_theme']
        self.pause_button.setIcon(qtgui.QIcon(str(resource_path / '{}_{}.svg'.format('pause' if self.timer.isActive() else 'play', theme))))
        self.reverse_button.setIcon(qtgui.QIcon(str(resource_path / '{}_{}.svg'.format('forward' if self.reverse_animation else 'backward', theme))))
        action_names, menu_names = ['reset', 'autoscale', 'pan', 'zoom', 'axis', 'configure', 'filter', 'settings', 'data_inspect', 'screenshot', 'record'], [None, None, ['rect_select', 'ellipse_select', 'lasso_select'], None]
        for action in self.toolbar.actions():
            if isinstance(action, qtwidgets.QWidgetAction): # Special case for QToolButtons
                select_names = menu_names.pop(0)
                if select_names is None:
                    action.defaultWidget().setIcon(qtgui.QIcon(str(resource_path / '{}_{}.svg'.format(action_names.pop(0), theme))))
                else:
                    for select_action in action.defaultWidget().actions():
                        select_action.setIcon(qtgui.QIcon(str(resource_path / '{}_{}.svg'.format(select_names.pop(0), theme))))
            elif action.text() != '': # Ignore separators
                action.setIcon(qtgui.QIcon(str(resource_path / '{}_{}.svg'.format(action_names.pop(0), theme))))

    def update_canvas(self, time_updated=False):
        if not time_updated:
            self.update_legend()
        self.canvas.update_axes(self.data, self.axes, self.current_time, self.get_hold_time(), self.settings['timezone'], self.unit_reg, time_updated=time_updated)

    def update_filters(self, filters_changed=False, limits_changed=False, data_subset=None):
        """
        Update filter indices in the data objects.

        Parameters
        ----------
        filters_changed : bool (Default: False)
            Toggle whether filter indices in the data objects should be recalculated.
        limits_changed : bool (Default: False)
            Toggle whether the setting that specifies whether filters affect limit calculations has been changed.
        data_subset : None, array (Default: None)
            The names of the data objects to recalculate the filter indices for.
            If None, all data objects will have their filter indices recalculated.
        """
        if filters_changed or limits_changed:
            if filters_changed:
                data_names = list(self.data) if data_subset is None else data_subset
                for data_name in data_names:
                    self.data[data_name].reset_filter()
                filter_idx = self.get_filter_indices(None, None, data_subset=data_subset)
                for data_name in filter_idx:
                    self.data[data_name].apply_filter(filter_idx[data_name])

            data = self.data if filters_changed else None
            self.canvas.update_filters(data, self.axes, self.settings['apply_limits_filter'])
            self.update_time_limits()
            self.update_canvas()
            self.update_table()

    def update_legend(self):
        self.legend.clear()
        entries = self.canvas.get_legend(self.data, self.axes, self.settings['apply_limits_filter'])
        for entry in entries:
            item = custom_qt.CompactTreeWidgetItem(parent=self.legend, text=entry[0])
            item.setIcon(0, qtgui.QIcon(qtgui.QPixmap.fromImage(qtgui.QImage.fromData(entry[1].encode()))))
            item.setExpanded(True)
            for subentry in entry[2]:
                subitem = custom_qt.CompactTreeWidgetItem(parent=item, text=subentry[0], enable_flags=[qtcore.Qt.ItemNeverHasChildren])
                subitem.setIcon(0, qtgui.QIcon(qtgui.QPixmap.fromImage(qtgui.QImage.fromData(subentry[1].encode()))))
        self.set_splitter_visible()

    def update_limit_buttons(self):
        """
        Update the menus for the reset and autoscale buttons in the toolbar.
        """
        for action in self.reset_button.actions():
            self.reset_button.removeAction(action)
            action.deleteLater()
        for action in self.autoscale_button.actions():
            self.autoscale_button.removeAction(action)
            action.deleteLater()
        names = sorted(set([axis.state['name'] for axis in self.canvas.axes]), key=helper_functions.natural_order)
        for name in names:
            self.reset_button.addAction(qtwidgets.QAction(name, self.reset_button))
            self.autoscale_button.addAction(qtwidgets.QAction(name, self.autoscale_button))

    def update_table(self, row_index=None):
        """
        Update row values in the table.

        Parameters
        ----------
        row_index : None, int (Default: None)
            The index of the table row to update.
            If None, all rows will be updated.
        """
        change_idx = {}
        table_change_time = pd.Timedelta(self.settings['table_change_time'], unit='S') if isinstance(self.min_time, pd.Timestamp) else self.settings['table_change_time']
        rows = range(len(self.table_rows)) if row_index is None else [row_index]
        for iRow in rows:
            value, row_color, text_color = self.table_rows[iRow].get_row_data(self.data, change_idx, self.current_time, self.settings['timezone'], table_change_time)
            self.table.item(iRow, 0).setText(value)
            self.table.verticalHeaderItem(iRow).setText(self.table_rows[iRow].label)
            if row_color is None:
                self.table.item(iRow, 0).setBackground(qtgui.QBrush())
                self.table.item(iRow, 0).setForeground(qtgui.QBrush())
            else:
                self.table.item(iRow, 0).setBackground(qtgui.QColor(row_color[0], row_color[1], row_color[2]))
                self.table.item(iRow, 0).setForeground(qtgui.QColor(text_color[0], text_color[1], text_color[2]))

    def update_time_controls(self):
        """
        Update the widgets that can set the current time.
        """
        if self.min_time is not None:
            time_delta = self.current_time.timestamp() - self.min_time.timestamp() if isinstance(self.min_time, pd.Timestamp) else self.current_time - self.min_time
            self.time_slider.blockSignals(True)
            self.time_slider.setValue(int(np.ceil(time_delta)))
            self.time_slider.blockSignals(False)
            self.date_edit.set_time(self.current_time)

    def update_time_limits(self):
        """
        Update the minimum and maximum time values based on the current data and settings.
        """
        self.min_time, self.max_time = dive_data.DIVEData.get_time_limits(self.data, use_filter=self.settings['apply_limits_filter'])
        self.min_time, self.max_time, self.current_time = helper_functions.safe_tz_convert(self.min_time, self.settings['timezone']), helper_functions.safe_tz_convert(self.max_time, self.settings['timezone']), helper_functions.safe_tz_convert(self.current_time, self.settings['timezone'])
        if self.min_time is None:
            self.current_time = None
        else:
            time_delta = self.max_time.timestamp() - self.min_time.timestamp() if isinstance(self.min_time, pd.Timestamp) else self.max_time - self.min_time
            self.time_slider.setRange(0, int(np.ceil(time_delta)))
            self.date_edit.set_limits(self.min_time, self.max_time)
            if self.current_time is None or isinstance(self.current_time, pd.Timestamp) != isinstance(self.min_time, pd.Timestamp) or self.current_time < self.min_time:
                self.set_current_time(self.min_time)
            elif self.current_time > self.max_time:
                self.set_current_time(self.max_time)
        self.update_time_controls()
        self.set_control_visible()
        self.set_clock()

    # Widget callbacks
    def callback_autoscale(self, action):
        self.axis_limits_autoscale(None if action is self.autoscale_button.defaultAction() else action.text())

    def callback_axis(self):
        name, is_group, ok = dialogs.DisplayAxisDialog.get_axis(self.widget, self.axes, self.axis_groups)
        if ok:
            if is_group:
                self.display_axis_group(name)
            else:
                self.display_axis(name)

    def callback_configure(self, action):
        actions = action.parent().actions()
        idx = actions.index(action) if action in actions else -1
        if idx == 0:
            axes, removed_names, ok = dialogs.ConfigureAxesArtistsDialog.get_axes_artists(self.widget, self.data, self.get_axis(None), self.get_artist(None, None), self.unit_reg)
            if ok:
                for axis_group_obj in self.axis_groups.values():
                    for axis_name in removed_names:
                        axis_group_obj.remove_axis(axis_name)
                self.axes = axes
                if self.canvas.current_axis_group is None:
                    if len(self.canvas.axes) > 0:
                        if self.canvas.axes[0].state['name'] in removed_names:
                            self.display_axis(None)
                        else:
                            self.canvas.recreate_grid_cell(self.data, self.axes[self.canvas.axes[0].state['name']], self.settings['apply_limits_filter'])
                            self.update_canvas()
                else:
                    self.edit_axis_group(self.canvas.current_axis_group['name'], {})
        elif idx == 1:
            axis_groups, removed_names, ok = dialogs.ConfigureAxisGroupsDialog.get_axis_groups(self.widget, self.axes, self.get_axis_group(None))
            if ok:
                current_name = None if self.canvas.current_axis_group is None else self.canvas.current_axis_group['name']
                remove_axis_group = current_name in removed_names
                if remove_axis_group:
                    self.remove_axis_group(current_name)
                self.axis_groups = axis_groups
                if not remove_axis_group and current_name is not None:
                    self.edit_axis_group(current_name, {})
        elif idx == 2:
            selection = {}
            for data_name in self.data:
                data_obj = self.data[data_name]
                if data_obj.selection is not None:
                    selection[data_name] = data_obj.selection
            selection, ok = dialogs.SelectDataDialog.get_selected(self.widget, self.data, self.settings['timezone'], selection)
            if ok:
                if len(selection) == 0:
                    for data_obj in self.data.values():
                        data_obj.reset_selection()
                else:
                    for data_obj in self.data.values():
                        data_obj.apply_selection(selection[data_obj.name] if data_obj.name in selection else None)
                self.canvas.update_axes(self.data, self.axes, self.current_time, self.get_hold_time(), self.settings['timezone'], self.unit_reg, time_updated=False)
        elif idx == 3:
            table_rows, ok = dialogs.ConfigureTableRowsDialog.get_table_rows(self.widget, self.data, self.get_table_row(None), self.settings['timezone'])
            if ok:
                self.table_rows = table_rows
                for row in reversed(range(self.table.rowCount())):
                    self.table.removeRow(row)
                for row in range(len(self.table_rows)):
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, qtwidgets.QTableWidgetItem(''))
                    self.table.setVerticalHeaderItem(row, qtwidgets.QTableWidgetItem(''))
                self.set_splitter_visible()
                self.update_table()

    def callback_data_inspect(self, table_row=None):
        """
        Open the inspect data dialog.

        Parameters
        ----------
        table_row : None, DIVETableRow (Default: None)
            A table row object. If not None and its operation is "latest",
            the data inspection window will highlight the latest value in
            the data field referenced by the table row object.
        """
        if table_row is None:
            highlight_cell = None
        elif table_row.operation == 'latest':
            valid_idx = np.nonzero(self.data[table_row.data_name].get_valid_idx(self.current_time))[0]
            highlight_cell = (table_row.data_name, table_row.field_name, valid_idx[-1]) if len(valid_idx) > 0 else None
        else:
            return
        dialogs.InspectDataDialog.inspect_data(self.widget, self.data, self.settings['timezone'], highlight_cell)

    def callback_date_edit(self):
        self.set_current_time(self.date_edit.get_time())

    def callback_filter(self):
        if not self.recording:
            filters, ok = dialogs.FilterDialog.get_filters(self.widget, self.data, self.filters, self.settings['timezone'])
            if ok:
                self.filters = filters
                self.update_filters(filters_changed=True)

    def callback_reset(self, action):
        self.axis_limits_reset(None if action is self.reset_button.defaultAction() else action.text())

    def callback_record(self):
        if not self.recording:
            details, ok = dialogs.RecordDialog.get_video_details(self.widget, self.min_time, self.max_time, self.settings['fps'])
            if ok:
                self.record_video(**details)

    def callback_screenshot(self):
        file_path, _ = qtwidgets.QFileDialog.getSaveFileName(self.widget, 'Save Screenshot', '', 'PNG File (*.png)')
        if file_path:
            self.take_screenshot(file_path)

    def callback_selection(self, clear):
        if clear:
            if len(self.data) == 0:
                return
            for data_obj in self.data.values():
                if data_obj.selection is None: # No data is currently selected
                    return
                data_obj.reset_selection()
        else:
            self.canvas.select_points(self.data, self.axes, self.current_time, self.get_hold_time())
        self.canvas.update_axes(self.data, self.axes, self.current_time, self.get_hold_time(), self.settings['timezone'], self.unit_reg, time_updated=False)

    def callback_settings(self):
        if not self.recording:
            settings, ok = dialogs.SettingsDialog.get_settings(self.widget, 'qdarkstyle' in globals(), **self.settings.copy())
            if ok:
                self.set_settings(settings)

    def callback_time_slider(self, time):
        self.set_current_time(helper_functions.safe_time_math(self.min_time, pd.Timedelta(time, unit='S') if isinstance(self.min_time, pd.Timestamp) else time, add=True))

    def callback_timer(self):
        time = helper_functions.safe_time_math(self.current_time, self.get_time_step(), add=not self.reverse_animation)
        if time <= self.min_time or time >= self.max_time:
            self.set_animation_state(False)
        self.set_current_time(time)

    def callback_toolbar_group(self, action):
        if action.text() == 'Pan':
            self.canvas.set_mode('pan')
        elif action.text() == 'Zoom':
            self.canvas.set_mode('zoom')
        elif action.text() == 'Rectangle Selection':
            self.canvas.set_mode('rectangle')
        elif action.text() == 'Ellipse Selection':
            self.canvas.set_mode('ellipse')
        elif action.text() == 'Lasso Selection':
            self.canvas.set_mode('lasso')

    # DIVEWidget functions
    def add_artist(self, axis_name, artist_type, state):
        if not isinstance(axis_name, str):
            helper_functions.print_error('Cannot add artist. axis_name must be of type: str')
        elif axis_name in self.axes:
            axis_obj = self.axes[axis_name]
            err_msg = axis_obj.add_artist(self.data, artist_type, self.unit_reg, state)
            if err_msg is None:
                need_update = self.canvas.recreate_grid_cell(self.data, axis_obj, self.settings['apply_limits_filter'])
                if need_update:
                    self.update_canvas()
            else:
                helper_functions.print_error('Cannot add {} artist. {}'.format(artist_type, err_msg))
        else:
            helper_functions.print_error('Cannot add artist. "{}" is not a valid axis name.'.format(axis_name))

    def add_axis(self, state):
        axis_obj = dive_axis.DIVEAxis()
        err_msg = axis_obj.set_state(list(self.axes), self.unit_reg, state)
        if err_msg is None:
            self.axes[axis_obj.name] = axis_obj
            self.axes = dict(sorted(self.axes.items(), key=lambda item: helper_functions.natural_order(item[0])))
        else:
            helper_functions.print_error('Cannot add axis. {}'.format(err_msg))

    def add_axis_group(self, state):
        axis_group_obj = dive_axis_group.DIVEAxisGroup()
        err_msg = axis_group_obj.set_state(list(self.axes), list(self.axis_groups), state)
        if err_msg is None:
            self.axis_groups[axis_group_obj.name] = axis_group_obj
            self.axis_groups = dict(sorted(self.axis_groups.items(), key=lambda item: helper_functions.natural_order(item[0])))
        else:
            helper_functions.print_error('Cannot add axis group. {}'.format(err_msg))

    def add_data(self, state):
        if self.recording:
            helper_functions.print_error('Cannot add data. A video recording is in progress.')
        else:
            data_obj = dive_data.DIVEData()
            data_names = list(self.data)
            err_msg = data_obj.set_state(data_names, state)
            if err_msg is None:
                self.data[data_obj.name] = data_obj
                self.data = dict(sorted(self.data.items(), key=lambda item: helper_functions.natural_order(item[0])))
                self.align_data_selection()

                # Update the time limits since they might have changed
                self.update_time_limits()
            else:
                helper_functions.print_error('Cannot add data. {}'.format(err_msg))

    def add_filter(self, filter_type, state):
        if self.recording:
            helper_functions.print_error('Cannot add {} filter group. A video recording is in progress.'.format(filter_type))
        else:
            err_msg = self.filters.add_filter(self.data, filter_type, state)
            if err_msg is None:
                if state['enabled']:
                    self.update_filters(filters_changed=True, data_subset=self.filters.get_data_names(filter_type, state['name']))
            else:
                helper_functions.print_error('Cannot add {} filter group. {}'.format(filter_type, err_msg))

    def add_table_row(self, state):
        if not isinstance(state['index'], (type(None), int, np.integer)):
            helper_functions.print_error('Cannot add table row. index must be one of the following types: None, int')
        else:
            table_row_obj = dive_table_row.DIVETableRow()
            err_msg = table_row_obj.set_state(self.data, state)
            if err_msg is None:
                row_count = len(self.table_rows)
                index = row_count if state['index'] is None else np.clip(state['index'], 0, row_count)
                self.table_rows.insert(index, table_row_obj)

                # Update the table widget
                self.table.insertRow(index)
                self.table.setItem(index, 0, qtwidgets.QTableWidgetItem(''))
                self.table.setVerticalHeaderItem(index, qtwidgets.QTableWidgetItem(''))
                self.set_splitter_visible()
                self.update_table(index)
            else:
                helper_functions.print_error('Cannot add table row. {}'.format(err_msg))

    def axis_limits_autoscale(self, name):
        if not isinstance(name, (type(None), str)):
            helper_functions.print_error('Cannot autoscale axis limits. name must be one of the following types: None, str')
        elif name is None or name in self.axes:
            self.canvas.axis_limits_autoscale(self.data, self.axes, name, self.current_time, self.get_hold_time())
        else:
            helper_functions.print_error('Cannot autoscale axis limits. "{}" is not a valid axis name.'.format(name))

    def axis_limits_reset(self, name):
        if not isinstance(name, (type(None), str)):
            helper_functions.print_error('Cannot reset axis limits. name must be one of the following types: None, str')
        elif name is None or name in self.axes:
            self.canvas.axis_limits_reset(name)
        else:
            helper_functions.print_error('Cannot reset axis limits. "{}" is not a valid axis name.'.format(name))

    def display_axis(self, name):
        if not isinstance(name, (type(None), str)):
            helper_functions.print_error('Cannot display axis. name must be one of the following types: None, str')
        elif name is None or name in self.axes:
            need_update = self.canvas.display_axis(self.data, self.axes, name, self.settings['apply_limits_filter'])
            if need_update:
                self.update_canvas()
                self.update_limit_buttons()
        else:
            helper_functions.print_error('Cannot display axis. "{}" is not a valid axis name.'.format(name))

    def display_axis_group(self, name):
        if not isinstance(name, (type(None), str)):
            helper_functions.print_error('Cannot display axis group. name must be one of the following types: None, str')
        elif name is None or name in self.axis_groups:
            need_update = self.canvas.display_axis_group(self.data, self.axes, self.axis_groups, name, self.settings['apply_limits_filter'])
            if need_update:
                self.update_canvas()
                self.update_limit_buttons()
        else:
            helper_functions.print_error('Cannot display axis group. "{}" is not a valid axis group name.'.format(name))

    def edit_artist(self, axis_name, name, state):
        if not isinstance(name, str):
            helper_functions.print_error('Cannot edit artist. axis_name must be of type: str')
        elif axis_name in self.axes:
            axis_obj = self.axes[axis_name]
            err_msg = axis_obj.edit_artist(self.data, name, self.unit_reg, state)
            if err_msg is None:
                need_update = self.canvas.recreate_grid_cell(self.data, axis_obj, self.settings['apply_limits_filter'])
                if need_update:
                    self.update_canvas()
            else:
                helper_functions.print_error('Cannot edit artist. {}'.format(err_msg))
        else:
            helper_functions.print_error('Cannot edit artist. "{}" is not a valid axis name.'.format(axis_name))

    def edit_axis(self, name, state):
        if not isinstance(name, str):
            helper_functions.print_error('Cannot edit axis. name must be of type: str')
        elif name in self.axes:
            axis_obj = self.axes[name]
            err_msg = axis_obj.set_state(list(self.axes), self.unit_reg, state)
            if err_msg is None:
                need_update = self.canvas.edit_axis(axis_obj)
                if need_update:
                    self.update_canvas()
            else:
                helper_functions.print_error('Cannot edit axis. {}'.format(err_msg))
        else:
            helper_functions.print_error('Cannot edit axis. "{}" is not a valid axis name.'.format(name))

    def edit_axis_group(self, name, state):
        if not isinstance(name, str):
            helper_functions.print_error('Cannot edit axis group. name must be of type: str')
        elif name in self.axis_groups:
            axis_group_obj = self.axis_groups[name]
            err_msg = axis_group_obj.set_state(list(self.axes), list(self.axis_groups), state)
            if err_msg is None:
                need_update = self.canvas.edit_axis_group(self.data, self.axes, axis_group_obj, self.settings['apply_limits_filter'])
                if need_update:
                    self.update_canvas()
                    self.update_limit_buttons()
            else:
                helper_functions.print_error('Cannot edit axis group. {}'.format(err_msg))
        else:
            helper_functions.print_error('Cannot edit axis group. "{}" is not a valid axis group name.'.format(name))

    def edit_data(self, name, state):
        if self.recording:
            helper_functions.print_error('Cannot edit data. A video recording is in progress.')
        elif not isinstance(name, str):
            helper_functions.print_error('Cannot edit data. name must be of type: str')
        elif name in self.data:
            data_obj = self.data[name]
            err_msg = data_obj.set_state(list(self.data), state)
            if err_msg is None:
                self.align_data_selection()
                for axis_obj in self.axes.values():
                    axis_obj.validate_data(self.data, self.unit_reg)
                self.filters.validate_data(self.data, name)
                for i in reversed(range(self.table.rowCount())):
                    err_msg = self.table_rows[i].set_state(self.data, {'data_name': self.table_rows[i].data_name})
                    if err_msg is not None:
                        self.remove_table_row(i)
                if self.canvas.current_axis_group is None:
                    if len(self.canvas.axes) > 0:
                        self.canvas.recreate_grid_cell(self.data, self.axes[self.canvas.axes[0].state['name']], self.settings['apply_limits_filter'])
                else:
                    self.canvas.edit_axis_group(self.data, self.axes, self.axis_groups[self.canvas.current_axis_group['name']], self.settings['apply_limits_filter'])
                self.update_filters(filters_changed=True)
            else:
                helper_functions.print_error('Cannot edit data. {}'.format(err_msg))
        else:
            helper_functions.print_error('Cannot edit data. "{}" is not a valid data name.'.format(name))

    def edit_filter(self, filter_type, name, state):
        if self.recording:
            helper_functions.print_error('Cannot edit {} filter group. A video recording is in progress.'.format(filter_type))
        else:
            old_filter_obj, err_msg = self.filters.get_filter(filter_type, name)
            if err_msg is None:
                data_names = self.filters.get_data_names(filter_type, name)
            new_filter_obj, err_msg = self.filters.edit_filter(self.data, filter_type, name, state)
            if err_msg is None:
                data_names = list(set(data_names + self.filters.get_data_names(filter_type, new_filter_obj['name'])))
                if old_filter_obj['enabled'] or new_filter_obj['enabled']:
                    self.update_filters(filters_changed=True, data_subset=data_names)
            else:
                helper_functions.print_error('Cannot edit {} filter group. {}'.format(err_msg, filter_type))

    def edit_table_row(self, row_index, state):
        if not isinstance(row_index, (int, np.integer)):
            helper_functions.print_error('Cannot edit table row. row_index must be of type: int')
        elif not 0 <= row_index < len(self.table_rows):
            helper_functions.print_error('Cannot edit table row. Index {} is invalid for row count of {}.'.format(row_index, len(self.table_rows)))
        elif 'index' in state and not isinstance(state['index'], (type(None), int, np.integer)):
            helper_functions.print_error('Cannot edit table row. Index must be one of the following types: None, int')
        else:
            err_msg = self.table_rows[row_index].set_state(self.data, state)
            if err_msg is None:
                if 'index' in state:
                    row_count = len(self.table_rows)
                    new_index = row_count if state['index'] is None else np.clip(state['index'], 0, row_count)
                    self.table_rows.insert(new_index, self.table_rows.pop(row_index))

                    # Update the table widget
                    item, header = self.table.takeItem(row_index, 0), self.table.takeVerticalHeaderItem(row_index)
                    self.table.removeRow(row_index)
                    self.table.insertRow(new_index)
                    self.table.setItem(new_index, 0, item)
                    self.table.setVerticalHeaderItem(new_index, header)
                    row_index = new_index
                self.update_table(row_index)
            else:
                helper_functions.print_error('Cannot edit table row. {}'.format(err_msg))

    def get_animation_direction(self):
        return self.reverse_animation

    def get_animation_state(self):
        return self.timer.isActive()

    def get_artist(self, axis_name, name):
        if not isinstance(axis_name, (type(None), str)):
            helper_functions.print_error('Cannot get artist. axis_name must be one of the following types: None, str')
        elif axis_name is None:
            return {axis_obj.name: axis_obj.get_artist(None)[0] for axis_obj in self.axes.values()}
        elif axis_name in self.axes:
            artist, err_msg = self.axes[axis_name].get_artist(name)
            if err_msg is None:
                return artist
            else:
                helper_functions.print_error('Cannot get artist. {}'.format(err_msg))
        else:
            helper_functions.print_error('Cannot get artist. "{}" is not a valid axis name.'.format(axis_name))

    def get_axis(self, name):
        if not isinstance(name, (type(None), str)):
            helper_functions.print_error('Cannot get axis. name must be one of the following types: None, str')
        elif name is None:
            return [axis_obj.get_state() for axis_obj in self.axes.values()]
        elif name in self.axes:
            return self.axes[name].get_state()
        else:
            helper_functions.print_error('Cannot get axis. "{}" is not a valid axis name.'.format(name))

    def get_axis_group(self, name):
        if not isinstance(name, (type(None), str)):
            helper_functions.print_error('Cannot get axis group. name must be one of the following types: None, str')
        elif name is None:
            return [axis_group_obj.get_state() for axis_group_obj in self.axis_groups.values()]
        elif name in self.axis_groups:
            return self.axis_groups[name].get_state()
        else:
            helper_functions.print_error('Cannot get axis group. "{}" is not a valid axis group name.'.format(name))

    def get_current_time(self):
        return self.current_time

    def get_data(self, name):
        if not isinstance(name, (type(None), str)):
            helper_functions.print_error('Cannot get data. name must be one of the following types: None, str')
        elif name is None:
            return [self.data[data_name].get_state() for data_name in self.data]
        elif name in self.data:
            return self.data[name].get_state()
        else:
            helper_functions.print_error('Cannot get data. "{}" is not a valid data name.'.format(name))

    def get_filter(self, filter_type, name):
        filter, err_msg = self.filters.get_filter(filter_type, name)
        if err_msg is None:
            return filter
        else:
            helper_functions.print_error('Cannot get {} filter group. {}'.format(filter_type, err_msg))

    def get_filter_indices(self, filter_type, name, data_subset=None):
        filter_idx, err_msg = self.filters.get_filter_indices(self.data, filter_type, name, self.settings['and_filters'], data_subset)
        if err_msg is None:
            return filter_idx
        else:
            helper_functions.print_error('Cannot get {} filter group indices. {}'.format(filter_type, err_msg))

    def get_interact_mode(self):
        mode_names = ['pan', 'zoom', 'rectangle', 'ellipse', 'lasso']
        return mode_names[self.toolbar_group.actions().index(self.toolbar_group.checkedAction())]

    def get_recording_state(self):
        return self.recording

    def get_settings(self):
        return self.settings.copy()

    def get_table_row(self, index):
        if not isinstance(index, (type(None), int, np.integer)):
            helper_functions.print_error('Cannot get table row. Index must be one of the following types: None, int')
        elif index is None:
            table_rows = []
            for i, table_row_obj in enumerate(self.table_rows):
                table_rows.append(table_row_obj.get_state())
                table_rows[-1]['index'] = i
            return table_rows
        elif not 0 <= index < len(self.table_rows):
            helper_functions.print_error('Cannot get table row. Index {} is invalid for row count of {}.'.format(index, len(self.table_rows)))
        else:
            return self.table_rows[index].get_state()

    def get_time_limits(self):
        return self.min_time, self.max_time

    def record_video(self, file_path, start_time, stop_time, fps):
        err_msg = None

        if 'cv2' not in globals():
            err_msg = 'The "opencv-python" module must be installed in order to record a video.'
        elif self.recording:
            err_msg = 'A video recording is in progress.'
        elif not isinstance(file_path, str):
            err_msg = 'file_path must be of type: str'
        else:
            try:
                p = pathlib.Path(file_path)
                p.exists() # Causes exception if file_path is invalid
                valid = p.parent.exists()
            except:
                valid = False
            if valid:
                if p.suffix.lower() != '.mp4':
                    p = p.parent / (p.name + '.mp4')
                file_path = str(p)
            else:
                err_msg = '"{}" isn\'t a valid file path.'.format(file_path)
        if err_msg is None:
            times = [start_time, stop_time]
            for i in range(2):
                if isinstance(times[i], pd.Timestamp) and times[i].tzinfo is not None:
                    times[i] = helper_functions.safe_tz_convert(times[i], self.settings['timezone'])
                    if not isinstance(self.min_time, pd.Timestamp):
                        err_msg = 'The current range of time values aren\'t pandas.Timestamps with tz.'
                elif pd.api.types.is_numeric_dtype(type(times[i])):
                    times[i] = times[i].real
                    if not pd.api.types.is_numeric_dtype(type(self.min_time)):
                        err_msg = 'The current range of time values aren\'t numeric.'
                    elif not np.isfinite(times[i]):
                        err_msg = 'Start and stop times must be finite.'
                else:
                    err_msg = 'Start and stop times must be one of the following types: numeric, pandas.Timestamp with tz'
            if err_msg is None:
                start_time, stop_time = np.clip(times, self.min_time, self.max_time)
                if start_time > stop_time:
                    err_msg = 'start_time cannot be after stop_time.'
        if err_msg is None:
            if isinstance(fps, type(None)):
                fps = self.settings['fps']
            elif not isinstance(fps, (int, np.integer)):
                err_msg = 'fps must be one of the following types: None, int'
            elif fps <= 0:
                err_msg = 'fps must be greater than 0.'

        if err_msg is None:
            self.set_animation_state(False)
            orig_time = self.current_time
            time_step = self.get_time_step()
            is_timestamp = isinstance(self.min_time, pd.Timestamp)
            min_size, max_size = self.widget.minimumSize(), self.widget.maximumSize()
            self.progress_bar.setValue(self.progress_bar.minimum())
            self.control_bar.setCurrentIndex(1)
            self.widget.setFixedSize(self.widget.size())

            frames, time = [], start_time
            self.recording = True
            while True:
                if not self.recording:
                    break
                self.set_current_time(time, recording_override=True)
                # Process events to be able to catch cancel button press
                qtwidgets.QApplication.processEvents()
                buffer = qtcore.QBuffer()
                buffer.open(qtcore.QBuffer.ReadWrite)
                self.grab_picture().save(buffer, 'PNG')
                b = buffer.data()
                buffer.close()
                frames.append(cv2.imdecode(np.frombuffer(b, dtype='uint8'), flags=1))
                if is_timestamp:
                    self.progress_bar.setValue(int((self.current_time.timestamp() - start_time.timestamp() + time_step.total_seconds()) / (stop_time.timestamp() - start_time.timestamp() + time_step.total_seconds()) * self.progress_bar.maximum()))
                else:
                    self.progress_bar.setValue(int((self.current_time - start_time + time_step) / (stop_time - start_time + time_step) * self.progress_bar.maximum()))
                if self.current_time == stop_time:
                    break
                time = np.clip(helper_functions.safe_time_math(self.current_time, time_step, add=True), None, stop_time)
            if self.recording and len(frames) > 0:
                height, width, _ = frames[0].shape
                video = cv2.VideoWriter(file_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
                for frame in frames:
                    video.write(frame)
                video.release()
            self.recording = False

            self.widget.setMinimumSize(min_size)
            self.widget.setMaximumSize(max_size)
            self.control_bar.setCurrentIndex(0)
            self.set_current_time(orig_time)
        else:
            helper_functions.print_error('Cannot record video. {}'.format(err_msg))

    def remove_artist(self, axis_name, name):
        if not isinstance(axis_name, (type(None), str)):
            helper_functions.print_error('Cannot remove artist. axis_name must be one of the following types: None, str')
        elif axis_name is None:
            for axis_obj in self.axes.values():
                axis_obj.remove_artist(None)
            if self.canvas.current_axis_group is None:
                if len(self.canvas.axes) > 0:
                    self.canvas.recreate_grid_cell(self.data, self.axes[self.canvas.axes[0].state['name']], self.settings['apply_limits_filter'])
                    self.update_canvas()
            else:
                self.edit_axis_group(self.canvas.current_axis_group['name'], {})
        elif axis_name in self.axes:
            axis_obj = self.axes[axis_name]
            err_msg = axis_obj.remove_artist(name)
            if err_msg is None:
                need_update = self.canvas.recreate_grid_cell(self.data, axis_obj, self.settings['apply_limits_filter'])
                if need_update:
                    self.update_canvas()
            else:
                helper_functions.print_error('Cannot remove artist. {}'.format(err_msg))
        else:
            helper_functions.print_error('Cannot remove artist. "{}" is not a valid axis name.'.format(axis_name))

    def remove_axis(self, name):
        if not isinstance(name, (type(None), str)):
            helper_functions.print_error('Cannot remove axis. name must be one of the following types: None, str')
        elif name is None:
            for axis_group_obj in self.axis_groups.values():
                for axis_name in list(self.axes):
                    axis_group_obj.remove_axis(axis_name)
            self.axes = {}
            if self.canvas.current_axis_group is None:
                self.display_axis(None)
            else:
                self.edit_axis_group(self.canvas.current_axis_group['name'], {})
        elif name in self.axes:
            del self.axes[name]
            for axis_group_obj in self.axis_groups.values():
                axis_group_obj.remove_axis(name)
            need_update = self.canvas.remove_axis(self.data, self.axes, self.axis_groups, name, self.settings['apply_limits_filter'])
            if need_update:
                self.update_canvas()
                self.update_limit_buttons()
        else:
            helper_functions.print_error('Cannot remove axis. "{}" is not a valid axis name.'.format(name))

    def remove_axis_group(self, name):
        if not isinstance(name, (type(None), str)):
            helper_functions.print_error('Cannot remove axis group. name must be one of the following types: None, str')
        elif name is None:
            self.axis_groups = {}
            if self.canvas.current_axis_group is not None:
                self.display_axis_group(None)
        elif name in self.axis_groups:
            del self.axis_groups[name]
            need_update = self.canvas.remove_axis_group(name)
            if need_update:
                self.update_limit_buttons()
        else:
            helper_functions.print_error('Cannot remove axis group. "{}" is not a valid axis group name.'.format(name))

    def remove_data(self, name):
        if self.recording:
            helper_functions.print_error('Cannot remove data. A video recording is in progress.')
        elif not isinstance(name, (type(None), str)):
            helper_functions.print_error('Cannot remove data. name must be one of the following types: None, str')
        elif name is None:
            self.data = {}
            for axis_obj in self.axes.values():
                axis_obj.remove_data(name)
            self.filters.remove_data(name)
            for i in reversed(range(self.table.rowCount())):
                self.remove_table_row(i)
            if self.canvas.current_axis_group is None:
                if len(self.canvas.axes) > 0:
                    self.canvas.recreate_grid_cell(self.data, self.axes[self.canvas.axes[0].state['name']], self.settings['apply_limits_filter'])
            else:
                self.canvas.edit_axis_group(self.data, self.axes, self.axis_groups[self.canvas.current_axis_group['name']], self.settings['apply_limits_filter'])
            self.update_filters(filters_changed=True)
        elif name in self.data:
            del self.data[name]
            for axis_obj in self.axes.values():
                axis_obj.remove_data(name)
            self.filters.remove_data(name)
            for i in reversed(range(self.table.rowCount())):
                if self.table_rows[i].data_name == name:
                    self.remove_table_row(i)
            if self.canvas.current_axis_group is None:
                if len(self.canvas.axes) > 0:
                    self.canvas.recreate_grid_cell(self.data, self.axes[self.canvas.axes[0].state['name']], self.settings['apply_limits_filter'])
            else:
                self.canvas.edit_axis_group(self.data, self.axes, self.axis_groups[self.canvas.current_axis_group['name']], self.settings['apply_limits_filter'])
            self.update_filters(filters_changed=True)
        else:
            helper_functions.print_error('Cannot remove data. "{}" is not a valid data name.'.format(name))

    def remove_filter(self, filter_type, name):
        if self.recording:
            helper_functions.print_error('Cannot edit {} filter group. A video recording is in progress.'.format(filter_type))
        elif name is None:
            filters, _ = self.filters.get_filter(filter_type, name)
            if len(filters) == 0:
                return
            data_names = set()
            for i in range(len(filters)):
                if filters[i]['enabled']:
                    data_names.update(self.filters.get_data_names(filter_type, filters[i]['name']))
            self.filters.remove_filter(filter_type, name)
            self.update_filters(filters_changed=True, data_subset=list(data_names))
        else:
            filter_obj, err_msg = self.filters.get_filter(filter_type, name)
            if err_msg is None:
                data_names = self.filters.get_data_names(filter_type, name)
            err_msg = self.filters.remove_filter(filter_type, name)
            if err_msg is None:
                if filter_obj['enabled']:
                    self.update_filters(filters_changed=True, data_subset=data_names)
            else:
                helper_functions.print_error('Cannot remove {} filter group. {}'.format(err_msg, filter_type))

    def remove_table_row(self, index):
        if not isinstance(index, (type(None), int, np.integer)):
            helper_functions.print_error('Cannot remove table row. index must be one of the following types: None, int')
        elif index is None:
            self.table_rows = []
            for row in reversed(range(self.table.rowCount())):
                self.table.removeRow(row)
            self.set_splitter_visible()
        elif not 0 <= index < len(self.table_rows):
            helper_functions.print_error('Cannot remove table row. Index {} is invalid for row count of {}.'.format(index, len(self.table_rows)))
        else:
            del self.table_rows[index]
            self.table.removeRow(index)
            self.set_splitter_visible()

    def set_animation_direction(self, reverse):
        if isinstance(reverse, (bool, np.bool_)):
            resource_path = pathlib.Path(__file__).absolute().parent.parent / '_resources'
            icon_name = 'forward_{}.svg' if reverse else 'backward_{}.svg'
            self.reverse_button.setIcon(qtgui.QIcon(str(resource_path / icon_name.format('light' if self.settings['gui_theme'] == 'default' else self.settings['gui_theme']))))
            self.reverse_animation = reverse
        else:
            helper_functions.print_error('Cannot set animation direction. reverse must be of type: bool')

    def set_animation_state(self, running):
        if self.recording:
            helper_functions.print_error('Cannot set animation state. A video recording is in progress.')
        elif isinstance(running, (bool, np.bool_)):
            resource_path = pathlib.Path(__file__).absolute().parent.parent / '_resources'
            if running and not self.timer.isActive():
                if (self.reverse_animation and self.current_time == self.min_time) or (not self.reverse_animation and self.current_time == self.max_time):
                    return
                self.pause_button.setIcon(qtgui.QIcon(str(resource_path / 'pause_{}.svg'.format('light' if self.settings['gui_theme'] == 'default' else self.settings['gui_theme']))))
                self.timer.start(np.max([int(1000 / self.settings['fps']), 1]))
            elif not running and self.timer.isActive():
                self.pause_button.setIcon(qtgui.QIcon(str(resource_path / 'play_{}.svg'.format('light' if self.settings['gui_theme'] == 'default' else self.settings['gui_theme']))))
                self.timer.stop()
        else:
            helper_functions.print_error('Cannot set animation state. running must be of type: bool')

    def set_current_time(self, time, recording_override=False):
        if self.recording and not recording_override:
            helper_functions.print_error('Cannot set current time. A video recording is in progress.')
            return
        if isinstance(time, pd.Timestamp) and time.tzinfo is not None:
            time = helper_functions.safe_tz_convert(time, self.settings['timezone'])
            if not isinstance(self.min_time, pd.Timestamp):
                helper_functions.print_error('Cannot set current time. The current range of time values aren\'t pandas.Timestamps with tz.')
                return
        elif pd.api.types.is_numeric_dtype(type(time)):
            time = time.real
            if not pd.api.types.is_numeric_dtype(type(self.min_time)):
                helper_functions.print_error('Cannot set current time. The current range of time values aren\'t numeric.')
                return
            elif not np.isfinite(time):
                helper_functions.print_error('Cannot set current time. time must be finite.')
                return
        else:
            helper_functions.print_error('Cannot set current time. time must be one of the following types: numeric, pandas.Timestamp with tz')
            return

        clipped_time = np.clip(time, self.min_time, self.max_time)
        if self.current_time == clipped_time:
            return
        self.current_time = clipped_time
        self.update_time_controls()
        self.set_clock()
        self.update_canvas(time_updated=True)
        self.update_table()
        self.widget.current_time_changed.emit()

    def set_interact_mode(self, mode):
        mode_names = ['pan', 'zoom', 'rectangle', 'ellipse', 'lasso']
        if not isinstance(mode, str):
            helper_functions.print_error('mode must be of type: str')
        elif mode.lower() not in mode_names:
            helper_functions.print_error('mode must be one of the following: "pan", "zoom", "rectangle", "ellipse", "lasso"')
        else:
            self.toolbar_group.actions()[mode_names.index(mode.lower())].trigger()

    def set_settings(self, state):
        if self.recording:
            helper_functions.print_error('Cannot set settings. A video recording is in progress.')
            return

        settings = self.settings.copy()
        err_msg = None

        for attr in ['time_step', 'hold_time', 'table_change_time', 'clock_size', 'marking_size', 'axis_label_size', 'axis_tick_size']:
            if attr in state:
                settings[attr] = state[attr]
                if not pd.api.types.is_numeric_dtype(type(settings[attr])):
                    err_msg = '{} must be numeric.'.format(attr)
                elif not np.isfinite(settings[attr]):
                    err_msg = '{} must be finite.'.format(attr)
                settings[attr] = settings[attr].real
                if attr == 'time_step' and not 0 < settings[attr] <= pd.Timedelta.max.total_seconds():
                    err_msg = '{} must be greater than 0 and less than or equal to {}.'.format(attr, pd.Timedelta.max.total_seconds())
                elif attr in ['hold_time', 'table_change_time'] and not 0 <= settings[attr] <= pd.Timedelta.max.total_seconds():
                    err_msg = '{} must be greater than or equal to 0 and less than or equal to {}.'.format(attr, pd.Timedelta.max.total_seconds())
                elif attr in ['clock_size', 'marking_size', 'axis_label_size', 'axis_tick_size'] and not 0 <= settings[attr]:
                    err_msg = '{} must be greater than or equal to 0.'.format(attr)
        if 'fps' in state:
            settings['fps'] = state['fps']
            if not isinstance(settings['fps'], (int, np.integer)):
                err_msg = 'fps must be of type: int'
            elif settings['fps'] <= 0:
                err_msg = 'fps must be greater than 0.'
        if 'timezone' in state:
            settings['timezone'] = state['timezone']
            if not isinstance(settings['timezone'], str):
                err_msg = 'timezone must be of type: str'
            try:
                pytz.timezone(settings['timezone'])
            except:
                err_msg = '"{}" is not a valid pytz timezone string.'
        if 'marking' in state:
            settings['marking'] = state['marking']
            if not isinstance(settings['marking'], str):
                err_msg = 'marking must be of type: str'
        if 'marking_color' in state:
            settings['marking_color'] = state['marking_color']
            if not isinstance(settings['marking_color'], str):
                err_msg = 'marking_color must be of type: str'
            else:
                try:
                    settings['marking_color'] = vpcolor.Color(settings['marking_color']).hex
                except:
                    err_msg = '"{}" is not a valid color string.'.format(settings['marking_color'])
        if 'gui_theme' in state:
            settings['gui_theme'] = state['gui_theme']
            if 'qdarkstyle' not in globals():
                settings['gui_theme'] = 'default'
            elif not isinstance(settings['gui_theme'], str):
                err_msg = 'gui_theme must be of type: str'
            settings['gui_theme'] = settings['gui_theme'].lower()
            if settings['gui_theme'] not in ['default', 'light', 'dark']:
                err_msg = 'gui_theme must be one of the following: "default", "light", "dark"'
        if 'canvas_theme' in state:
            settings['canvas_theme'] = state['canvas_theme']
            if not isinstance(settings['canvas_theme'], str):
                err_msg = 'canvas_theme must be of type: str'
            settings['canvas_theme'] = settings['canvas_theme'].lower()
            if settings['canvas_theme'] not in ['light', 'dark']:
                err_msg = 'canvas_theme must be one of the following: "light", "dark"'
        for attr in ['apply_limits_filter', 'and_filters']:
            if attr in state:
                settings[attr] = state[attr]
                if not isinstance(settings[attr], (bool, np.bool_)):
                    err_msg = '{} must be of type: bool'.format(attr)

        if err_msg is None:
            old_settings = self.settings.copy()
            self.settings = settings

            self.clock.setFont(qtgui.QFont(self.clock.font().family(), pointSize=min(self.settings['clock_size'], 2147483647)))
            self.marking.setFont(qtgui.QFont(self.marking.font().family(), pointSize=min(self.settings['marking_size'], 2147483647)))
            self.marking.setText(self.settings['marking'])
            self.marking.setStyleSheet('QLabel{{color: {}}}'.format(self.settings['marking_color']))
            filters_changed, limits_changed = old_settings['and_filters'] != self.settings['and_filters'], old_settings['apply_limits_filter'] != self.settings['apply_limits_filter']
            if filters_changed or limits_changed:
                if filters_changed:
                    self.filters.and_filters = self.settings['and_filters']
                self.update_filters(filters_changed=filters_changed, limits_changed=limits_changed)
            else:
                need_update = False
                if old_settings['timezone'] != self.settings['timezone']:
                    self.min_time = helper_functions.safe_tz_convert(self.min_time, self.settings['timezone'])
                    self.max_time = helper_functions.safe_tz_convert(self.max_time, self.settings['timezone'])
                    self.current_time = helper_functions.safe_tz_convert(self.current_time, self.settings['timezone'])
                    self.date_edit.set_timezone(self.settings['timezone'])
                if old_settings['hold_time'] != self.settings['hold_time'] or old_settings['timezone'] != self.settings['timezone']:
                    self.set_clock()
                    need_update = True
                if old_settings['axis_label_size'] != self.settings['axis_label_size'] or old_settings['axis_tick_size'] != self.settings['axis_tick_size']:
                    self.set_font_sizes()
                    need_update = True
                if need_update:
                    self.canvas.update_axes(self.data, self.axes, self.current_time, self.get_hold_time(), self.settings['timezone'], self.unit_reg, time_updated=False)
                if old_settings['timezone'] != self.settings['timezone'] or old_settings['table_change_time'] != self.settings['table_change_time']:
                    self.update_table()
            if old_settings['gui_theme'] != self.settings['gui_theme'] or old_settings['canvas_theme'] != self.settings['canvas_theme']:
                self.set_theme()
        else:
            helper_functions.print_error('Cannot set settings. {}'.format(err_msg))

    def take_screenshot(self, file_path):
        if not isinstance(file_path, str):
            helper_functions.print_error('Cannot take screenshot. file_path must be of type: str')
        else:
            try:
                p = pathlib.Path(file_path)
                p.exists() # Causes exception if file_path is invalid
                valid = p.parent.exists()
            except:
                valid = False
        if valid:
            if p.suffix.lower() != '.png':
                p = p.parent / (p.name + '.png')
            try:
                self.grab_picture().save(str(p))
            except Exception as error:
                print(error)
        else:
            helper_functions.print_error('Cannot take screenshot. "{}" isn\'t a valid file path.'.format(file_path))

    def toggle_toolbar(self, check_states):
        any_checked = False
        for check_state in check_states:
            if not isinstance(check_states[check_state], (bool, np.bool_)):
                helper_functions.print_error('Cannot toggle toolbar button. {} must be of type: bool'.format(check_state))
                return
            any_checked |= check_states[check_state]

        self.toolbar.setVisible(any_checked)
        if not any_checked:
            return
        action_names, menu_names = ['reset', 'autoscale', 'pan', 'zoom', 'selection', 'display_axis', 'filter_data', 'settings', 'inspect_data', 'screenshot', 'record'], [None, None, None, ['config_axes', 'config_axis_groups', 'config_data', 'config_table_rows']]
        actions = self.toolbar.actions()
        for action in actions:
            if isinstance(action, qtwidgets.QWidgetAction): # Special case for QToolButtons
                config_names = menu_names.pop(0)
                if config_names is None:
                    action.setVisible(check_states[action_names.pop(0)])
                else:
                    config_visible = False
                    for config_action in action.defaultWidget().actions():
                        config_action.setVisible(check_states[config_names.pop(0)])
                        config_visible |= config_action.isVisible()
                    action.setVisible(config_visible)
            elif action.text() != '': # Ignore separators
                action.setVisible(check_states[action_names.pop(0)])

        # Set separator visibility
        actions[2].setVisible(any([check_states[check_state] for check_state in ['reset', 'autoscale']]))
        actions[6].setVisible(any([check_states[check_state] for check_state in ['pan', 'zoom', 'selection']]))
        actions[11].setVisible(any([check_states[check_state] for check_state in ['display_axis', 'config_axes', 'config_axis_groups', 'config_data', 'config_table_rows', 'filter_data', 'settings']]))
        actions[13].setVisible(any([check_states[check_state] for check_state in ['inspect_data']]) and any([check_states[check_state] for check_state in ['screenshot', 'record']]))
