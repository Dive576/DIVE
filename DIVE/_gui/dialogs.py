from . import configure_widgets, custom_qt
from .._components import dive_axis, dive_axis_group, dive_filters, dive_table_row
from .._utilities import helper_functions
import importlib
import numpy as np
import pandas as pd
import pytz
import vispy.app as vpapp
qt = vpapp.use_app().backend_name
try:
    qtcore = importlib.import_module('{}.QtCore'.format(qt))
    qtwidgets = importlib.import_module('{}.QtWidgets'.format(qt))
except:
    pass
del qt

class ConfigureAxesArtistsDialog(qtwidgets.QDialog):
    """
    This class is a dialog used to add/edit/remove
    axes and artists in DIVE.
    """
    def __init__(self, data_objs, axes, artists, unit_reg, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle('Configure Axes/Artists')
        self.setWindowFlags(self.windowFlags() & ~qtcore.Qt.WindowContextHelpButtonHint | qtcore.Qt.WindowMaximizeButtonHint)
        self.resize(800, 600)
        self.setLayout(qtwidgets.QVBoxLayout())

        self.data_objs = data_objs
        self.unit_reg = unit_reg
        self.current_widget = None
        self.removed_names = []
        self.results = {}

        hbox = qtwidgets.QHBoxLayout()
        self.layout().addLayout(hbox)

        group = qtwidgets.QGroupBox('Axes/Artists')
        group.setLayout(qtwidgets.QVBoxLayout())
        hbox.addWidget(group, 0)
        button_hbox = qtwidgets.QHBoxLayout()
        group.layout().addLayout(button_hbox)
        add_axis_btn = qtwidgets.QPushButton('Add Axis')
        add_axis_btn.clicked.connect(self.add_axis)
        button_hbox.addWidget(add_axis_btn)
        add_artist_btn = qtwidgets.QPushButton('Add Artist')
        add_artist_btn.clicked.connect(self.add_artist)
        button_hbox.addWidget(add_artist_btn)
        remove_btn = qtwidgets.QPushButton('Remove')
        remove_btn.clicked.connect(self.remove_item)
        button_hbox.addWidget(remove_btn)
        self.axes = custom_qt.CompactTreeWidget()
        self.axes.currentItemChanged.connect(self.change_widget)
        group.layout().addWidget(self.axes)
        for axis in axes:
            branch = custom_qt.CompactTreeWidgetItem(parent=self.axes, text=axis['name'])
            branch.axis_values = axis
            branch.was_input = None
            for artist in artists[axis['name']]:
                item = custom_qt.CompactTreeWidgetItem(parent=branch, text=artist['name'], enable_flags=[qtcore.Qt.ItemNeverHasChildren])
                item.artist_values = artist
            branch.setExpanded(True)

        self.widget_group = qtwidgets.QGroupBox('')
        self.widget_group.setLayout(qtwidgets.QVBoxLayout())
        hbox.addWidget(self.widget_group, 1)
        self.scroll_area = qtwidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.widget_group.layout().addWidget(self.scroll_area)

        buttons = qtwidgets.QDialogButtonBox(qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_input)
        buttons.rejected.connect(self.reject)
        self.layout().addWidget(buttons)

    def add_artist(self):
        branch = self.axes.currentItem()
        if branch is not None:
            if hasattr(branch, 'artist_values'):
                branch = branch.parent()
            artist_names = [branch.child(i).text(0) for i in range(branch.childCount())]
            name, artist_type, ok = InputAxisDialog.get_info(self, artist_names, False)
            if ok:
                insert_idx = sorted(artist_names + [name], key=helper_functions.natural_order).index(name)
                item = custom_qt.CompactTreeWidgetItem(text=name, enable_flags=[qtcore.Qt.ItemNeverHasChildren])
                item.artist_values = {'name': name, 'artist_type': artist_type, **configure_widgets.get_artist_defaults(artist_type)}
                branch.insertChild(insert_idx, item)

    def add_axis(self):
        axis_names = [self.axes.topLevelItem(i).text(0) for i in range(self.axes.topLevelItemCount())]
        name, axis_type, ok = InputAxisDialog.get_info(self, axis_names, True)
        if ok:
            insert_idx = sorted(axis_names + [name], key=helper_functions.natural_order).index(name)
            item = custom_qt.CompactTreeWidgetItem(text=name)
            item.axis_values = {'name': name, 'axis_type': axis_type, **configure_widgets.AxisWidget.get_default_values()}
            self.axes.insertTopLevelItem(insert_idx, item)

    def change_widget(self, current, previous):
        self.update_widget(previous)
        if self.current_widget is not None:
            self.scroll_area.takeWidget()
            self.current_widget.deleteLater()
            self.current_widget = None
            self.widget_group.setTitle('')
        if current is not None:
            if hasattr(current, 'axis_values'):
                self.current_widget = configure_widgets.AxisWidget(current.axis_values)
                self.widget_group.setTitle('{} Axis'.format(current.axis_values['axis_type'].title()))
            else:
                self.current_widget = configure_widgets.create_artist_widget(self.data_objs, current.parent().axis_values['axis_type'], current.artist_values)
                self.widget_group.setTitle('{} Artist'.format(current.artist_values['artist_type'].title()))
            self.scroll_area.setWidget(self.current_widget)

    def remove_item(self):
        item = self.axes.currentItem()
        if item is not None:
            if hasattr(item, 'axis_values'):
                axis_name = item.text(0)
                self.axes.invisibleRootItem().removeChild(item)
                if hasattr(item, 'was_input'):
                    self.removed_names.append(axis_name)
            else:
                axis_name = item.parent().text(0)
                item.parent().removeChild(item)
            del item

    def update_widget(self, item):
        if item is not None:
            if isinstance(self.current_widget, configure_widgets.AxisWidget):
                item.axis_values = self.current_widget.get_values()
                item.axis_values['name'] = item.text(0)
            else:
                item.artist_values = self.current_widget.get_values()
                item.artist_values['name'] = item.text(0)

    def validate_input(self):
        self.results = {}
        self.update_widget(self.axes.currentItem())
        for iAxis in range(self.axes.topLevelItemCount()):
            branch = self.axes.topLevelItem(iAxis)
            axis_name = branch.axis_values['name']
            axis_obj = dive_axis.DIVEAxis()
            err_msg = axis_obj.set_state([], self.unit_reg, branch.axis_values)
            if err_msg is None:
                self.results[axis_name] = axis_obj
            else:
                qtwidgets.QMessageBox.critical(self, 'Error', 'Invalid input for axis "{}". {}'.format(axis_name, err_msg))
                return
            for iArtist in range(branch.childCount()):
                item = branch.child(iArtist)
                artist_type = item.artist_values['artist_type']
                err_msg = self.results[axis_name].add_artist(self.data_objs, artist_type, self.unit_reg, item.artist_values)
                if err_msg is not None:
                    qtwidgets.QMessageBox.critical(self, 'Error', 'Invalid input for {} artist "{}" in axis "{}". {}'.format(artist_type, item.artist_values['name'], axis_name, err_msg))
                    return
        self.accept()

    @staticmethod
    def get_axes_artists(parent, data_objs, axes, artists, unit_reg):
        dialog = ConfigureAxesArtistsDialog(data_objs, axes, artists, unit_reg, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        results, removed_names = dialog.results, dialog.removed_names
        dialog.deleteLater()
        return results, removed_names, status

class ConfigureAxisGroupsDialog(qtwidgets.QDialog):
    """
    This class is a dialog used to add/edit/remove
    axis groups in DIVE.
    """
    def __init__(self, axis_objs, axis_groups, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle('Configure Axis Groups')
        self.setWindowFlags(self.windowFlags() & ~qtcore.Qt.WindowContextHelpButtonHint | qtcore.Qt.WindowMaximizeButtonHint)
        self.resize(800, 600)
        self.setLayout(qtwidgets.QVBoxLayout())

        self.axis_objs = axis_objs
        self.removed_names = []

        hbox = qtwidgets.QHBoxLayout()
        self.layout().addLayout(hbox)

        group_vbox = qtwidgets.QVBoxLayout()
        hbox.addLayout(group_vbox, 0)
        axis_hbox = qtwidgets.QHBoxLayout()
        axis_hbox.addWidget(qtwidgets.QLabel('Axis:'), 0)
        group_vbox.addLayout(axis_hbox)
        self.axis = qtwidgets.QComboBox()
        self.axis.addItems(list(self.axis_objs))
        axis_hbox.addWidget(self.axis, 1)
        group = qtwidgets.QGroupBox('Axis Groups')
        group.setLayout(qtwidgets.QVBoxLayout())
        group_vbox.addWidget(group)
        button_hbox = qtwidgets.QHBoxLayout()
        group.layout().addLayout(button_hbox)
        add_btn = qtwidgets.QPushButton('Add')
        add_btn.clicked.connect(self.add_group)
        button_hbox.addWidget(add_btn)
        remove_btn = qtwidgets.QPushButton('Remove')
        remove_btn.clicked.connect(self.remove_group)
        button_hbox.addWidget(remove_btn)
        self.axis_groups = custom_qt.CompactListWidget()
        self.axis_groups.currentItemChanged.connect(self.change_group)
        group.layout().addWidget(self.axis_groups)
        for axis_group in axis_groups:
            item = custom_qt.CompactListWidgetItem(text=axis_group['name'], parent=self.axis_groups)
            item.axis_group_values = axis_group
            item.was_input = None

        self.group_widget = qtwidgets.QWidget()
        self.group_widget.setLayout(qtwidgets.QHBoxLayout())
        sp = self.group_widget.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.group_widget.setSizePolicy(sp)
        self.group_widget.setVisible(False)
        hbox.addWidget(self.group_widget, 1)

        grid_group = qtwidgets.QGroupBox('Axis Group Layout')
        grid_group.setLayout(qtwidgets.QVBoxLayout())
        self.group_widget.layout().addWidget(grid_group)
        options_hbox = qtwidgets.QHBoxLayout()
        grid_group.layout().addLayout(options_hbox)
        options_hbox.addWidget(qtwidgets.QLabel('Row Count:'), 0)
        self.row_count = qtwidgets.QSpinBox()
        self.row_count.setRange(1, 20)
        self.row_count.editingFinished.connect(lambda: self.grid_table.setRowCount(self.row_count.value()))
        options_hbox.addWidget(self.row_count, 1)
        options_hbox.addWidget(qtwidgets.QLabel('Column Count:'), 0)
        self.column_count = qtwidgets.QSpinBox()
        self.column_count.setRange(1, 20)
        self.column_count.editingFinished.connect(lambda: self.grid_table.setColumnCount(self.column_count.value()))
        options_hbox.addWidget(self.column_count, 1)
        merge_btn = qtwidgets.QPushButton('Merge')
        merge_btn.clicked.connect(self.grid_merge)
        options_hbox.addWidget(merge_btn, 1)
        split_btn = qtwidgets.QPushButton('Split')
        split_btn.clicked.connect(self.grid_split)
        options_hbox.addWidget(split_btn, 1)
        insert_btn = qtwidgets.QPushButton('Insert Axis')
        insert_btn.clicked.connect(self.grid_insert)
        options_hbox.addWidget(insert_btn, 1)
        remove_btn = qtwidgets.QPushButton('Remove Axis')
        remove_btn.clicked.connect(self.grid_remove)
        options_hbox.addWidget(remove_btn, 1)
        self.grid_table = custom_qt.CompactTableWidget(1, 1)
        self.grid_table.setEditTriggers(qtwidgets.QAbstractItemView.NoEditTriggers)
        self.grid_table.setSelectionMode(qtwidgets.QAbstractItemView.ContiguousSelection)
        grid_group.layout().addWidget(self.grid_table)

        buttons = qtwidgets.QDialogButtonBox(qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout().addWidget(buttons)

    def add_group(self):
        group_names = [self.axis_groups.item(row).text() for row in range(self.axis_groups.count())]
        name, ok = InputNameDialog.get_name(self, group_names)
        if ok:
            insert_row = sorted(group_names + [name], key=helper_functions.natural_order).index(name)
            item = custom_qt.CompactListWidgetItem(text=name)
            item.axis_group_values = {'name': name, 'row_count': 1, 'column_count': 1, 'axis_names': [], 'rows': [], 'columns': [], 'row_spans': [], 'column_spans': []}
            self.axis_groups.insertItem(insert_row, item)

    def change_group(self, current, previous):
        self.update_group(previous)
        if current is None:
            self.group_widget.setVisible(False)
        else:
            axis_group = current.axis_group_values
            self.row_count.setValue(axis_group['row_count'])
            self.column_count.setValue(axis_group['column_count'])
            self.grid_table.clear()
            self.grid_table.setRowCount(0)
            self.grid_table.setRowCount(axis_group['row_count'])
            self.grid_table.setColumnCount(axis_group['column_count'])
            for i in range(len(axis_group['axis_names'])):
                self.grid_table.setItem(axis_group['rows'][i], axis_group['columns'][i], qtwidgets.QTableWidgetItem(axis_group['axis_names'][i]))
                if not (axis_group['row_spans'][i] == 1 and axis_group['column_spans'][i] == 1):
                    self.grid_table.setSpan(axis_group['rows'][i], axis_group['columns'][i], axis_group['row_spans'][i], axis_group['column_spans'][i])
            self.group_widget.setVisible(True)

    def grid_insert(self):
        if self.axis.count() > 0:
            name = self.axis.currentText()
            for index in self.grid_table.selectedIndexes():
                row, col = index.row(), index.column()
                item = self.grid_table.item(row, col)
                if item is None:
                    item = qtwidgets.QTableWidgetItem()
                    self.grid_table.setItem(row, col, item)
                item.setText(name)

    def grid_merge(self):
        rows, cols = [], []
        self.grid_split()
        for index in self.grid_table.selectedIndexes():
            rows.append(index.row())
            cols.append(index.column())
        if len(rows) > 0:
            min_row, min_col = np.min(rows), np.min(cols)
            row_span, col_span = np.max(rows) - min_row + 1, np.max(cols) - min_col + 1
            if not (row_span == 1 and col_span == 1):
                for i in range(len(rows)):
                    row, col = rows[i], cols[i]
                    if not (row == min_row and col == min_col):
                        item = self.grid_table.item(row, col)
                        if item is not None:
                            self.grid_table.takeItem(row, col)
                            del item
                self.grid_table.setSpan(min_row, min_col, row_span, col_span)

    def grid_remove(self):
        for index in self.grid_table.selectedIndexes():
            item = self.grid_table.takeItem(index.row(), index.column())
            del item

    def grid_split(self):
        for index in self.grid_table.selectedIndexes():
            row, col = index.row(), index.column()
            if not (self.grid_table.rowSpan(row, col) == 1 and self.grid_table.columnSpan(row, col) == 1):
                self.grid_table.setSpan(row, col, 1, 1)

    def remove_group(self):
        indexes = self.axis_groups.selectedIndexes()
        if len(indexes) > 0:
            item = self.axis_groups.takeItem(indexes[0].row())
            if hasattr(item, 'was_input'):
                self.removed_names.append(item.text())
            del item

    def update_group(self, group_item):
        if group_item is not None:
            group = group_item.axis_group_values
            group['row_count'] = self.row_count.value()
            group['column_count'] = self.column_count.value()
            group['axis_names'], group['rows'], group['columns'], group['row_spans'], group['column_spans'] = [], [], [], [], []
            for row in range(self.grid_table.rowCount()):
                for col in range(self.grid_table.columnCount()):
                    item = self.grid_table.item(row, col)
                    if item is not None:
                        group['axis_names'].append(item.text())
                        group['rows'].append(row)
                        group['columns'].append(col)
                        group['row_spans'].append(self.grid_table.rowSpan(row, col))
                        group['column_spans'].append(self.grid_table.columnSpan(row, col))

    def get_results(self, status):
        self.update_group(self.axis_groups.currentItem())
        axis_groups = {}
        if status:
            for row in range(self.axis_groups.count()):
                axis_group = self.axis_groups.item(row).axis_group_values
                name = axis_group['name']
                axis_group_obj = dive_axis_group.DIVEAxisGroup()
                axis_group_obj.set_state(self.axis_objs, [], axis_group)
                axis_groups[name] = axis_group_obj
        return axis_groups, self.removed_names

    @staticmethod
    def get_axis_groups(parent, axis_names, axis_groups):
        dialog = ConfigureAxisGroupsDialog(axis_names, axis_groups, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        results = dialog.get_results(status)
        dialog.deleteLater()
        return (*results, status)

class ConfigureTableRowsDialog(qtwidgets.QDialog):
    """
    This class is a dialog used to add/edit/remove
    table rows in DIVE.
    """
    def __init__(self, data_objs, table_rows, timezone, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle('Configure Table Rows')
        self.setWindowFlags(self.windowFlags() & ~qtcore.Qt.WindowContextHelpButtonHint | qtcore.Qt.WindowMaximizeButtonHint)
        self.resize(800, 600)
        self.setLayout(qtwidgets.QVBoxLayout())

        self.data_objs = data_objs
        self.timezone = timezone
        self.current_criteria = None
        self.results = []

        row_group = qtwidgets.QGroupBox('Table Rows')
        row_group.setLayout(qtwidgets.QVBoxLayout())
        self.layout().addWidget(row_group)
        button_hbox = qtwidgets.QHBoxLayout()
        row_group.layout().addLayout(button_hbox)
        add_btn = qtwidgets.QPushButton('Add')
        add_btn.clicked.connect(lambda: self.add_row())
        button_hbox.addWidget(add_btn)
        remove_btn = qtwidgets.QPushButton('Remove')
        remove_btn.clicked.connect(self.remove_row)
        button_hbox.addWidget(remove_btn)
        move_up_btn = qtwidgets.QPushButton('Move Up')
        move_up_btn.clicked.connect(lambda: self.move_row(False))
        button_hbox.addWidget(move_up_btn)
        move_down_btn = qtwidgets.QPushButton('Move Down')
        move_down_btn.clicked.connect(lambda: self.move_row(True))
        button_hbox.addWidget(move_down_btn)
        self.row_table = custom_qt.CompactTableWidget(0, 5)
        self.row_table.setSelectionMode(qtwidgets.QTableWidget.SingleSelection)
        self.row_table.setHorizontalHeaderLabels(['Data Name', 'Field Name', 'Label', 'Operation', 'Blend Colors'])
        self.row_table.itemSelectionChanged.connect(self.set_criteria)
        row_group.layout().addWidget(self.row_table)

        criteria_group = qtwidgets.QGroupBox('Color Criteria')
        criteria_group.setLayout(qtwidgets.QVBoxLayout())
        self.layout().addWidget(criteria_group)
        button_hbox = qtwidgets.QHBoxLayout()
        criteria_group.layout().addLayout(button_hbox)
        add_btn = qtwidgets.QPushButton('Add')
        add_btn.clicked.connect(lambda: self.add_criteria())
        button_hbox.addWidget(add_btn)
        edit_btn = qtwidgets.QPushButton('Edit')
        edit_btn.clicked.connect(self.edit_criteria)
        button_hbox.addWidget(edit_btn)
        remove_btn = qtwidgets.QPushButton('Remove')
        remove_btn.clicked.connect(self.remove_criteria)
        button_hbox.addWidget(remove_btn)
        move_up_btn = qtwidgets.QPushButton('Move Up')
        move_up_btn.clicked.connect(lambda: self.move_criteria(False))
        button_hbox.addWidget(move_up_btn)
        move_down_btn = qtwidgets.QPushButton('Move Down')
        move_down_btn.clicked.connect(lambda: self.move_criteria(True))
        button_hbox.addWidget(move_down_btn)
        self.criteria_table = custom_qt.CompactTableWidget(0, 3)
        self.criteria_table.setSelectionMode(qtwidgets.QTableWidget.SingleSelection)
        self.criteria_table.setHorizontalHeaderLabels(['Comparison', 'Value', 'Color'])
        criteria_group.layout().addWidget(self.criteria_table)

        buttons = qtwidgets.QDialogButtonBox(qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_input)
        buttons.rejected.connect(self.reject)
        self.layout().addWidget(buttons)

        for table_row in table_rows:
            self.add_row([table_row['data_name'], table_row['field_name'], table_row['label'], table_row['operation'], table_row['blend_colors'], table_row['index'], table_row['color_criteria']])

    def add_criteria(self, criteria_info=None):
        criteria_info = ['>', '', '#7f7f7f', self.criteria_table.rowCount()] if criteria_info is None else criteria_info
        indexes = self.row_table.selectedIndexes()
        if len(indexes) > 0:
            row = criteria_info[3]
            self.current_criteria.insert(row, criteria_info[:3])
            self.criteria_table.insertRow(row)
            combo = qtwidgets.QComboBox()
            combo.addItems(['>', '>=', '==', '!=', '<=', '<', 'change'])
            combo.setCurrentIndex(combo.findText(criteria_info[0]))
            self.criteria_table.setCellWidget(row, 0, combo)
            value = criteria_info[1]
            value_str = helper_functions.strftime(helper_functions.safe_tz_convert(value, self.timezone), include_tz=True) if isinstance(value, pd.Timestamp) and value.tzinfo is not None else str(value)
            item = qtwidgets.QTableWidgetItem(value_str)
            item.criteria_value = value
            item.setFlags(item.flags() & ~qtcore.Qt.ItemIsEditable)
            self.criteria_table.setItem(row, 1, item)
            self.criteria_table.setCellWidget(row, 2, custom_qt.ColorButton(criteria_info[2]))
        else:
            qtwidgets.QMessageBox.critical(self, 'Error', 'A table row must be selected.')

    def add_row(self, row_info=None):
        row_info = [None, None, '', '', False, self.row_table.rowCount(), []] if row_info is None else row_info
        row = row_info[5]
        self.row_table.insertRow(row)
        for col in range(5):
            if col == 0:
                data_combo = qtwidgets.QComboBox()
                self.row_table.setCellWidget(row, col, data_combo)
            elif col == 1:
                fields_combo = qtwidgets.QComboBox()
                self.row_table.setCellWidget(row, col, fields_combo)
            elif col == 4:
                item = qtwidgets.QWidget()
                item.setLayout(qtwidgets.QHBoxLayout())
                item.layout().setAlignment(qtcore.Qt.AlignCenter)
                item.layout().setContentsMargins(0, 0, 0, 0)
                self.row_table.setCellWidget(row, col, item)
                check = qtwidgets.QCheckBox()
                check.setChecked(row_info[4])
                item.layout().addWidget(check)
            else:
                self.row_table.setItem(row, col, qtwidgets.QTableWidgetItem(row_info[col]))
        self.row_table.item(row, 2).color_criteria = row_info[6]
        data_combo.currentTextChanged.connect(lambda text: self.set_fields(fields_combo, text))
        data_combo.addItems(list(self.data_objs))
        data_combo.setCurrentIndex(max(0, data_combo.findText(row_info[0])))
        fields_combo.setCurrentIndex(max(0, fields_combo.findText(row_info[1])))

    def edit_criteria(self):
        indexes = self.criteria_table.selectedIndexes()
        if len(indexes) > 0:
            row = self.row_table.selectedIndexes()[0].row()
            criteria_row = indexes[0].row()
            _, value, ok = InputValueDialog.get_value(self, self.data_objs[self.row_table.cellWidget(row, 0).currentText()], self.row_table.cellWidget(row, 1).currentText(), self.timezone, value=self.current_criteria[criteria_row][1], show_comparison=False)
            if ok:
                item = self.criteria_table.item(criteria_row, 1)
                value_str = helper_functions.strftime(helper_functions.safe_tz_convert(value, self.timezone), include_tz=True) if isinstance(value, pd.Timestamp) and value.tzinfo is not None else str(value)
                item.setText(value_str)
                item.criteria_value = value
                self.current_criteria[criteria_row][1] = value

    def move_criteria(self, down):
        indexes = self.criteria_table.selectedIndexes()
        if len(indexes) > 0:
            row = indexes[0].row()
            if down and row < self.criteria_table.rowCount() - 1:
                old_row, new_row = row, row + 2
            elif not down and row > 0:
                old_row, new_row = row + 1, row - 1
            else:
                return
            criteria = self.current_criteria.pop(row)
            self.add_criteria(criteria + [new_row])
            self.criteria_table.setCurrentIndex(self.criteria_table.model().index(new_row, indexes[0].column()))
            self.criteria_table.setFocus()
            self.criteria_table.removeRow(old_row)

    def move_row(self, down):
        indexes = self.row_table.selectedIndexes()
        if len(indexes) > 0:
            row = indexes[0].row()
            if down and row < self.row_table.rowCount() - 1:
                old_row, new_row = row, row + 2
            elif not down and row > 0:
                old_row, new_row = row + 1, row - 1
            else:
                return
            self.add_row([self.row_table.cellWidget(row, 0).currentText(), self.row_table.cellWidget(row, 1).currentText(), self.row_table.item(row, 2).text(), self.row_table.item(row, 3).text(), self.row_table.cellWidget(row, 4).layout().itemAt(0).widget().isChecked(), new_row, self.row_table.item(row, 2).color_criteria])
            self.row_table.blockSignals(True)
            self.row_table.setCurrentIndex(self.row_table.model().index(new_row, indexes[0].column()))
            self.row_table.blockSignals(False)
            self.row_table.setFocus()
            self.row_table.removeRow(old_row)

    def remove_criteria(self):
        criteria_indexes = self.criteria_table.selectedIndexes()
        if len(criteria_indexes) > 0:
            row = criteria_indexes[0].row()
            self.current_criteria.pop(row)
            self.criteria_table.removeRow(row)

    def remove_row(self):
        indexes = self.row_table.selectedIndexes()
        if len(indexes) > 0:
            self.row_table.removeRow(indexes[0].row())

    def set_criteria(self):
        indexes = self.row_table.selectedIndexes()
        if len(indexes) > 0:
            row = indexes[0].row()
            new_criteria = self.row_table.item(row, 2).color_criteria
            if new_criteria is not self.current_criteria:
                self.update_criteria()
                self.current_criteria = []
                self.row_table.item(row, 2).color_criteria = self.current_criteria
                for row in reversed(range(self.criteria_table.rowCount())):
                    self.criteria_table.removeRow(row)
                for row in range(len(new_criteria)):
                    self.add_criteria(new_criteria[row] + [row])
        else:
            self.update_criteria()
            self.current_criteria = None
            for row in reversed(range(self.criteria_table.rowCount())):
                self.criteria_table.removeRow(row)

    def set_fields(self, fields_combo, text):
        fields_combo.clear()
        fields_combo.addItems(self.data_objs[text].data.columns.tolist())

    def update_criteria(self):
        for row in range(self.criteria_table.rowCount()):
            self.current_criteria[row] = [self.criteria_table.cellWidget(row, 0).currentText(), self.criteria_table.item(row, 1).criteria_value, self.criteria_table.cellWidget(row, 2).get_color()]

    def validate_input(self):
        self.results = []
        self.update_criteria()
        for row in range(self.row_table.rowCount()):
            table_row = dive_table_row.DIVETableRow()
            state = {'data_name': self.row_table.cellWidget(row, 0).currentText(),
                     'field_name': self.row_table.cellWidget(row, 1).currentText(),
                     'label': self.row_table.item(row, 2).text(),
                     'operation': self.row_table.item(row, 3).text(),
                     'color_criteria': self.row_table.item(row, 2).color_criteria,
                     'blend_colors': self.row_table.cellWidget(row, 4).layout().itemAt(0).widget().isChecked()}
            err_msg = table_row.set_state(self.data_objs, state)
            if err_msg is None:
                self.results.append(table_row)
            else:
                qtwidgets.QMessageBox.critical(self, 'Error', err_msg)
                return
        self.accept()

    @staticmethod
    def get_table_rows(parent, data_objs, table_rows, timezone):
        dialog = ConfigureTableRowsDialog(data_objs, table_rows, timezone, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        results = dialog.results
        dialog.deleteLater()
        return results, status

class DisplayAxisDialog(qtwidgets.QDialog):
    """
    This class is a dialog used to select
    an axis/axis group to display in DIVE.
    """
    def __init__(self, axis_objs, axis_group_objs, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle('Display Axis')
        self.setWindowFlags(self.windowFlags() & ~qtcore.Qt.WindowContextHelpButtonHint)
        self.setLayout(qtwidgets.QVBoxLayout())

        self.axes_tree = custom_qt.CompactTreeWidget()
        custom_qt.CompactTreeWidgetItem(parent=self.axes_tree, text='No Axis', enable_flags=[qtcore.Qt.ItemNeverHasChildren])
        if len(axis_objs) > 0:
            branch = custom_qt.CompactTreeWidgetItem(parent=self.axes_tree, text='Axes', disable_flags=[qtcore.Qt.ItemIsSelectable])
            for name in axis_objs:
                custom_qt.CompactTreeWidgetItem(parent=branch, text=name, enable_flags=[qtcore.Qt.ItemNeverHasChildren])
            branch.setExpanded(True)
        if len(axis_group_objs) > 0:
            branch = custom_qt.CompactTreeWidgetItem(parent=self.axes_tree, text='Axis Groups', disable_flags=[qtcore.Qt.ItemIsSelectable])
            for name in axis_group_objs:
                custom_qt.CompactTreeWidgetItem(parent=branch, text=name, enable_flags=[qtcore.Qt.ItemNeverHasChildren])
            branch.setExpanded(True)
        self.layout().addWidget(self.axes_tree)

        buttons = qtwidgets.QDialogButtonBox(qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_input)
        buttons.rejected.connect(self.reject)
        self.layout().addWidget(buttons)

    def get_results(self, status):
        if status:
            item = self.axes_tree.selectedItems()[0]
            parent_item = item.parent()
            if parent_item is not None:
                return item.text(0), parent_item.text(0) == 'Axis Groups'
        return None, False

    def validate_input(self):
        if len(self.axes_tree.selectedItems()) > 0:
            self.accept()
            return
        qtwidgets.QMessageBox.critical(self, 'Error', 'An axis or axis group must be selected.')

    @staticmethod
    def get_axis(parent, axis_objs, axis_group_objs):
        dialog = DisplayAxisDialog(axis_objs, axis_group_objs, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        results = dialog.get_results(status)
        dialog.deleteLater()
        return (*results, status)

class FilterDialog(qtwidgets.QDialog):
    """
    This class is a dialog used to add/edit/remove
    filter groups in DIVE.
    """
    def __init__(self, data_objs, filters, timezone, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle('Filter Data')
        self.setWindowFlags(self.windowFlags() & ~qtcore.Qt.WindowContextHelpButtonHint)
        self.setLayout(qtwidgets.QVBoxLayout())

        self.data_objs = data_objs
        self.timezone = timezone
        self.id_sort_idx = {} # Holds sorted indices for ID fields so they don't have to be recalculated

        tabs = qtwidgets.QTabWidget()
        self.layout().addWidget(tabs)

        # Setup the widgets for ID filter groups
        self.id_list = None
        if np.any([data_obj.id_field is not None for data_obj in self.data_objs.values()]):
            id_tab = qtwidgets.QWidget()
            id_tab.setLayout(qtwidgets.QVBoxLayout())
            tabs.addTab(id_tab, 'ID')
            button_hbox = qtwidgets.QHBoxLayout()
            id_tab.layout().addLayout(button_hbox)
            add_btn = qtwidgets.QPushButton('Add')
            add_btn.clicked.connect(self.add_id)
            button_hbox.addWidget(add_btn)
            edit_btn = qtwidgets.QPushButton('Edit')
            edit_btn.clicked.connect(self.edit_id)
            button_hbox.addWidget(edit_btn)
            remove_btn = qtwidgets.QPushButton('Remove')
            remove_btn.clicked.connect(self.remove_id)
            button_hbox.addWidget(remove_btn)
            self.id_list = custom_qt.CompactListWidget()
            id_tab.layout().addWidget(self.id_list)
            id_indices = filters.get_filter_indices(self.data_objs, 'ID', None, True, None)[0]
            # Convert the bool indices for ID filter groups to int indices
            for filter_indices in id_indices:
                for data_name in filter_indices['indices']:
                    data_ids = self.data_objs[data_name].data.loc[filter_indices['indices'][data_name], self.data_objs[data_name].id_field].astype('str')
                    data_ids.reset_index(drop=True, inplace=True)
                    data_ids.drop_duplicates(inplace=True)
                    unique_idx = data_ids.index.to_numpy()
                    filter_indices['indices'][data_name] = np.arange(len(self.data_objs[data_name].data.index))[filter_indices['indices'][data_name]][unique_idx]
            for i, id_obj in enumerate(filters.get_filter('ID', None)[0]):
                item = custom_qt.CompactListWidgetItem(text=id_obj['name'], parent=self.id_list, enable_flags=[qtcore.Qt.ItemIsUserCheckable], checked=id_obj['enabled'])
                item.id_filter = {'name': id_obj['name'], 'values': id_indices[i]['indices']}
            if self.id_list.count() > 0:
                self.id_list.setCurrentRow(0)

        # Setup the widgets for value filter groups
        value_tab = qtwidgets.QWidget()
        value_tab.setLayout(qtwidgets.QHBoxLayout())
        tabs.addTab(value_tab, 'Value')
        avail_group = qtwidgets.QGroupBox('Available Data')
        avail_group.setLayout(qtwidgets.QVBoxLayout())
        value_tab.layout().addWidget(avail_group)
        self.avail_tree = custom_qt.CompactTreeWidget()
        for data_name in list(self.data_objs):
            branch = custom_qt.CompactTreeWidgetItem(parent=self.avail_tree, text=data_name, disable_flags=[qtcore.Qt.ItemIsSelectable])
            for field in self.data_objs[data_name].data:
                custom_qt.CompactTreeWidgetItem(parent=branch, text=field, enable_flags=[qtcore.Qt.ItemNeverHasChildren])
        avail_group.layout().addWidget(self.avail_tree)

        button_vbox = qtwidgets.QVBoxLayout()
        value_tab.layout().addLayout(button_vbox)
        button_vbox.addStretch()
        group_btn = qtwidgets.QPushButton('Add Group')
        group_btn.clicked.connect(self.add_group)
        button_vbox.addWidget(group_btn)
        add_btn = qtwidgets.QPushButton('Add Filter')
        add_btn.clicked.connect(lambda: self.add_value())
        button_vbox.addWidget(add_btn)
        and_btn = qtwidgets.QPushButton('Add AND')
        and_btn.clicked.connect(lambda: self.add_value('AND'))
        button_vbox.addWidget(and_btn)
        or_btn = qtwidgets.QPushButton('Add OR')
        or_btn.clicked.connect(lambda: self.add_value('OR'))
        button_vbox.addWidget(or_btn)
        edit_btn = qtwidgets.QPushButton('Edit')
        edit_btn.clicked.connect(self.edit_value)
        button_vbox.addWidget(edit_btn)
        remove_btn = qtwidgets.QPushButton('Remove')
        remove_btn.clicked.connect(self.remove_value)
        button_vbox.addWidget(remove_btn)
        button_vbox.addStretch()

        filter_group = qtwidgets.QGroupBox('Filter Groups')
        filter_group.setLayout(qtwidgets.QVBoxLayout())
        value_tab.layout().addWidget(filter_group)
        self.value_tree = custom_qt.FilterTreeWidget()
        for value_filter in filters.get_filter('value', None)[0]:
            self.value_tree.add_group(value_filter)
        filter_group.layout().addWidget(self.value_tree)

        # Setup the widgets for custom filter groups
        custom_tab = qtwidgets.QWidget()
        custom_tab.setLayout(qtwidgets.QVBoxLayout())
        tabs.addTab(custom_tab, 'Custom')
        button_hbox = qtwidgets.QHBoxLayout()
        custom_tab.layout().addLayout(button_hbox)
        add_btn = qtwidgets.QPushButton('Add')
        add_btn.clicked.connect(self.add_custom)
        button_hbox.addWidget(add_btn)
        edit_btn = qtwidgets.QPushButton('Edit')
        edit_btn.clicked.connect(self.edit_custom)
        button_hbox.addWidget(edit_btn)
        remove_btn = qtwidgets.QPushButton('Remove')
        remove_btn.clicked.connect(self.remove_custom)
        button_hbox.addWidget(remove_btn)
        self.custom_list = custom_qt.CompactListWidget()
        custom_tab.layout().addWidget(self.custom_list)
        for custom_obj in filters.get_filter('custom', None)[0]:
            item = custom_qt.CompactListWidgetItem(text=custom_obj['name'], parent=self.custom_list, enable_flags=[qtcore.Qt.ItemIsUserCheckable], checked=custom_obj['enabled'])
            item.custom_filter = {'name': custom_obj['name'], 'values': custom_obj['values']}
        if self.custom_list.count() > 0:
            self.custom_list.setCurrentRow(0)

        buttons = qtwidgets.QDialogButtonBox(qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout().addWidget(buttons)

    def add_custom(self):
        custom_filter_names = [self.custom_list.item(i).text() for i in range(self.custom_list.count())]
        name, values, ok = CustomFilterDialog.get_filter(self, self.data_objs, self.timezone, {}, None, custom_filter_names)
        if ok:
            insert_idx = sorted(custom_filter_names + [name], key=helper_functions.natural_order).index(name)
            item = custom_qt.CompactListWidgetItem(text=name, enable_flags=[qtcore.Qt.ItemIsUserCheckable], checked=True)
            item.custom_filter = {'name': name, 'values': values}
            self.custom_list.insertItem(insert_idx, item)

    def add_group(self):
        data_names = [self.avail_tree.topLevelItem(i).text(0) for i in range(self.avail_tree.topLevelItemCount())]
        value_filter_names = [self.value_tree.topLevelItem(i).text(0) for i in range(self.value_tree.topLevelItemCount())]
        values, ok = ValueFilterDialog.get_filter(self, None, None, data_names, [], value_filter_names)
        if ok:
            self.value_tree.add_group(values)

    def add_id(self):
        id_filter_names = [self.id_list.item(i).text() for i in range(self.id_list.count())]
        name, values, ok = IDFilterDialog.get_filter(self, self.data_objs, {}, self.id_sort_idx, None, id_filter_names)
        if ok:
            insert_idx = sorted(id_filter_names + [name], key=helper_functions.natural_order).index(name)
            item = custom_qt.CompactListWidgetItem(text=name, enable_flags=[qtcore.Qt.ItemIsUserCheckable], checked=True)
            item.id_filter = {'name': name, 'values': values}
            self.id_list.insertItem(insert_idx, item)

    def add_value(self, logical_op=None):
        items = self.value_tree.selectedItems()
        if len(items) > 0:
            if logical_op is None:
                field_items = self.avail_tree.selectedItems()
                if len(field_items) > 0:
                    data_name, field_name = field_items[0].parent().text(0), field_items[0].text(0)
                    comparison_op, value, ok = InputValueDialog.get_value(self, self.data_objs[data_name], field_name, self.timezone)
                    if ok:
                        self.value_tree.add_filter(items[0], [comparison_op, data_name, field_name, value])
                else:
                    qtwidgets.QMessageBox.critical(self, 'Error', 'A data field name must be selected.')
            else:
                self.value_tree.add_filter(items[0], [logical_op])
        else:
            qtwidgets.QMessageBox.critical(self, 'Error', 'A value filter group item must be selected.')

    def edit_custom(self):
        items = self.custom_list.selectedItems()
        if len(items) > 0:
            filter_name = items[0].text()
            _, values, ok = CustomFilterDialog.get_filter(self, self.data_objs, self.timezone, items[0].custom_filter['values'], filter_name, [])
            if ok:
                items[0].custom_filter['values'] = values

    def edit_id(self):
        items = self.id_list.selectedItems()
        if len(items) > 0:
            filter_name = items[0].text()
            _, values, ok = IDFilterDialog.get_filter(self, self.data_objs, items[0].id_filter['values'], self.id_sort_idx, filter_name, [])
            if ok:
                items[0].id_filter['values'] = values

    def edit_value(self):
        items = self.value_tree.selectedItems()
        if len(items) > 0:
            if items[0].item_type == 'group':
                id_filter = items[0].child(0).text(0).split(': ')[1]
                id_filter = None if id_filter == 'None' else id_filter.lower()
                data_names = [self.avail_tree.topLevelItem(i).text(0) for i in range(self.avail_tree.topLevelItemCount())]
                check_names = [items[0].child(1).child(i).text(0) for i in range(items[0].child(1).childCount())]
                values, ok = ValueFilterDialog.get_filter(self, items[0].text(0), id_filter, data_names, check_names, [])
                if ok:
                    self.value_tree.edit_filter(values)
            elif items[0].item_type == 'filter':
                comparison_op, data_name, field_name, value = items[0].item_values
                comparison_op, value, ok = InputValueDialog.get_value(self, self.data_objs[data_name], field_name, self.timezone, comparison_op=comparison_op, value=value)
                if ok:
                    self.value_tree.edit_filter([comparison_op, data_name, field_name, value])
            else:
                self.value_tree.edit_filter()

    def remove_custom(self):
        indexes = self.custom_list.selectedIndexes()
        if len(indexes) > 0:
            item = self.custom_list.takeItem(indexes[0].row())
            del item

    def remove_id(self):
        indexes = self.id_list.selectedIndexes()
        if len(indexes) > 0:
            item = self.id_list.takeItem(indexes[0].row())
            del item

    def remove_value(self):
        self.value_tree.remove_filter()

    def get_results(self, status):
        filters = dive_filters.DIVEFilters()
        if status:
            if self.id_list is not None:
                for i in range(self.id_list.count()):
                    item = self.id_list.item(i)
                    for data_name in item.id_filter['values']:
                        item.id_filter['values'][data_name] = self.data_objs[data_name].data.iloc[item.id_filter['values'][data_name], self.data_objs[data_name].data.columns.get_loc(self.data_objs[data_name].id_field)]
                    item.id_filter['enabled'] = item.checkState() == qtcore.Qt.Checked
                    filters.add_filter(self.data_objs, 'ID', item.id_filter)
            for group in self.value_tree.get_groups():
                filters.add_filter(self.data_objs, 'value', group)
            for i in range(self.custom_list.count()):
                item = self.custom_list.item(i)
                item.custom_filter['enabled'] = item.checkState() == qtcore.Qt.Checked
                filters.add_filter(self.data_objs, 'custom', item.custom_filter)
        return filters

    @staticmethod
    def get_filters(parent, data_objs, filters, timezone):
        dialog = FilterDialog(data_objs, filters, timezone, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        results = dialog.get_results(status)
        dialog.deleteLater()
        return results, status

class IDFilterDialog(qtwidgets.QDialog):
    """
    This class is a dialog used to specify
    inputs for an ID filter group.
    """
    def __init__(self, data_objs, check_idx, sort_idx, name, id_filter_names, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle('Add ID Filter Group' if name is None else 'Edit ID Filter Group')
        self.setWindowFlags(self.windowFlags() & ~qtcore.Qt.WindowContextHelpButtonHint)
        self.setLayout(qtwidgets.QVBoxLayout())

        self.data_objs = data_objs
        self.sort_idx = sort_idx
        self.id_filter_names = id_filter_names
        self.data_name = None
        data_names = [data_name for data_name in self.data_objs if self.data_objs[data_name].id_field is not None]

        self.check_idx = {}
        for data_name in data_names:
            self.check_idx[data_name] = check_idx[data_name].copy() if data_name in check_idx else []

        name_hbox = qtwidgets.QHBoxLayout()
        self.layout().addLayout(name_hbox)
        name_hbox.addWidget(qtwidgets.QLabel('Name:'), 0)
        self.name = qtwidgets.QLineEdit('' if name is None else name)
        self.name.setEnabled(name is None)
        name_hbox.addWidget(self.name, 1)

        options_hbox = qtwidgets.QHBoxLayout()
        self.layout().addLayout(options_hbox)
        check_current_btn = qtwidgets.QPushButton('Check Current Data')
        check_current_btn.clicked.connect(lambda: self.id_list.set_checked(True))
        options_hbox.addWidget(check_current_btn)
        uncheck_current_btn = qtwidgets.QPushButton('Uncheck Current Data')
        uncheck_current_btn.clicked.connect(lambda: self.id_list.set_checked(False))
        options_hbox.addWidget(uncheck_current_btn)

        data_hbox = qtwidgets.QHBoxLayout()
        self.layout().addLayout(data_hbox)
        data_group = qtwidgets.QGroupBox('Data Names')
        data_group.setLayout(qtwidgets.QVBoxLayout())
        data_hbox.addWidget(data_group)
        self.data_list = custom_qt.CompactListWidget()
        self.data_list.currentTextChanged.connect(self.data_changed)
        for data_name in data_names:
            custom_qt.CompactListWidgetItem(text=data_name, parent=self.data_list, enable_flags=[qtcore.Qt.ItemIsUserCheckable], checked=data_name in check_idx)
        data_group.layout().addWidget(self.data_list)

        id_group = qtwidgets.QGroupBox('ID Values')
        id_group.setLayout(qtwidgets.QVBoxLayout())
        data_hbox.addWidget(id_group)
        self.id_list = custom_qt.LargeListView()
        id_group.layout().addWidget(self.id_list)

        buttons = qtwidgets.QDialogButtonBox(qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_input)
        buttons.rejected.connect(self.reject)
        self.layout().addWidget(buttons)

        if len(data_names) > 0:
            self.data_list.setCurrentRow(0)

    def data_changed(self, data_name):
        self.update_checked()
        self.data_name = data_name
        data_obj = self.data_objs[data_name]
        if data_name not in self.sort_idx:
            data_ids = data_obj.data.loc[:, data_obj.id_field].astype('str')
            data_ids.reset_index(drop=True, inplace=True)
            data_ids.drop_duplicates(inplace=True)
            data_ids.sort_values(inplace=True, kind='mergesort', key=lambda s: s.map(helper_functions.natural_order))
            self.sort_idx[data_name] = data_ids.index.to_numpy()
        checked = np.isin(self.sort_idx[data_name], self.check_idx[data_name])
        self.id_list.change_data(data_obj.data.iloc[self.sort_idx[data_name], data_obj.data.columns.get_loc(data_obj.id_field)].tolist(), checked)

    def update_checked(self):
        if self.data_name is not None:
            self.check_idx[self.data_name] = self.sort_idx[self.data_name][self.id_list.get_checked()]

    def validate_input(self):
        if self.name.text() in self.id_filter_names:
            qtwidgets.QMessageBox.critical(self, 'Error', 'Name "{}" is already in use.'.format(self.name.text()))
            return
        self.accept()

    def get_results(self, status):
        if status:
            self.update_checked()
            for i in range(self.data_list.count()):
                item = self.data_list.item(i)
                if item.checkState() == qtcore.Qt.Unchecked:
                    del self.check_idx[item.text()]
        return self.name.text(), self.check_idx

    @staticmethod
    def get_filter(parent, data_objs, check_idx, sort_idx, name, id_filter_names):
        dialog = IDFilterDialog(data_objs, check_idx, sort_idx, name, id_filter_names, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        results = dialog.get_results(status)
        dialog.deleteLater()
        return (*results, status)

class InputNameDialog(qtwidgets.QDialog):
    """
    This class is a dialog used to specify an object name.
    """
    def __init__(self, used_names, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle('Specify Name')
        self.setWindowFlags(self.windowFlags() & ~qtcore.Qt.WindowContextHelpButtonHint)
        self.setLayout(qtwidgets.QFormLayout())

        self.used_names = used_names

        self.name = qtwidgets.QLineEdit()
        self.layout().addRow('Name:', self.name)

        buttons = qtwidgets.QDialogButtonBox(qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_input)
        buttons.rejected.connect(self.reject)
        self.layout().addRow(buttons)

    def validate_input(self):
        if self.name.text() in self.used_names:
            qtwidgets.QMessageBox.critical(self, 'Error', 'Name "{}" is already in use.'.format(self.name.text()))
            return
        self.accept()

    @staticmethod
    def get_name(parent, used_names):
        dialog = InputNameDialog(used_names, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        name = dialog.name.text()
        dialog.deleteLater()
        return name, status

class InputAxisDialog(InputNameDialog):
    """
    This class is a dialog used to specify the name and type for an axis/artist.
    """
    def __init__(self, used_names, is_axis, **kwargs):
        super().__init__(used_names, **kwargs)
        self.setWindowTitle('Add Axis' if is_axis else 'Add Artist')

        self.type_value = qtwidgets.QComboBox()
        self.type_value.addItems(['2D', '3D'] if is_axis else ['Arrow', 'Box', 'Ellipse', 'Image', 'Infinite Line', 'Polygon', 'Rectangle', 'Scatter', 'Surface', 'Text'])
        self.layout().insertRow(1, 'Type:', self.type_value)

    @staticmethod
    def get_info(parent, used_names, is_axis):
        dialog = InputAxisDialog(used_names, is_axis, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        name, type_value = dialog.name.text(), dialog.type_value.currentText().lower()
        dialog.deleteLater()
        return name, type_value, status

class InputValueDialog(qtwidgets.QDialog):
    """
    This class is a dialog used to specify a value.
    """
    def __init__(self, data_obj, field_name, timezone, comparison_op, value, show_comparison, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle('Specify Value')
        self.setWindowFlags(self.windowFlags() & ~qtcore.Qt.WindowContextHelpButtonHint)
        self.setLayout(qtwidgets.QFormLayout())

        self.data_obj = data_obj
        self.field_name = field_name
        self.sort_idx = None

        if show_comparison:
            self.comparison_op = qtwidgets.QComboBox()
            self.comparison_op.addItems(['>', '>=', '==', '!=', '<=', '<'])
            if comparison_op is not None:
                self.comparison_op.setCurrentIndex(self.comparison_op.findText(comparison_op))
            self.layout().addRow('Comparison:', self.comparison_op)
        else:
            self.comparison_op = None

        value_group = qtwidgets.QGroupBox('Value')
        value_group.setLayout(qtwidgets.QVBoxLayout())
        self.layout().addRow(value_group)

        data_field = self.data_obj.data.loc[:, self.field_name]
        if pd.api.types.is_numeric_dtype(data_field):
            self.value = qtwidgets.QLineEdit()
            if value is not None:
                self.value.setText(str(value))
        elif pd.api.types.is_datetime64tz_dtype(data_field):
            self.value = custom_qt.TimeEdit()
            min_time, max_time = helper_functions.safe_tz_convert(pd.Timestamp.min.tz_localize('UTC'), timezone), helper_functions.safe_tz_convert(pd.Timestamp.max.tz_localize('UTC'), timezone)
            self.value.set_limits(min_time, max_time)
            time_val = data_field.min() if value is None or not (isinstance(value, pd.Timestamp) and value.tzinfo is not None) else value
            if time_val is not pd.NaT:
                self.value.set_time(time_val)
        else:
            self.value = custom_qt.LargeListView()
            data_field = data_field.astype('str')
            data_field.reset_index(drop=True, inplace=True)
            data_field.drop_duplicates(inplace=True)
            data_field.sort_values(inplace=True, kind='mergesort', key=lambda s: s.map(helper_functions.natural_order))
            self.sort_idx = data_field.index.to_numpy()
            self.value.change_data(data_field.tolist(), None)
            if value is None:
                self.value.setCurrentIndex(self.value.model().index(0))
            else:
                idx = data_field.isin(pd.Series([value], dtype='str'))
                idx.reset_index(drop=True, inplace=True)
                idx = idx.loc[idx].index
                self.value.setCurrentIndex(self.value.model().index(idx[0] if len(idx) > 0 else 0))

        value_group.layout().addWidget(self.value)

        buttons = qtwidgets.QDialogButtonBox(qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_input)
        buttons.rejected.connect(self.reject)
        self.layout().addRow(buttons)

    def validate_input(self):
        if isinstance(self.value, qtwidgets.QLineEdit):
            try:
                float(self.value.text())
            except:
                try:
                    complex(self.value.text())
                except:
                    qtwidgets.QMessageBox.critical(self, 'Error', 'The given value is invalid.')
                    return
        self.accept()

    def get_results(self, status):
        comparison_op, value = None, None
        if status:
            comparison_op = None if self.comparison_op is None else self.comparison_op.currentText()
            if isinstance(self.value, qtwidgets.QLineEdit):
                try:
                    value = float(self.value.text())
                except:
                    value = complex(self.value.text())
            elif isinstance(self.value, custom_qt.TimeEdit):
                value = self.value.get_time()
            else:
                value = self.data_obj.data.iat[self.sort_idx[self.value.currentIndex().row()], self.data_obj.data.columns.get_loc(self.field_name)]
        return comparison_op, value

    @staticmethod
    def get_value(parent, data_obj, field_name, timezone, comparison_op=None, value=None, show_comparison=True):
        dialog = InputValueDialog(data_obj, field_name, timezone, comparison_op, value, show_comparison, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        results = dialog.get_results(status)
        dialog.deleteLater()
        return (*results, status)

class InspectDataDialog(qtwidgets.QDialog):
    """
    This class is a dialog that displays a tabular view
    of the data objects that have been added to DIVE.
    """
    def __init__(self, data_objs, timezone, highlight_cell, check_state=None, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle('Inspect Data')
        self.setWindowFlags(self.windowFlags() & ~qtcore.Qt.WindowContextHelpButtonHint | qtcore.Qt.WindowMaximizeButtonHint)
        self.resize(800, 600)
        self.setLayout(qtwidgets.QVBoxLayout())

        self.data_objs = data_objs
        self.check_state = {name: None for name in self.data_objs} if check_state is None else check_state
        self.table_state = {name: None for name in self.data_objs}
        self.data_name = None

        hbox = qtwidgets.QHBoxLayout()
        self.layout().addLayout(hbox)

        data_group = qtwidgets.QGroupBox('Data Names')
        data_group.setLayout(qtwidgets.QVBoxLayout())
        self.data_list = custom_qt.CompactListWidget()
        self.data_list.addItems(list(self.data_objs))
        self.data_list.currentTextChanged.connect(self.data_changed)
        data_group.layout().addWidget(self.data_list)
        hbox.addWidget(data_group, 0)

        field_group = qtwidgets.QGroupBox('Field Names')
        field_group.setLayout(qtwidgets.QVBoxLayout())
        self.field_list = custom_qt.CompactListWidget()
        self.field_list.setSelectionMode(qtwidgets.QListWidget.ExtendedSelection)
        self.field_list.itemChanged.connect(self.toggle_visibility)
        field_group.layout().addWidget(self.field_list)
        hbox.addWidget(field_group, 0)

        table_vbox = qtwidgets.QVBoxLayout()
        hbox.addLayout(table_vbox, 1)
        self.options_hbox = qtwidgets.QHBoxLayout()
        table_vbox.addLayout(self.options_hbox)
        self.use_filters = qtwidgets.QCheckBox('Show Filtered')
        self.use_filters.stateChanged.connect(self.toggle_filter)
        self.options_hbox.addWidget(self.use_filters, 0)
        self.use_selected = qtwidgets.QCheckBox('Show Selected')
        self.use_selected.stateChanged.connect(self.toggle_filter)
        self.options_hbox.addWidget(self.use_selected, 0)
        clear_highlight_btn = qtwidgets.QPushButton('Clear Highlight')
        clear_highlight_btn.clicked.connect(lambda: self.table.setCurrentIndex(self.table.model().index(-1, -1)))
        self.options_hbox.addWidget(clear_highlight_btn, 0)
        clear_sort_btn = qtwidgets.QPushButton('Clear Sort')
        clear_sort_btn.clicked.connect(lambda: self.table.horizontalHeader().setSortIndicator(-1, qtcore.Qt.AscendingOrder))
        self.options_hbox.addWidget(clear_sort_btn, 0)
        self.row_count = qtwidgets.QLabel('')
        self.options_hbox.addWidget(self.row_count, 1)
        self.table = custom_qt.PandasTableView(timezone)
        self.table.horizontalHeader().sectionMoved.connect(self.column_moved)
        table_vbox.addWidget(self.table)

        self.update_row_count()

        if highlight_cell is not None:
            self.data_list.setCurrentRow(list(self.data_objs).index(highlight_cell[0]))
            self.table.setCurrentIndex(self.table.model().index(highlight_cell[2], self.data_objs[highlight_cell[0]].data.columns.get_loc(highlight_cell[1])))
            self.table.setFocus()
        elif len(self.data_objs) > 0:
            self.data_list.setCurrentRow(0)

    def calc_filters(self, data_name):
        selected_idx = self.data_objs[data_name].selection
        if self.use_filters.isChecked() and self.use_selected.isChecked():
            return self.data_objs[data_name].filtered_idx if selected_idx is None else np.logical_and(self.data_objs[data_name].filtered_idx, selected_idx)
        elif self.use_filters.isChecked():
            return self.data_objs[data_name].filtered_idx
        elif self.use_selected.isChecked():
            return np.ones(len(self.data_objs[data_name].filtered_idx), 'bool') if selected_idx is None else selected_idx
        return None

    def column_moved(self, logical_idx, old_idx, new_idx):
        check_offset = 0 if self.check_state[self.data_name] is None else 1
        self.field_list.insertItem(new_idx - check_offset, self.field_list.takeItem(old_idx - check_offset))

    def data_changed(self, data_name):
        if self.data_name is not None:
            self.table_state[self.data_name] = (self.table.horizontalHeader().saveState(), self.table.get_selection())
        self.data_name = data_name

        filtered_idx = self.calc_filters(data_name)
        self.table.change_data(self.data_objs[data_name].data, filtered_idx, self.check_state[data_name], self.table_state[data_name])

        self.update_row_count()

        self.field_list.clear()
        self.field_list.blockSignals(True)
        check_offset = 0 if self.check_state[self.data_name] is None else 1
        for iField in range(self.table.model().columnCount() - check_offset):
            logical_idx = self.table.horizontalHeader().logicalIndex(iField + check_offset)
            custom_qt.CompactListWidgetItem(text=self.table.model().headerData(logical_idx, qtcore.Qt.Horizontal), parent=self.field_list, enable_flags=[qtcore.Qt.ItemIsUserCheckable], checked=not self.table.isColumnHidden(logical_idx))
        self.field_list.blockSignals(False)

    def toggle_filter(self, state):
        for i, data_name in enumerate(self.data_objs):
            filtered_idx = self.calc_filters(data_name)
            self.data_list.item(i).setHidden(False if filtered_idx is None or filtered_idx.any() else True)
            if data_name == self.data_name:
                self.table.update_filter(filtered_idx)
                self.update_row_count()

    def toggle_visibility(self, item):
        logical_idx = self.data_objs[self.data_name].data.columns.get_loc(item.text()) + (0 if self.check_state[self.data_name] is None else 1)
        self.table.setColumnHidden(logical_idx, False if item.checkState() == qtcore.Qt.Checked else True)

    def update_row_count(self):
        self.row_count.setText('Total Rows: {}'.format(self.table.model().rowCount()))

    def validate_input(self):
        self.accept()

    @staticmethod
    def inspect_data(parent, data_objs, timezone, highlight_cell):
        dialog = InspectDataDialog(data_objs, timezone, highlight_cell, parent=parent)
        dialog.exec()
        dialog.deleteLater()

class SelectDataDialog(InspectDataDialog):
    """
    This class is a dialog that allows the user to specify the selected
    indices for the data objects that have been added to DIVE.
    """
    def __init__(self, data_objs, timezone, check_state, **kwargs):
        self.check_state = {}
        for data_name in data_objs:
            self.check_state[data_name] = check_state[data_name].copy() if data_name in check_state else np.zeros(len(data_objs[data_name].data.index), dtype='bool')

        super().__init__(data_objs, timezone, None, self.check_state, **kwargs)
        self.setWindowTitle('Select Data')
        self.use_selected.hide()

        check_current_btn = qtwidgets.QPushButton('Check Current Data')
        check_current_btn.clicked.connect(lambda: self.set_checked(current=True, state=True))
        self.options_hbox.insertWidget(2, check_current_btn, 0)
        uncheck_current_btn = qtwidgets.QPushButton('Uncheck Current Data')
        uncheck_current_btn.clicked.connect(lambda: self.set_checked(current=True, state=False))
        self.options_hbox.insertWidget(3, uncheck_current_btn, 0)
        check_all_btn = qtwidgets.QPushButton('Check All Data')
        check_all_btn.clicked.connect(lambda: self.set_checked(current=False, state=True))
        self.options_hbox.insertWidget(4, check_all_btn, 0)
        uncheck_all_btn = qtwidgets.QPushButton('Uncheck All Data')
        uncheck_all_btn.clicked.connect(lambda: self.set_checked(current=False, state=False))
        self.options_hbox.insertWidget(5, uncheck_all_btn, 0)

        buttons = qtwidgets.QDialogButtonBox(qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_input)
        buttons.rejected.connect(self.reject)
        self.layout().addWidget(buttons)

        for i in range(self.data_list.count()):
            item = self.data_list.item(i)
            item.setFlags(item.flags() | qtcore.Qt.ItemIsUserCheckable)
            item.setCheckState(qtcore.Qt.Checked if item.text() in check_state else qtcore.Qt.Unchecked)

    def get_results(self, status):
        if status:
            for i in range(self.data_list.count()):
                item = self.data_list.item(i)
                if item.checkState() == qtcore.Qt.Unchecked:
                    del self.check_state[item.text()]
        return self.check_state

    def set_checked(self, current, state):
        if current:
            self.table.set_checked(state)
        else:
            for i in range(self.data_list.count()):
                item = self.data_list.item(i)
                if not item.isHidden():
                    if item.text() == self.data_name:
                        self.table.set_checked(state)
                    else:
                        filtered_idx = self.calc_filters(item.text())
                        self.check_state[item.text()][slice(None) if filtered_idx is None else filtered_idx] = state

    @staticmethod
    def get_selected(parent, data_objs, timezone, check_state):
        dialog = SelectDataDialog(data_objs, timezone, check_state, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        results = dialog.get_results(status)
        dialog.deleteLater()
        return results, status

class CustomFilterDialog(SelectDataDialog):
    """
    This class is a dialog used to specify
    inputs for a custom filter group.
    """
    def __init__(self, data_objs, timezone, check_state, name, custom_filter_names, **kwargs):
        super().__init__(data_objs, timezone, check_state, **kwargs)
        self.setWindowTitle('Add Custom Filter Group' if name is None else 'Edit Custom Filter Group')
        self.use_selected.show()
        self.use_filters.hide()

        self.custom_filter_names = custom_filter_names

        name_hbox = qtwidgets.QHBoxLayout()
        self.layout().insertLayout(0, name_hbox, 0)
        name_hbox.addWidget(qtwidgets.QLabel('Name:'), 0)
        self.name = qtwidgets.QLineEdit('' if name is None else name)
        self.name.setEnabled(name is None)
        name_hbox.addWidget(self.name, 1)

    def get_results(self, status):
        return self.name.text(), super().get_results(status)

    def validate_input(self):
        if self.name.text() in self.custom_filter_names:
            qtwidgets.QMessageBox.critical(self, 'Error', 'Name "{}" is already in use.'.format(self.name.text()))
            return
        self.accept()

    @staticmethod
    def get_filter(parent, data_objs, timezone, check_state, name, custom_filter_names):
        dialog = CustomFilterDialog(data_objs, timezone, check_state, name, custom_filter_names, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        results = dialog.get_results(status)
        dialog.deleteLater()
        return (*results, status)

class RecordDialog(qtwidgets.QDialog):
    """
    This class is a dialog used to specify inputs for
    DIVEManager.record_video.
    """
    def __init__(self, min_time, max_time, fps, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle('Record Video')
        self.setWindowFlags(self.windowFlags() & ~qtcore.Qt.WindowContextHelpButtonHint)
        self.setLayout(qtwidgets.QFormLayout())

        path_hbox = qtwidgets.QHBoxLayout()
        self.layout().addRow('File Path:', path_hbox)
        self.file_path = qtwidgets.QLineEdit()
        self.file_path.setReadOnly(True)
        path_hbox.addWidget(self.file_path)
        self.browse_btn = qtwidgets.QPushButton('Browse')
        self.browse_btn.clicked.connect(self.specify_path)
        path_hbox.addWidget(self.browse_btn)
        self.start_time = custom_qt.TimeEdit()
        self.start_time.set_limits(min_time, max_time)
        self.layout().addRow('Start Time:', self.start_time)
        self.stop_time = custom_qt.TimeEdit()
        self.stop_time.set_limits(min_time, max_time)
        self.layout().addRow('Stop Time:', self.stop_time)
        self.fps = qtwidgets.QDoubleSpinBox()
        self.fps.setRange(0.0, float('inf'))
        self.fps.setValue(fps)
        self.fps.setDecimals(0)
        self.layout().addRow('FPS:', self.fps)

        buttons = qtwidgets.QDialogButtonBox(qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_input)
        buttons.rejected.connect(self.reject)
        self.layout().addRow(buttons)

    def specify_path(self):
        file_name, _ = qtwidgets.QFileDialog.getSaveFileName(self, 'Path to Video File', '', 'MP4 File (*.mp4)')
        if file_name:
            if not file_name.lower().endswith('.mp4'):
                file_name += '.mp4'
            self.file_path.setText(file_name)

    def validate_input(self):
        if self.file_path.text() == '':
            qtwidgets.QMessageBox.critical(self, 'Error', 'A path must be given for the video file.')
            return
        start_time = self.start_time.get_time()
        stop_time = self.stop_time.get_time()
        if start_time > stop_time:
            qtwidgets.QMessageBox.critical(self, 'Error', 'The start time cannot be after the stop time.')
            return
        elif int(self.fps.value()) <= 0:
            qtwidgets.QMessageBox.critical(self, 'Error', 'The FPS must be greater than 0.')
            return
        self.accept()

    def get_results(self, status):
        if status:
            return {'file_path': self.file_path.text(),
                    'start_time': self.start_time.get_time(),
                    'stop_time': self.stop_time.get_time(),
                    'fps': int(self.fps.value())}
        return {}

    @staticmethod
    def get_video_details(parent, min_time, max_time, fps):
        dialog = RecordDialog(min_time, max_time, fps, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        results = dialog.get_results(status)
        dialog.deleteLater()
        return results, status

class SettingsDialog(qtwidgets.QDialog):
    """
    This class is a dialog used to specify inputs for
    DIVEManager.set_settings.
    """
    def __init__(self, allow_theme, time_step, fps, hold_time, table_change_time, timezone, clock_size, marking, marking_color, marking_size, gui_theme, canvas_theme, axis_label_size, axis_tick_size, apply_limits_filter, and_filters, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle('Settings')
        self.setWindowFlags(self.windowFlags() & ~qtcore.Qt.WindowContextHelpButtonHint)
        self.setLayout(qtwidgets.QVBoxLayout())

        animation_group = qtwidgets.QGroupBox('Animation')
        animation_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addWidget(animation_group)
        self.time_step = qtwidgets.QDoubleSpinBox()
        self.time_step.setRange(0.0, pd.Timedelta.max.total_seconds())
        self.time_step.setValue(time_step)
        self.time_step.setDecimals(6)
        animation_group.layout().addRow('Time Step (sec):', self.time_step)
        self.fps = qtwidgets.QDoubleSpinBox()
        self.fps.setRange(0.0, float('inf'))
        self.fps.setValue(fps)
        self.fps.setDecimals(0)
        animation_group.layout().addRow('FPS:', self.fps)
        self.hold_time = qtwidgets.QDoubleSpinBox()
        self.hold_time.setRange(0.0, pd.Timedelta.max.total_seconds())
        self.hold_time.setValue(hold_time)
        self.hold_time.setDecimals(6)
        animation_group.layout().addRow('Hold Time (sec):', self.hold_time)
        self.table_change_time = qtwidgets.QDoubleSpinBox()
        self.table_change_time.setRange(0.0, pd.Timedelta.max.total_seconds())
        self.table_change_time.setValue(table_change_time)
        self.table_change_time.setDecimals(6)
        animation_group.layout().addRow('Table Change Time (sec):', self.table_change_time)
        labels_group = qtwidgets.QGroupBox('Labels')
        labels_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addWidget(labels_group)
        self.timezone = qtwidgets.QComboBox()
        self.timezone.addItems(pytz.all_timezones)
        self.timezone.setCurrentIndex(self.timezone.findText(timezone))
        labels_group.layout().addRow('Timezone:', self.timezone)
        self.clock_size = qtwidgets.QDoubleSpinBox()
        self.clock_size.setRange(0.0, float('inf'))
        self.clock_size.setValue(clock_size)
        self.clock_size.setDecimals(6)
        labels_group.layout().addRow('Clock Size:', self.clock_size)
        marking_hbox = qtwidgets.QHBoxLayout()
        labels_group.layout().addRow('Marking:', marking_hbox)
        self.marking = qtwidgets.QLineEdit(marking)
        marking_hbox.addWidget(self.marking)
        self.marking_color = custom_qt.ColorButton(marking_color)
        marking_hbox.addWidget(self.marking_color)
        self.marking_size = qtwidgets.QDoubleSpinBox()
        self.marking_size.setRange(0.0, float('inf'))
        self.marking_size.setValue(marking_size)
        self.marking_size.setDecimals(6)
        labels_group.layout().addRow('Marking Size:', self.marking_size)
        appearance_group = qtwidgets.QGroupBox('Appearance')
        appearance_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addWidget(appearance_group)
        if allow_theme:
            self.gui_theme = qtwidgets.QComboBox()
            self.gui_theme.addItems(['Default', 'Light', 'Dark'])
            self.gui_theme.setCurrentIndex(self.gui_theme.findText(gui_theme.title()))
            appearance_group.layout().addRow('GUI Theme:', self.gui_theme)
        else:
            self.gui_theme = None
        self.canvas_theme = qtwidgets.QComboBox()
        self.canvas_theme.addItems(['Light', 'Dark'])
        self.canvas_theme.setCurrentIndex(self.canvas_theme.findText(canvas_theme.title()))
        appearance_group.layout().addRow('Canvas Theme:', self.canvas_theme)
        self.axis_label_size = qtwidgets.QDoubleSpinBox()
        self.axis_label_size.setRange(0.0, float('inf'))
        self.axis_label_size.setValue(axis_label_size)
        self.axis_label_size.setDecimals(6)
        appearance_group.layout().addRow('Axis Label Size:', self.axis_label_size)
        self.axis_tick_size = qtwidgets.QDoubleSpinBox()
        self.axis_tick_size.setRange(0.0, float('inf'))
        self.axis_tick_size.setValue(axis_tick_size)
        self.axis_tick_size.setDecimals(6)
        appearance_group.layout().addRow('Axis Tick Size:', self.axis_tick_size)
        filters_group = qtwidgets.QGroupBox('Filters')
        filters_group.setLayout(qtwidgets.QFormLayout())
        self.layout().addWidget(filters_group)
        self.apply_limits_filter = qtwidgets.QCheckBox()
        self.apply_limits_filter.setChecked(apply_limits_filter)
        filters_group.layout().addRow('Apply Filters To Limits:', self.apply_limits_filter)
        and_hbox = qtwidgets.QHBoxLayout()
        filters_group.layout().addRow('Merge Filter Groups Using:', and_hbox)
        self.and_filters = qtwidgets.QRadioButton('AND')
        self.and_filters.setChecked(and_filters)
        and_hbox.addWidget(self.and_filters, 0)
        or_filters = qtwidgets.QRadioButton('OR')
        or_filters.setChecked(not and_filters)
        and_hbox.addWidget(or_filters, 1)

        buttons = qtwidgets.QDialogButtonBox(qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_input)
        buttons.rejected.connect(self.reject)
        self.layout().addWidget(buttons)

    def validate_input(self):
        if self.time_step.value() <= 0:
            qtwidgets.QMessageBox.critical(self, 'Error', 'The time step must be greater than 0.')
            return
        elif int(self.fps.value()) <= 0:
            qtwidgets.QMessageBox.critical(self, 'Error', 'The FPS must be greater than 0.')
            return
        self.accept()

    def get_results(self, status):
        if status:
            return {'time_step': self.time_step.value(),
                    'fps': int(self.fps.value()),
                    'hold_time': self.hold_time.value(),
                    'table_change_time': self.table_change_time.value(),
                    'timezone': self.timezone.currentText(),
                    'clock_size': self.clock_size.value(),
                    'marking': self.marking.text(),
                    'marking_color': self.marking_color.get_color(),
                    'marking_size': self.marking_size.value(),
                    'gui_theme': 'default' if self.gui_theme is None else self.gui_theme.currentText().lower(),
                    'canvas_theme': self.canvas_theme.currentText().lower(),
                    'axis_label_size': self.axis_label_size.value(),
                    'axis_tick_size': self.axis_tick_size.value(),
                    'apply_limits_filter': self.apply_limits_filter.isChecked(),
                    'and_filters': self.and_filters.isChecked()}
        return {}

    @staticmethod
    def get_settings(parent, allow_theme, time_step, fps, hold_time, table_change_time, timezone, clock_size, marking, marking_color, marking_size, gui_theme, canvas_theme, axis_label_size, axis_tick_size, apply_limits_filter, and_filters):
        dialog = SettingsDialog(allow_theme, time_step, fps, hold_time, table_change_time, timezone, clock_size, marking, marking_color, marking_size, gui_theme, canvas_theme, axis_label_size, axis_tick_size, apply_limits_filter, and_filters, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        results = dialog.get_results(status)
        dialog.deleteLater()
        return results, status

class ValueFilterDialog(qtwidgets.QDialog):
    """
    This class is a dialog used to specify
    inputs for a value filter group.
    """
    def __init__(self, name, id_filter, data_names, check_names, value_filter_names, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle('Add Value Filter Group' if name is None else 'Edit Value Filter Group')
        self.setWindowFlags(self.windowFlags() & ~qtcore.Qt.WindowContextHelpButtonHint)
        self.setLayout(qtwidgets.QFormLayout())

        self.value_filter_names = value_filter_names

        self.name = qtwidgets.QLineEdit()
        self.name.setText('' if name is None else name)
        self.name.setEnabled(name is None)
        self.layout().addRow('Name:', self.name)

        self.id_filter = qtwidgets.QComboBox()
        self.id_filter.addItems(['None', 'Any Match', 'All Match', 'Any Mismatch', 'All Mismatch'])
        if id_filter is not None:
            self.id_filter.setCurrentIndex(self.id_filter.findText(id_filter.title()))
        self.layout().addRow('ID Filter:', self.id_filter)

        data_group = qtwidgets.QGroupBox('Data Names')
        data_group.setLayout(qtwidgets.QVBoxLayout())
        self.data_list = custom_qt.CompactListWidget()
        for data_name in data_names:
            custom_qt.CompactListWidgetItem(text=data_name, parent=self.data_list, enable_flags=[qtcore.Qt.ItemIsUserCheckable], checked=data_name in check_names)
        data_group.layout().addWidget(self.data_list)
        self.layout().addRow(data_group)

        self.buttons = qtwidgets.QDialogButtonBox(qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.validate_input)
        self.buttons.rejected.connect(self.reject)
        self.layout().addRow(self.buttons)

    def validate_input(self):
        if self.name.text() in self.value_filter_names:
            qtwidgets.QMessageBox.critical(self, 'Error', 'Name "{}" is already in use.'.format(self.name.text()))
            return
        self.accept()

    def get_results(self, status):
        if status:
            return {'name': self.name.text(),
                    'data_names': [self.data_list.item(i).text() for i in range(self.data_list.count()) if self.data_list.item(i).checkState() == qtcore.Qt.Checked],
                    'filters': ['AND'],
                    'id_filter': None if self.id_filter.currentText() == 'None' else self.id_filter.currentText().lower(),
                    'enabled': True}
        return {}

    @staticmethod
    def get_filter(parent, name, id_filter, data_names, check_names, value_filter_names):
        dialog = ValueFilterDialog(name, id_filter, data_names, check_names, value_filter_names, parent=parent)
        status = dialog.exec() == qtwidgets.QDialog.Accepted
        results = dialog.get_results(status)
        dialog.deleteLater()
        return results, status