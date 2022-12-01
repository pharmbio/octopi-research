# qt libraries
from qtpy.QtCore import Qt, QModelIndex, QSize, Signal
from qtpy.QtWidgets import QFrame, QPushButton, QLineEdit, QDoubleSpinBox, \
    QSpinBox, QListWidget, QGridLayout, QCheckBox, QLabel, QAbstractItemView, \
    QComboBox, QHBoxLayout, QMessageBox, QFileDialog, QProgressBar, QDesktopWidget, \
    QWidget, QTableWidget, QSizePolicy, QTableWidgetItem, QApplication
from qtpy.QtGui import QIcon

from control._def import *

def as_widget(layout)->QWidget:
    w=QWidget()
    w.setLayout(layout)
    return w

from typing import Optional, Union, List, Tuple, Callable

from control.core import MultiPointController, ConfigurationManager
from control.typechecker import TypecheckFunction

BUTTON_START_ACQUISITION_IDLE_TEXT="Start Acquisition"
BUTTON_START_ACQUISITION_RUNNING_TEXT="Abort Acquisition"

class MultiPointWidget(QFrame):
    def __init__(self,
        multipointController:MultiPointController,
        configurationManager:ConfigurationManager,
        start_experiment:Callable[[str,List[str]],Optional[Signal]],
        abort_experiment:Callable[[],None]
    ):
        """ start_experiment callable may return signal that is emitted on experiment completion"""
        super().__init__()
        
        self.multipointController = multipointController
        self.configurationManager = configurationManager
        self.start_experiment=start_experiment
        self.abort_experiment=abort_experiment

        self.base_path_is_set = False

        self.add_components()
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)

    @TypecheckFunction
    def add_components(self):

        if True: # add image saving options (path where to save)
            self.btn_setSavingDir = QPushButton('Browse')
            self.btn_setSavingDir.setDefault(False)
            self.btn_setSavingDir.setIcon(QIcon('icon/folder.png'))
            self.btn_setSavingDir.clicked.connect(self.set_saving_dir)
            
            self.lineEdit_savingDir = QLineEdit()
            self.lineEdit_savingDir.setReadOnly(True)
            self.lineEdit_savingDir.setText('Choose a base saving directory')

            self.lineEdit_savingDir.setText(MACHINE_DISPLAY_CONFIG.DEFAULT_SAVING_PATH)
            self.multipointController.set_base_path(MACHINE_DISPLAY_CONFIG.DEFAULT_SAVING_PATH)
            self.base_path_is_set = True

            self.lineEdit_experimentID = QLineEdit()

        if True: # add imaging grid configuration options
            self.entry_deltaX = QDoubleSpinBox()
            self.entry_deltaX.setMinimum(0) 
            self.entry_deltaX.setMaximum(5) 
            self.entry_deltaX.setSingleStep(0.1)
            self.entry_deltaX.setValue(self.multipointController.deltaX)
            self.entry_deltaX.setDecimals(3)
            self.entry_deltaX.setKeyboardTracking(False)
            self.entry_deltaX.valueChanged.connect(self.set_deltaX)

            self.entry_NX = QSpinBox()
            self.entry_NX.setMinimum(1)
            self.entry_NX.setSingleStep(1)
            self.entry_NX.setKeyboardTracking(False)
            self.entry_NX.valueChanged.connect(self.set_NX)
            self.entry_NX.valueChanged.connect(lambda v:self.grid_changed("x",v))
            self.set_NX(self.multipointController.NX)

            self.entry_deltaY = QDoubleSpinBox()
            self.entry_deltaY.setMinimum(0)
            self.entry_deltaY.setSingleStep(0.1)
            self.entry_deltaY.setDecimals(3)
            self.entry_deltaY.setKeyboardTracking(False)
            self.entry_deltaY.valueChanged.connect(self.set_deltaY)
            self.entry_deltaY.setValue(self.multipointController.deltaY)
            
            self.entry_NY = QSpinBox()
            self.entry_NY.setMinimum(1)
            self.entry_NY.setSingleStep(1)
            self.entry_NY.setKeyboardTracking(False)
            self.entry_NY.valueChanged.connect(self.set_NY)
            self.entry_NY.valueChanged.connect(lambda v:self.grid_changed("y",v))
            self.set_NY(self.multipointController.NY)

            self.entry_deltaZ = QDoubleSpinBox()
            self.entry_deltaZ.setMinimum(0)
            self.entry_deltaZ.setSingleStep(0.2)
            self.entry_deltaZ.setValue(self.multipointController.deltaZ)
            self.entry_deltaZ.setDecimals(3)
            self.entry_deltaZ.setKeyboardTracking(False)
            self.entry_deltaZ.valueChanged.connect(self.set_deltaZ)
            
            self.entry_NZ = QSpinBox()
            self.entry_NZ.setMinimum(1)
            self.entry_NZ.setSingleStep(1)
            self.entry_NZ.setKeyboardTracking(False)
            self.entry_NZ.valueChanged.connect(self.set_NZ)
            self.set_NZ(self.multipointController.NZ)
            
            self.entry_dt = QDoubleSpinBox()
            self.entry_dt.setMinimum(0)
            self.entry_dt.setSingleStep(1)
            self.entry_dt.setValue(self.multipointController.deltat)
            self.entry_dt.setDecimals(3)
            self.entry_dt.setKeyboardTracking(False)
            self.entry_dt.valueChanged.connect(self.multipointController.set_deltat)

            self.entry_Nt = QSpinBox()
            self.entry_Nt.setMinimum(1)
            self.entry_Nt.setSingleStep(1)
            self.entry_Nt.setKeyboardTracking(False)
            self.entry_Nt.valueChanged.connect(self.set_Nt)
            self.set_Nt(self.multipointController.Nt)

        self.list_configurations = QListWidget()
        self.list_configurations.list_channel_names=[mc.name for mc in self.configurationManager.configurations]
        self.list_configurations.addItems(self.list_configurations.list_channel_names)
        self.list_configurations.setSelectionMode(QAbstractItemView.MultiSelection) # ref: https://doc.qt.io/qt-5/qabstractitemview.html#SelectionMode-enum
        self.list_configurations.setDragDropMode(QAbstractItemView.InternalMove) # allow moving items within list
        self.list_configurations.model().rowsMoved.connect(self.channel_list_rows_moved)

        if True: # add autofocus related stuff
            self.checkbox_withAutofocus = QCheckBox('Software AF')
            self.checkbox_withAutofocus.setToolTip("enable autofocus for multipoint acquisition\nfor each well the autofocus will be calculated in the channel selected below")
            self.checkbox_withAutofocus.setChecked(MACHINE_DISPLAY_CONFIG.MULTIPOINT_SOFTWARE_AUTOFOCUS_ENABLE_BY_DEFAULT)
            self.checkbox_withAutofocus.stateChanged.connect(self.set_software_af_flag)

            af_channel_dropdown=QComboBox()
            af_channel_dropdown.setToolTip("set channel that will be used for autofocus measurements")
            channel_names=[microscope_configuration.name for microscope_configuration in self.configurationManager.configurations]
            af_channel_dropdown.addItems(channel_names)
            af_channel_dropdown.setCurrentIndex(channel_names.index(self.multipointController.autofocus_channel_name))
            af_channel_dropdown.currentIndexChanged.connect(lambda index:setattr(MUTABLE_MACHINE_CONFIG,"MULTIPOINT_AUTOFOCUS_CHANNEL",channel_names[index]))
            self.af_channel_dropdown=af_channel_dropdown

            self.set_software_af_flag(MACHINE_DISPLAY_CONFIG.MULTIPOINT_SOFTWARE_AUTOFOCUS_ENABLE_BY_DEFAULT)

            self.checkbox_laserAutofocs = QCheckBox('Laser AF')
            self.checkbox_laserAutofocs.setChecked(MACHINE_DISPLAY_CONFIG.MULTIPOINT_LASER_AUTOFOCUS_ENABLE_BY_DEFAULT)
            self.checkbox_laserAutofocs.stateChanged.connect(self.multipointController.set_laser_af_flag)
            self.multipointController.set_laser_af_flag(MACHINE_DISPLAY_CONFIG.MULTIPOINT_LASER_AUTOFOCUS_ENABLE_BY_DEFAULT)

            self.btn_startAcquisition = QPushButton(BUTTON_START_ACQUISITION_IDLE_TEXT)
            self.btn_startAcquisition.setCheckable(True)
            self.btn_startAcquisition.setChecked(False)
            self.btn_startAcquisition.clicked.connect(self.toggle_acquisition)

            grid_multipoint_acquisition_config=QGridLayout()
            grid_multipoint_acquisition_config.addWidget(self.checkbox_withAutofocus,0,0)
            grid_multipoint_acquisition_config.addWidget(self.af_channel_dropdown,1,0)
            grid_multipoint_acquisition_config.addWidget(self.checkbox_laserAutofocs,2,0)
            grid_multipoint_acquisition_config.addWidget(self.btn_startAcquisition,3,0)

        # layout
        grid_line0 = QGridLayout()
        grid_line0.addWidget(QLabel('Saving Path'))
        grid_line0.addWidget(self.lineEdit_savingDir, 0,1)
        grid_line0.addWidget(self.btn_setSavingDir, 0,2)

        grid_line1 = QGridLayout()
        grid_line1.addWidget(QLabel('Experiment ID'), 0,0)
        grid_line1.addWidget(self.lineEdit_experimentID,0,1)

        grid_line2 = QGridLayout()
        dx_tooltip="acquire grid of images (Nx images with dx mm in between acquisitions; dx does not matter if Nx is 1)\ncan be combined with dy/Ny and dz/Nz and dt/Nt for a total of Nx * Ny * Nz * Nt images"
        qtlabel_dx=QLabel('dx (mm)')
        qtlabel_dx.setToolTip(dx_tooltip)
        grid_line2.addWidget(qtlabel_dx, 0,2)
        grid_line2.addWidget(self.entry_deltaX, 0,3)
        qtlabel_Nx=QLabel('Nx')
        qtlabel_Nx.setToolTip(dx_tooltip)
        grid_line2.addWidget(qtlabel_Nx, 0,0)
        grid_line2.addWidget(self.entry_NX, 0,1)
 
        dy_tooltip="acquire grid of images (Ny images with dy mm in between acquisitions; dy does not matter if Ny is 1)\ncan be combined with dx/Nx and dz/Nz and dt/Nt for a total of Nx*Ny*Nz*Nt images"
        qtlabel_dy=QLabel('dy (mm)')
        qtlabel_dy.setToolTip(dy_tooltip)
        grid_line2.addWidget(qtlabel_dy, 1,2)
        grid_line2.addWidget(self.entry_deltaY, 1,3)
        qtlabel_Ny=QLabel('Ny')
        qtlabel_Ny.setToolTip(dy_tooltip)
        grid_line2.addWidget(qtlabel_Ny, 1,0)
        grid_line2.addWidget(self.entry_NY, 1,1)
 
        dz_tooltip="acquire z-stack of images (Nz images with dz µm in between acquisitions; dz does not matter if Nz is 1)\ncan be combined with dx/Nx and dy/Ny and dt/Nt for a total of Nx*Ny*Nz*Nt images"
        qtlabel_dz=QLabel('dz (um)')
        qtlabel_dz.setToolTip(dz_tooltip)
        grid_line2.addWidget(qtlabel_dz, 2,2)
        grid_line2.addWidget(self.entry_deltaZ, 2,3)
        qtlabel_Nz=QLabel('Nz')
        qtlabel_Nz.setToolTip(dz_tooltip)
        grid_line2.addWidget(qtlabel_Nz, 2,0)
        grid_line2.addWidget(self.entry_NZ, 2,1)
 
        dt_tooltip="acquire time-series of 'Nt' images, with 'dt' seconds in between acquisitions (dt does not matter if Nt is 1)\ncan be combined with dx/Nx and dy/Ny and dz/Nz for a total of Nx*Ny*Nz*Nt images"
        qtlabel_dt=QLabel('dt (s)')
        qtlabel_dt.setToolTip(dt_tooltip)
        grid_line2.addWidget(qtlabel_dt, 3,2)
        grid_line2.addWidget(self.entry_dt, 3,3)
        qtlabel_Nt=QLabel('Nt')
        qtlabel_Nt.setToolTip(dt_tooltip)
        grid_line2.addWidget(qtlabel_Nt, 3,0)
        grid_line2.addWidget(self.entry_Nt, 3,1)

        self.well_grid_selector=QTableWidget()
        self.well_grid_selector.horizontalHeader().hide()
        self.well_grid_selector.verticalHeader().hide()
        self.well_grid_selector.horizontalHeader().setMinimumSectionSize(0)
        self.well_grid_selector.verticalHeader().setMinimumSectionSize(0)
        self.grid_changed("x",self.multipointController.NX)
        self.grid_changed("y",self.multipointController.NY)
 
        self.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Minimum)
        grid_line2.addWidget(self.well_grid_selector,0,4,4,1)

        grid_line3 = QHBoxLayout()
        grid_line3.addWidget(self.list_configurations)
        grid_line3.addLayout(grid_multipoint_acquisition_config)

        self.progress_bar=QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(0)

        self.grid = QGridLayout()
        self.grid.addLayout(grid_line0,0,0)
        self.grid.addLayout(grid_line1,1,0)
        self.grid.addLayout(grid_line2,2,0)
        self.grid.addLayout(grid_line3,3,0)
        self.grid.addWidget(self.progress_bar,4,0)
        self.setLayout(self.grid)

    def set_NX(self,new_value:int):
        self.multipointController.set_NX(new_value)
        if new_value==1:
            self.entry_deltaX.setDisabled(True)
        else:
            self.entry_deltaX.setDisabled(False)

    def set_NY(self,new_value:int):
        self.multipointController.set_NY(new_value)
        if new_value==1:
            self.entry_deltaY.setDisabled(True)
        else:
            self.entry_deltaY.setDisabled(False)

    def set_NZ(self,new_value:int):
        self.multipointController.set_NZ(new_value)
        if new_value==1:
            self.entry_deltaZ.setDisabled(True)
        else:
            self.entry_deltaZ.setDisabled(False)

    def set_Nt(self,new_value:int):
        self.multipointController.set_Nt(new_value)
        if new_value==1:
            self.entry_dt.setDisabled(True)
        else:
            self.entry_dt.setDisabled(False)


    def set_software_af_flag(self,flag:Union[int,bool]):
        flag=bool(flag)
        self.af_channel_dropdown.setDisabled(not flag)
        self.multipointController.set_software_af_flag(flag)

    def grid_changed(self,dimension:str,new_value:int):
        if dimension=="x":
            self.well_grid_selector.setColumnCount(new_value)
        elif dimension=="y":
            self.well_grid_selector.setRowCount(new_value)
        elif dimension=="z":
            pass
        elif dimension=="t":
            pass
        else:
            raise Exception()

        size=QDesktopWidget().width()*0.06
        nx=self.multipointController.NX
        ny=self.multipointController.NY

        #self.well_grid_selector.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Minimum)
        self.well_grid_selector.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # type: ignore
        self.well_grid_selector.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # type: ignore
        self.well_grid_selector.setFixedSize(size,size)
        self.well_grid_selector.horizontalHeader().setDefaultSectionSize(size//ny)
        self.well_grid_selector.verticalHeader().setDefaultSectionSize(size//nx)

        for x in range(0,nx):
            for y in range(0,ny):
                grid_item=QTableWidgetItem()
                grid_item.setSizeHint(QSize(grid_item.sizeHint().width(), size//nx))
                grid_item.setSizeHint(QSize(grid_item.sizeHint().height(), size//ny))
                grid_item.setSelected(True)
                self.well_grid_selector.setItem(y,x,grid_item)

        self.well_grid_selector.resizeColumnsToContents()
        self.well_grid_selector.resizeRowsToContents()

    def channel_list_rows_moved(self,_parent:QModelIndex,row_range_moved_start:int,row_range_moved_end:int,_destination:QModelIndex,row_index_drop_release:int):
        # saved items about to be moved
        dragged=self.list_configurations.list_channel_names[row_range_moved_start:row_range_moved_end+1]
        dragged_range_len=len(dragged)

        # remove range that is about to be moved
        ret_list=self.list_configurations.list_channel_names[:row_range_moved_start]
        ret_list.extend(self.list_configurations.list_channel_names[row_range_moved_end+1:])
        self.list_configurations.list_channel_names=ret_list

        # insert items at insert index, adjusted for removed range
        if row_index_drop_release<=row_range_moved_start:
            insert_index=row_index_drop_release
        else:
            insert_index=row_index_drop_release-dragged_range_len

        for i in reversed(range(dragged_range_len)):
            self.list_configurations.list_channel_names.insert(insert_index,dragged[i])

    @TypecheckFunction
    def set_deltaX(self,value:float):
        mm_per_ustep = MACHINE_CONFIG.SCREW_PITCH_X_MM/(self.multipointController.navigationController.x_microstepping*MACHINE_CONFIG.FULLSTEPS_PER_REV_X) # to implement a get_x_microstepping() in multipointController
        deltaX = round(value/mm_per_ustep)*mm_per_ustep
        self.entry_deltaX.setValue(deltaX)
        self.multipointController.set_deltaX(deltaX)

    @TypecheckFunction
    def set_deltaY(self,value:float):
        mm_per_ustep = MACHINE_CONFIG.SCREW_PITCH_Y_MM/(self.multipointController.navigationController.y_microstepping*MACHINE_CONFIG.FULLSTEPS_PER_REV_Y)
        deltaY = round(value/mm_per_ustep)*mm_per_ustep
        self.entry_deltaY.setValue(deltaY)
        self.multipointController.set_deltaY(deltaY)

    @TypecheckFunction
    def set_deltaZ(self,value:float):
        mm_per_ustep = MACHINE_CONFIG.SCREW_PITCH_Z_MM/(self.multipointController.navigationController.z_microstepping*MACHINE_CONFIG.FULLSTEPS_PER_REV_Z)
        deltaZ = round(value/1000/mm_per_ustep)*mm_per_ustep*1000
        self.entry_deltaZ.setValue(deltaZ)
        self.multipointController.set_deltaZ(deltaZ)

    @TypecheckFunction
    def set_saving_dir(self,_state:Any=None):
        dialog = QFileDialog(options=QFileDialog.DontUseNativeDialog)
        dialog.setWindowModality(Qt.ApplicationModal)
        save_dir_base = dialog.getExistingDirectory(None, "Select Folder")
        if save_dir_base!="":
            self.multipointController.set_base_path(save_dir_base)
            self.lineEdit_savingDir.setText(save_dir_base)
            self.base_path_is_set = True

    @TypecheckFunction
    def toggle_acquisition(self,pressed:bool):
        self.btn_startAcquisition.setChecked(False)

        if self.base_path_is_set == False:
            msg = QMessageBox()
            msg.setText("Please choose base saving directory first")
            msg.exec_()
            return

        if pressed:
            self.btn_startAcquisition.setText(BUTTON_START_ACQUISITION_RUNNING_TEXT)
            QApplication.processEvents() # make sure that the text change is visible

            # @@@ to do: add a widgetManger to enable and disable widget 
            # @@@ to do: emit signal to widgetManager to disable other widgets
            self.setEnabled_all(False)

            # get list of selected channels
            selected_channel_list:List[str]=[item.text() for item in self.list_configurations.selectedItems()]
            # 'sort' list according to current order in widget
            imaging_channel_list=[channel for channel in self.list_configurations.list_channel_names if channel in selected_channel_list]

            experiment_data_target_folder:str=self.lineEdit_experimentID.text()

            self.start_experiment(
                experiment_data_target_folder,
                imaging_channel_list
            ).connect(self.acquisition_is_finished)
        else:
            self.abort_experiment()
            self.acquisition_is_finished()

    @TypecheckFunction
    def acquisition_is_finished(self):
        self.btn_startAcquisition.setText(BUTTON_START_ACQUISITION_IDLE_TEXT)
        QApplication.processEvents() # make sure that the text change is visible
        
        self.setEnabled_all(True)

    @TypecheckFunction
    def setEnabled_all(self,enabled:bool,exclude_btn_startAcquisition:bool=True):
        self.btn_setSavingDir.setEnabled(enabled)
        self.lineEdit_savingDir.setEnabled(enabled)
        self.lineEdit_experimentID.setEnabled(enabled)
        self.entry_deltaX.setEnabled(enabled)
        self.entry_NX.setEnabled(enabled)
        self.entry_deltaY.setEnabled(enabled)
        self.entry_NY.setEnabled(enabled)
        self.entry_deltaZ.setEnabled(enabled)
        self.entry_NZ.setEnabled(enabled)
        self.entry_dt.setEnabled(enabled)
        self.entry_Nt.setEnabled(enabled)
        self.list_configurations.setEnabled(enabled)
        self.checkbox_withAutofocus.setEnabled(enabled)
        if exclude_btn_startAcquisition is not True:
            self.btn_startAcquisition.setEnabled(enabled)

    @TypecheckFunction
    def disable_the_start_aquisition_button(self):
        self.btn_startAcquisition.setEnabled(False)

    @TypecheckFunction
    def enable_the_start_aquisition_button(self):
        self.btn_startAcquisition.setEnabled(True)
