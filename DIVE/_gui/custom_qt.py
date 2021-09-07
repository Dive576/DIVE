from .._utilities import helper_functions
import importlib
import numpy as np
import pandas as pd
import re
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
    import matplotlib.pyplot as plt
except:
    pass

# Create colormap images for ColormapCombo
if 'plt' in globals():
    colormaps = list(set(vpcolor.get_colormaps()) | set(plt.colormaps()))
else:
    colormaps = list(vpcolor.get_colormaps())
colormaps = {colormap: None for colormap in sorted(colormaps)}
for colormap in colormaps:
    color_hex = vpcolor.get_colormap(colormap).colors.hex
    color_pct = np.linspace(0, 100, len(color_hex))
    colormap_str = '<linearGradient id="color" x1="0%" y1="0%" x2="100%" y2="0%">{}</linearGradient>'.format(''.join(['<stop offset="{}%" stop-color="{}" />'.format(color_pct[i], color_hex[i]) for i in range(len(color_hex))]))
    colormaps[colormap] = qtgui.QImage.fromData('<svg width="100" height="15"><defs>{}</defs><rect x="0" y="0" width="100" height="15" fill="url(#color)" /></svg>'.format(colormap_str).encode())
del colormap, color_hex, color_pct, colormap_str

class ColorButton(qtwidgets.QPushButton):
    """
    This class is a QPushButton that allows a color to be selected.
    """
    def __init__(self, color):
        super().__init__()

        self.set_color(color)
        self.clicked.connect(self.pick_color)

    def get_color(self):
        return self.color

    def pick_color(self):
        color = qtwidgets.QColorDialog.getColor(initial=qtgui.QColor(self.color))
        if color.isValid():
            self.set_color(color.name())

    def set_color(self, color):
        self.color = vpcolor.Color(color).hex
        self.setIcon(qtgui.QIcon(qtgui.QPixmap.fromImage(qtgui.QImage.fromData('<svg width="24" height="24"><rect x="0" y="0" width="24" height="24" fill="{}" /></svg>'.format(self.color).encode()))))

class ColormapCombo(qtwidgets.QComboBox):
    """
    This class is a QComboBox that allows a colormap to be selected.
    """
    def __init__(self):
        super().__init__()
        self.setIconSize(qtcore.QSize(100, 25))
        for colormap in colormaps:
            self.addItem(qtgui.QIcon(qtgui.QPixmap.fromImage(colormaps[colormap])), colormap)

class CompactListWidget(qtwidgets.QListWidget):
    def __init__(self):
        super().__init__()
        self.setHorizontalScrollMode(qtwidgets.QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(qtwidgets.QAbstractItemView.ScrollPerPixel)

class CompactListWidgetItem(qtwidgets.QListWidgetItem):
    def __init__(self, text='', parent=None, enable_flags=None, checked=None):
        super().__init__(text, parent)
        if enable_flags is not None:
            flags = self.flags()
            for flag in enable_flags:
                flags |= flag
            self.setFlags(flags)
        if checked is not None:
            self.setCheckState(qtcore.Qt.Checked if checked else qtcore.Qt.Unchecked)

class CompactTableWidget(qtwidgets.QTableWidget):
    def __init__(self, row_count, col_count):
        super().__init__(row_count, col_count)
        self.setWordWrap(False)
        self.setCornerButtonEnabled(False)
        self.setHorizontalScrollMode(self.ScrollPerPixel)
        self.setVerticalScrollMode(self.ScrollPerPixel)

class CompactTreeWidget(qtwidgets.QTreeWidget):
    def __init__(self):
        super().__init__()
        self.header().hide()
        self.header().setSectionResizeMode(qtwidgets.QHeaderView.ResizeToContents)
        self.header().setStretchLastSection(False)
        self.setHorizontalScrollMode(qtwidgets.QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(qtwidgets.QAbstractItemView.ScrollPerPixel)
        self.setUniformRowHeights(True)

class CompactTreeWidgetItem(qtwidgets.QTreeWidgetItem):
    def __init__(self, parent=None, text='', enable_flags=None, disable_flags=None):
        super().__init__(parent, [text])
        if enable_flags is not None or disable_flags is not None:
            flags = self.flags()
            if enable_flags is not None:
                for flag in enable_flags:
                    flags |= flag
            if disable_flags is not None:
                for flag in disable_flags:
                    flags &= ~flag
            self.setFlags(flags)

class FilterTreeWidget(CompactTreeWidget):
    """
    This class is a QTreeWidget that manages value filter groups.
    """
    def __init__(self):
        super().__init__()
        self.setDragDropMode(qtwidgets.QAbstractItemView.InternalMove)
        self.itemCollapsed.connect(lambda item: setattr(item, 'is_expanded', False))
        self.itemExpanded.connect(lambda item: setattr(item, 'is_expanded', True))

    def dropEvent(self, event):
        drop_item = self.itemAt(event.pos())
        drop_pos = self.dropIndicatorPosition()
        if drop_item is None or drop_item.item_type == 'group' or (drop_item.item_type == 'top' and drop_pos in [qtwidgets.QAbstractItemView.AboveItem, qtwidgets.QAbstractItemView.BelowItem]) or (drop_item.item_type == 'filter' and drop_pos == qtwidgets.QAbstractItemView.OnItem):
            event.ignore()
        else:
            drag_item = self.selectedItems()[0]
            super().dropEvent(event)
            self.clearSelection()
            drag_item.setSelected(True)
            self.expand_items(drag_item)

    def add_filter(self, parent, values, is_top=False):
        if is_top:
            top_item = CompactTreeWidgetItem(parent=parent, text=values[0], disable_flags=[qtcore.Qt.ItemIsDragEnabled])
            top_item.item_type = 'top'
            for value in values[1:]:
                self.add_filter(top_item, value)
        else:
            if parent.item_type == 'group':
                parent = parent.child(2)
            elif parent.item_type == 'filter':
                parent = parent.parent()
            if values[0] in ['AND', 'OR']:
                logical_item = CompactTreeWidgetItem(parent=parent, text=values[0])
                logical_item.item_type = 'logical'
                for value in values[1:]:
                    self.add_filter(logical_item, value)
            else:
                if isinstance(values[3], pd.Timestamp) and values[3].tzinfo is not None:
                    value_text = helper_functions.strftime(values[3], include_tz=True)
                else:
                    value_text = str(values[3])
                filter_item = CompactTreeWidgetItem(parent=parent, text='{} {} {} for {}'.format(values[2], values[0], value_text, values[1]), enable_flags=[qtcore.Qt.ItemNeverHasChildren])
                filter_item.item_type = 'filter'
                filter_item.item_values = values

    def add_group(self, values):
        insert_idx = sorted([self.topLevelItem(i).text(0) for i in range(self.topLevelItemCount())] + [values['name']], key=lambda f: helper_functions.natural_order(f)).index(values['name'])
        # Add group item
        group_item = CompactTreeWidgetItem(text=values['name'], enable_flags=[qtcore.Qt.ItemIsUserCheckable], disable_flags=[qtcore.Qt.ItemIsDragEnabled, qtcore.Qt.ItemIsDropEnabled])
        group_item.setCheckState(0, qtcore.Qt.Checked if values['enabled'] else qtcore.Qt.Unchecked)
        group_item.item_type = 'group'
        self.insertTopLevelItem(insert_idx, group_item)
        # Add id item
        id_item = CompactTreeWidgetItem(parent=group_item, text='ID Filter: {}'.format('None' if values['id_filter'] is None else values['id_filter'].title()), enable_flags=[qtcore.Qt.ItemNeverHasChildren], disable_flags=[qtcore.Qt.ItemIsDragEnabled, qtcore.Qt.ItemIsDropEnabled, qtcore.Qt.ItemIsSelectable])
        id_item.item_type = 'id'
        # Add data item
        data_item = CompactTreeWidgetItem(parent=group_item, text='Data To Filter', disable_flags=[qtcore.Qt.ItemIsDragEnabled, qtcore.Qt.ItemIsDropEnabled, qtcore.Qt.ItemIsSelectable])
        data_item.item_type = 'data'
        for data_name in values['data_names']:
            name_item = CompactTreeWidgetItem(parent=data_item, text=data_name, enable_flags=[qtcore.Qt.ItemNeverHasChildren], disable_flags=[qtcore.Qt.ItemIsDragEnabled, qtcore.Qt.ItemIsDropEnabled, qtcore.Qt.ItemIsSelectable])
            name_item.item_type = 'name'
        # Add top, logical, and filter items
        self.add_filter(group_item, values['filters'], is_top=True)

    def edit_filter(self, values=None):
        items = self.selectedItems()
        if len(items) > 0:
            if items[0].item_type == 'group':
                # Edit id item
                items[0].child(0).setText(0, 'ID Filter: {}'.format('None' if values['id_filter'] is None else values['id_filter'].title()))
                # Edit data item
                data_item = items[0].child(1)
                for i in reversed(range(data_item.childCount())):
                    name_item = data_item.child(i)
                    data_item.removeChild(name_item)
                    del name_item
                for data_name in values['data_names']:
                    name_item = CompactTreeWidgetItem(parent=data_item, text=data_name, enable_flags=[qtcore.Qt.ItemNeverHasChildren], disable_flags=[qtcore.Qt.ItemIsDragEnabled, qtcore.Qt.ItemIsDropEnabled, qtcore.Qt.ItemIsSelectable])
                    name_item.item_type = 'name'
                # Expand data item if it was expanded before edit
                self.expand_items(data_item)
            elif items[0].item_type == 'filter':
                if isinstance(values[3], pd.Timestamp) and values[3].tzinfo is not None:
                    items[0].setText(0, '{} {} {} for {}'.format(values[2], values[0], helper_functions.strftime(values[3], include_tz=True), values[1]))
                else:
                    items[0].setText(0, '{} {} {} for {}'.format(values[2], values[0], values[3], values[1]))
                items[0].item_values = values
            elif items[0].item_type in ['top', 'logical']:
                items[0].setText(0, 'OR' if items[0].text(0) == 'AND' else 'AND')

    def expand_items(self, parent):
        item_iter = qtwidgets.QTreeWidgetItemIterator(parent)
        while item_iter.value():
            item = item_iter.value()
            item.setExpanded(getattr(item, 'is_expanded', False))
            item_iter += 1

    def get_groups(self, item=None):
        if item is None:
            return [self.get_groups(self.topLevelItem(i)) for i in range(self.topLevelItemCount())]
        elif item.item_type == 'group':
            id_filter = item.child(0).text(0).split(': ')[1]
            return {'name': item.text(0), 'data_names': self.get_groups(item.child(1)), 'filters': self.get_groups(item.child(2)), 'id_filter': None if id_filter == 'None' else id_filter.lower(), 'enabled': item.checkState(0) == qtcore.Qt.Checked}
        elif item.item_type == 'data':
            return [item.child(i).text(0) for i in range(item.childCount())]
        elif item.item_type in ['top', 'logical']:
            return [item.text(0)] + [self.get_groups(item.child(i)) for i in range(item.childCount())]
        return item.item_values

    def remove_filter(self):
        items = self.selectedItems()
        if len(items) > 0:
            if items[0].item_type == 'group':
                self.invisibleRootItem().removeChild(items[0])
                del items[0]
            elif items[0].item_type == 'top':
                text = items[0].text(0)
                group_item = items[0].parent()
                group_item.removeChild(items[0])
                del items[0]
                self.add_filter(group_item, [text], is_top=True)
                group_item.child(2).setSelected(True)
            else:
                items[0].parent().removeChild(items[0])
                del items[0]

class LargeListModel(qtcore.QAbstractListModel):
    """
    This class is a QAbstractListModel that supports checkable items.
    """
    def __init__(self):
        super().__init__()
        self.values = []
        self.checked = None

    def change_data(self, values, checked):
        self.beginResetModel()
        self.values = values
        self.checked = checked
        self.endResetModel()

    def data(self, index, role):
        if index.isValid():
            if role == qtcore.Qt.CheckStateRole:
                if self.checked is not None:
                    return qtcore.Qt.Checked if self.checked[index.row()] else qtcore.Qt.Unchecked
            elif role == qtcore.Qt.DisplayRole:
                return str(self.values[index.row()])
        return None

    def flags(self, index):
        f = super().flags(index)
        if index.isValid() and self.checked is not None:
            return f | qtcore.Qt.ItemIsUserCheckable
        return f

    def get_checked(self):
        return self.checked

    def rowCount(self, parent):
        return len(self.values)

    def set_checked(self, state):
        if self.checked is not None:
            self.beginResetModel()
            self.checked[:] = state
            self.endResetModel()

    def setData(self, index, value, role):
        if index.isValid() and role == qtcore.Qt.CheckStateRole and self.checked is not None:
            self.checked[index.row()] = value == qtcore.Qt.Checked
            return True
        return False

class LargeListView(qtwidgets.QListView):
    """
    This class is a QListView that supports checkable items.
    """
    def __init__(self):
        super().__init__()
        self.setUniformItemSizes(True)
        self.setHorizontalScrollMode(qtwidgets.QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(qtwidgets.QAbstractItemView.ScrollPerPixel)
        self.setModel(LargeListModel())

    def change_data(self, values, checked):
        self.model().change_data(values, checked)

    def get_checked(self):
        return self.model().get_checked()

    def set_checked(self, state):
        self.model().set_checked(state)

class PandasTableModel(qtcore.QAbstractTableModel):
    """
    This class is a QAbstractTableModel that supports pandas.DataFrames.
    """
    def __init__(self, data_frame, timezone, **kwargs):
        super().__init__(**kwargs)
        self.data_frame = data_frame
        self.timezone = timezone
        self.filtered_idx = None
        self.check_state = None
        self.check_col_offset = 0
        self.sort_col = -1
        self.sort_order = qtcore.Qt.AscendingOrder
        self.sort_idx = None
        self.sort_filtered_idx = None

    def change_data(self, data_frame, filtered_idx, check_state):
        self.beginResetModel()
        self.data_frame = data_frame
        self.filtered_idx = filtered_idx
        self.check_state = check_state
        self.check_col_offset = 0 if self.check_state is None else 1
        self.sort_col = -1
        self.sort_order = qtcore.Qt.AscendingOrder
        self.sort_idx = np.arange(self.data_frame.shape[0])
        self.update_sort_filter_indices()
        self.endResetModel()

    def columnCount(self, parent=None):
        return self.data_frame.shape[1] + self.check_col_offset

    def data(self, index, role):
        if index.isValid():
            if self.check_state is not None and index.column() == 0:
                if role == qtcore.Qt.CheckStateRole:
                    return qtcore.Qt.Checked if self.check_state[self.sort_filtered_idx[index.row()]] else qtcore.Qt.Unchecked
            elif role == qtcore.Qt.DisplayRole:
                col = index.column() - self.check_col_offset
                value = self.data_frame.iat[self.sort_filtered_idx[index.row()], col]
                if pd.api.types.is_datetime64tz_dtype(self.data_frame.dtypes.iat[col]):
                    return helper_functions.strftime(helper_functions.safe_tz_convert(value, self.timezone), include_tz=True)
                return str(value)
        return None

    def flags(self, index):
        if self.check_state is not None and index.column() == 0:
            return super().flags(index) | qtcore.Qt.ItemIsUserCheckable | qtcore.Qt.ItemIsEnabled
        return super().flags(index)

    def headerData(self, idx, orientation, role=qtcore.Qt.DisplayRole):
        if role == qtcore.Qt.DisplayRole:
            if orientation == qtcore.Qt.Horizontal:
                return '' if self.check_state is not None and idx == 0 else str(self.data_frame.columns[idx - self.check_col_offset])
            elif orientation == qtcore.Qt.Vertical:
                return str(self.sort_filtered_idx[idx] + 1)
        return super().headerData(idx, orientation, role)

    def rowCount(self, parent=None):
        return self.data_frame.shape[0] if self.filtered_idx is None else self.filtered_idx.sum()

    def set_checked(self, state):
        if self.check_state is not None:
            self.beginResetModel()
            self.check_state[slice(None) if self.filtered_idx is None else self.filtered_idx] = state
            self.endResetModel()

    def setData(self, index, value, role):
        if self.check_state is not None and index.column() == 0:
            self.check_state[self.sort_filtered_idx[index.row()]] = value == qtcore.Qt.Checked
            return True
        return super().setData(index, value, role)

    def sort(self, col, order):
        if self.data_frame.shape[0] > 0 and not (self.check_state is not None and col == 0):
            self.layoutAboutToBeChanged.emit()
            col -= self.check_col_offset if col != -1 else 0
            if col == -1: # No column to be sorted
                self.sort_col = col
                self.sort_order = qtcore.Qt.AscendingOrder
                self.sort_idx = np.arange(self.data_frame.shape[0])
            elif col != self.sort_col: # Sort column has changed
                self.sort_col = col
                self.sort_order = qtcore.Qt.AscendingOrder
                column_data = self.data_frame.iloc[:, col].reset_index(drop=True)
                if pd.api.types.is_numeric_dtype(column_data) or pd.api.types.is_datetime64tz_dtype(column_data):
                    column_data.sort_values(inplace=True, kind='mergesort')
                else:
                    column_data = column_data.astype('str')
                    column_data.sort_values(inplace=True, kind='mergesort', key=lambda s: s.map(helper_functions.natural_order))
                self.sort_idx = column_data.index.to_numpy()
            if order != self.sort_order: # Change from ascending order to descending order or vice versa
                self.sort_order = order
                self.sort_idx = self.sort_idx[::-1]
            self.update_sort_filter_indices()
            self.layoutChanged.emit()

    def update_filter(self, filtered_idx):
        self.beginResetModel()
        self.filtered_idx = filtered_idx
        self.update_sort_filter_indices()
        self.endResetModel()

    def update_sort_filter_indices(self):
        self.sort_filtered_idx = self.sort_idx if self.filtered_idx is None else self.sort_idx[self.filtered_idx[self.sort_idx]]

class PandasTableView(qtwidgets.QTableView):
    """
    This class is a QTableView that supports pandas.DataFrames.
    """
    def __init__(self, timezone, **kwargs):
        super().__init__(**kwargs)
        self.selected_idx = (-1, -1)
        self.setWordWrap(False)
        self.setCornerButtonEnabled(False)
        self.setSelectionMode(self.SingleSelection)
        self.setHorizontalScrollMode(qtwidgets.QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(qtwidgets.QAbstractItemView.ScrollPerPixel)
        self.setModel(PandasTableModel(pd.DataFrame(), timezone))
        self.model().layoutAboutToBeChanged.connect(lambda: setattr(self, 'selected_idx', self.get_selection()))
        self.model().layoutChanged.connect(lambda: self.set_selection(self.selected_idx))
        self.setSortingEnabled(True)
        self.horizontalHeader().setSortIndicator(-1, qtcore.Qt.AscendingOrder)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().sectionClicked.connect(self.block_sort)

    def block_sort(self, col):
        """
        Set the horizontal header's sort indicator back to its original position if the check column is clicked.
        """
        if self.model().check_state is not None and col == 0:
            orig_col = self.model().sort_col
            self.horizontalHeader().setSortIndicator(-1 if orig_col == -1 else orig_col + 1, self.model().sort_order)
    
    def change_data(self, data_frame, filtered_idx, check_state, table_state):
        self.blockSignals(True)
        self.model().change_data(pd.DataFrame(), None, None)
        self.horizontalHeader().reset()
        self.horizontalHeader().setSortIndicator(-1, qtcore.Qt.AscendingOrder)
        self.model().change_data(data_frame, filtered_idx, check_state)
        if check_state is not None:
            self.setColumnWidth(0, 1)
            self.horizontalHeader().setSectionResizeMode(0, qtwidgets.QHeaderView.Fixed)
            self.horizontalHeader().setFirstSectionMovable(False)
        if table_state is not None:
            self.horizontalHeader().restoreState(table_state[0])
            self.set_selection(table_state[1])
        self.blockSignals(False)

    def get_selection(self):
        sorted_idx = self.model().sort_filtered_idx
        return (sorted_idx[self.currentIndex().row()], self.currentIndex().column()) if len(sorted_idx) > 0 else (-1, -1)

    def set_checked(self, state):
        self.model().set_checked(state)

    def set_selection(self, selected_idx):
        sorted_idx = self.model().sort_filtered_idx
        row_idx = np.argwhere(sorted_idx == selected_idx[0])
        if len(row_idx) > 0:
            current_idx = self.model().index(row_idx[0][0], selected_idx[1])
            self.setCurrentIndex(current_idx)
            self.scrollTo(current_idx)
    
    def update_filter(self, filtered_idx):
        selected_idx = self.get_selection()
        self.model().update_filter(filtered_idx)
        self.set_selection(selected_idx)

class SliderStyle(qtwidgets.QProxyStyle):
    """
    This class is a style that allows a QSlider to jump to any position on the slider that is clicked.
    """
    def styleHint(self, hint, option=0, widget=0, returnData=0):
        if hint == qtwidgets.QStyle.SH_Slider_AbsoluteSetButtons:
            return qtcore.Qt.LeftButton | qtcore.Qt.MidButton | qtcore.Qt.RightButton
        return super().styleHint(hint, option, widget, returnData)

class TimeEdit(qtwidgets.QAbstractSpinBox):
    """
    This class is a QSpinBox that supports floats and pandas.Timestamps with tz.
    """
    returnPressed = qtcore.pyqtSignal(int) if hasattr(qtcore, 'pyqtSignal') else qtcore.Signal(int)

    def __init__(self):
        super().__init__()
        self.min_time = None
        self.max_time = None
        self.current_time = None
        self.is_timestamp = None
        self.time_regex = None
        self.hint_size = 0

    def get_time(self):
        return self.current_time

    def keyPressEvent(self, event):
        if event.key() == qtcore.Qt.Key_Return:
            try:
                value = pd.Timestamp(self.text(), tz=self.current_time.tzinfo) if self.is_timestamp else float(self.text())
            except:
                pass
            else:
                self.current_time = np.clip(value, self.min_time, self.max_time)
                self.returnPressed.emit(event.key())
        else:
            super().keyPressEvent(event)

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        hint.setWidth(hint.width() + self.hint_size)
        return hint

    def set_limits(self, min_time, max_time):
        self.min_time = min_time
        self.max_time = max_time
        if self.current_time is None or isinstance(self.current_time, pd.Timestamp) != isinstance(self.min_time, pd.Timestamp):
            self.current_time = min_time
        self.current_time = np.clip(self.current_time, self.min_time, self.max_time)
        if isinstance(self.current_time, pd.Timestamp):
            self.current_time = helper_functions.safe_tz_convert(self.current_time, self.min_time.tzinfo)
            self.is_timestamp = True
            self.time_regex = r'^(0?\d|1[012])?/([012]?\d|3[01])?/(\d+)? ([01]?\d|2[0-3])?:([0-5]?\d)?:([0-5]?\d)?(\.\d*)?$'
        else:
            self.is_timestamp = False
            self.time_regex = r'^\d*(\.\d*)?$'
        self.hint_size = qtgui.QFontMetrics(self.font()).horizontalAdvance(helper_functions.strftime(self.max_time)) + 2
        self.lineEdit().setText(helper_functions.strftime(self.current_time))

    def set_time(self, value):
        current_pos = self.lineEdit().cursorPosition()
        self.current_time = np.clip(value, self.min_time, self.max_time)
        if isinstance(self.min_time, pd.Timestamp):
            self.current_time = helper_functions.safe_tz_convert(self.current_time, str(self.min_time.tzinfo))
        self.lineEdit().setText(helper_functions.strftime(self.current_time))
        self.lineEdit().setCursorPosition(current_pos)

    def set_timezone(self, timezone):
        if isinstance(self.min_time, pd.Timestamp):
            current_pos = self.lineEdit().cursorPosition()
            self.min_time = helper_functions.safe_tz_convert(self.min_time, timezone)
            self.max_time = helper_functions.safe_tz_convert(self.max_time, timezone)
            self.current_time = helper_functions.safe_tz_convert(self.current_time, timezone)
            self.lineEdit().setText(helper_functions.strftime(self.current_time))
            self.lineEdit().setCursorPosition(current_pos)

    def stepBy(self, steps):
        current_pos = self.lineEdit().cursorPosition()
        text = self.text()
        section_text = text[:current_pos]
        section_idx = section_text.count('/') + section_text.count(':') + section_text.count(' ') + section_text.count('.')
        if self.is_timestamp:
            sections = ['months', 'days', 'years', 'hours', 'minutes', 'seconds', 'microseconds']
            try:
                self.current_time += pd.DateOffset(**{sections[section_idx]: steps})
            except:
                pass
        else:
            self.current_time = self.current_time + steps if section_idx == 0 else (self.current_time * 1e6 + steps) / 1e6
        self.current_time = np.clip(self.current_time, self.min_time, self.max_time)
        self.lineEdit().setText(helper_functions.strftime(self.current_time))
        self.lineEdit().setCursorPosition(current_pos)

    def stepEnabled(self):
        return self.StepUpEnabled | self.StepDownEnabled
    
    def validate(self, text, pos):
        if re.match(self.time_regex, text) is None:
            return (qtgui.QValidator.Invalid, text, pos)
        else:
            try:
                value = pd.Timestamp(text, tz=self.current_time.tzinfo) if self.is_timestamp else float(text)
            except:
                pass
            else:
                self.current_time = value
        return (qtgui.QValidator.Acceptable, text, pos)