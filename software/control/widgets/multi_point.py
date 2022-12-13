# qt libraries
from qtpy.QtCore import Qt, QModelIndex, QSize, Signal, QEvent
from qtpy.QtWidgets import QFrame, QPushButton, QLineEdit, QDoubleSpinBox, \
    QSpinBox, QListWidget, QGridLayout, QCheckBox, QLabel, QAbstractItemView, \
    QComboBox, QHBoxLayout, QMessageBox, QFileDialog, QProgressBar, QDesktopWidget, \
    QWidget, QTableWidget, QSizePolicy, QTableWidgetItem, QApplication
from qtpy.QtGui import QIcon, QMouseEvent

from control._def import *

from typing import Optional, Union, List, Tuple, Callable
from collections import namedtuple

from control.core import MultiPointController, ConfigurationManager
from control.typechecker import TypecheckFunction
from control.gui import *

BUTTON_START_ACQUISITION_IDLE_TEXT="Start Acquisition"
BUTTON_START_ACQUISITION_RUNNING_TEXT="Abort Acquisition"

AF_CHANNEL_TOOLTIP="set channel that will be used for autofocus measurements"
IMAGE_FORMAT_TOOLTIP="change file format for images acquired with the multi point acquisition function"
compression_tooltip="enable image file compression (not supported for bmp)"
SOFTWARE_AUTOFOCUS_TOOLTIP="enable autofocus for multipoint acquisition\nfor each well the autofocus will be calculated in the channel selected below"

dx_tooltip="acquire grid of images (Nx images with dx mm in between acquisitions; dx does not matter if Nx is 1)\ncan be combined with dy/Ny and dz/Nz and dt/Nt for a total of Nx * Ny * Nz * Nt images"
dy_tooltip="acquire grid of images (Ny images with dy mm in between acquisitions; dy does not matter if Ny is 1)\ncan be combined with dx/Nx and dz/Nz and dt/Nt for a total of Nx*Ny*Nz*Nt images"
dz_tooltip="acquire z-stack of images (Nz images with dz µm in between acquisitions; dz does not matter if Nz is 1)\ncan be combined with dx/Nx and dy/Ny and dt/Nt for a total of Nx*Ny*Nz*Nt images"
dt_tooltip="acquire time-series of 'Nt' images, with 'dt' seconds in between acquisitions (dt does not matter if Nt is 1)\ncan be combined with dx/Nx and dy/Ny and dz/Nz for a total of Nx*Ny*Nz*Nt images"

class MultiPointWidget(QFrame):
    @property
    def multipointController(self)->MultiPointController:
        return self.hcs_controller.multipointController
    @property
    def configurationManager(self)->ConfigurationManager:
        return self.hcs_controller.configurationManager

    def __init__(self,
        hcs_controller,
        start_experiment:Callable[[str,List[str]],Optional[Signal]],
        abort_experiment:Callable[[],None]
    ):
        """ start_experiment callable may return signal that is emitted on experiment completion"""
        super().__init__()
        
        self.hcs_controller = hcs_controller
        self.start_experiment=start_experiment
        self.abort_experiment=abort_experiment

        self.base_path_is_set = False

        if True: # add image saving options (path where to save)
            self.btn_setSavingDir = Button('Browse',default=False).widget
            self.btn_setSavingDir.setIcon(QIcon('icon/folder.png'))
            self.btn_setSavingDir.clicked.connect(self.set_saving_dir)
            
            self.lineEdit_savingDir = QLineEdit()
            self.lineEdit_savingDir.setReadOnly(True)
            self.lineEdit_savingDir.setText('Choose a base saving directory')

            self.lineEdit_savingDir.setText(MACHINE_DISPLAY_CONFIG.DEFAULT_SAVING_PATH)
            self.multipointController.set_base_path(MACHINE_DISPLAY_CONFIG.DEFAULT_SAVING_PATH)
            self.base_path_is_set = True

            self.lineEdit_experimentID = QLineEdit()

            self.image_compress_widget=QCheckBox()
            self.image_compress_widget.stateChanged.connect(self.set_image_compression)
            self.image_compress_widget.setToolTip(compression_tooltip)

            self.image_compress_widget_container=HBox(
                Label("compression",tooltip=compression_tooltip),
                self.image_compress_widget
            ).layout

            self.image_format_widget=Dropdown(
                items=["BMP","TIF"],
                current_index=list(ImageFormat).index(Acquisition.IMAGE_FORMAT),
                tooltip=IMAGE_FORMAT_TOOLTIP,
                on_currentIndexChanged=self.set_image_format
            ).widget

        if True: # add imaging grid configuration options
            self.entry_deltaX = SpinBoxDouble(minimum=0.0,maximum=5.0,step=0.1,default=self.multipointController.deltaX,num_decimals=3,keyboard_tracking=False).widget
            self.entry_deltaX.valueChanged.connect(self.set_deltaX)

            self.entry_NX = SpinBoxInteger(minimum=1,maximum=10,step=1,keyboard_tracking=False,on_valueChanged=[
                self.set_NX,
                lambda v:self.grid_changed("x",v)
            ]).widget
            self.set_NX(self.multipointController.NX)

            self.entry_deltaY = SpinBoxDouble(minimum=0.0,step=0.1,num_decimals=3,keyboard_tracking=False,
                on_valueChanged=self.set_deltaY
            ).widget
            self.entry_deltaY.setValue(self.multipointController.deltaY)
            
            self.entry_NY = SpinBoxInteger(minimum=1,maximum=10,step=1,keyboard_tracking=False,on_valueChanged=[
                self.set_NY,
                lambda v:self.grid_changed("y",v)
            ]).widget
            self.set_NY(self.multipointController.NY)

            self.entry_deltaZ = SpinBoxDouble(minimum=0.0,step=0.2,default=self.multipointController.deltaZ,num_decimals=3,keyboard_tracking=False,
                on_valueChanged=self.set_deltaZ
            ).widget
            
            self.entry_NZ = SpinBoxInteger(minimum=1,step=1,keyboard_tracking=False,
                on_valueChanged=self.set_NZ
            ).widget
            self.set_NZ(self.multipointController.NZ)
            
            self.entry_dt = SpinBoxDouble(minimum=0.0,step=1.0,default=self.multipointController.deltat,num_decimals=3,keyboard_tracking=False,
                on_valueChanged=self.multipointController.set_deltat
            ).widget

            self.entry_Nt = SpinBoxInteger(minimum=1,step=1,keyboard_tracking=False,
                on_valueChanged=self.set_Nt
            ).widget
            self.set_Nt(self.multipointController.Nt)

        self.list_configurations = QListWidget()
        self.list_configurations.list_channel_names=[mc.name for mc in self.configurationManager.configurations]
        self.list_configurations.addItems(self.list_configurations.list_channel_names)
        self.list_configurations.setSelectionMode(QAbstractItemView.MultiSelection) # ref: https://doc.qt.io/qt-5/qabstractitemview.html#SelectionMode-enum
        self.list_configurations.setDragDropMode(QAbstractItemView.InternalMove) # allow moving items within list
        self.list_configurations.model().rowsMoved.connect(self.channel_list_rows_moved)

        if True: # add autofocus related stuff
            self.checkbox_withAutofocus = QCheckBox('Software AF')
            self.checkbox_withAutofocus.setToolTip(SOFTWARE_AUTOFOCUS_TOOLTIP)
            self.checkbox_withAutofocus.setChecked(MACHINE_DISPLAY_CONFIG.MULTIPOINT_SOFTWARE_AUTOFOCUS_ENABLE_BY_DEFAULT)
            self.checkbox_withAutofocus.stateChanged.connect(self.set_software_af_flag)

            channel_names=[microscope_configuration.name for microscope_configuration in self.configurationManager.configurations]
            self.af_channel_dropdown=Dropdown(
                items=channel_names,
                current_index=channel_names.index(self.multipointController.autofocus_channel_name),
                tooltip=AF_CHANNEL_TOOLTIP,
                on_currentIndexChanged=lambda index:setattr(MUTABLE_MACHINE_CONFIG,"MULTIPOINT_AUTOFOCUS_CHANNEL",channel_names[index])
            ).widget

            self.set_software_af_flag(MACHINE_DISPLAY_CONFIG.MULTIPOINT_SOFTWARE_AUTOFOCUS_ENABLE_BY_DEFAULT)

            self.checkbox_laserAutofocs = QCheckBox('Laser AF')
            self.checkbox_laserAutofocs.setChecked(MACHINE_DISPLAY_CONFIG.MULTIPOINT_LASER_AUTOFOCUS_ENABLE_BY_DEFAULT)
            self.checkbox_laserAutofocs.stateChanged.connect(self.multipointController.set_laser_af_flag)
            self.hcs_controller.set_laser_af_flag(MACHINE_DISPLAY_CONFIG.MULTIPOINT_LASER_AUTOFOCUS_ENABLE_BY_DEFAULT)

            self.btn_startAcquisition = Button(BUTTON_START_ACQUISITION_IDLE_TEXT,checkable=True,checked=False,on_clicked=self.toggle_acquisition).widget

            grid_multipoint_acquisition_config=Grid(
                [self.checkbox_withAutofocus],
                [self.af_channel_dropdown],
                [self.checkbox_laserAutofocs],
                [self.btn_startAcquisition],
            ).widget

        # layout
        grid_line0 = Grid([
            QLabel('Saving Path'),
            self.lineEdit_savingDir,
            self.btn_setSavingDir,
        ])

        grid_line1 = Grid([
            QLabel('Experiment ID'),
            self.lineEdit_experimentID,
            self.image_compress_widget_container,
            self.image_format_widget,
        ])

        qtlabel_dx=Label('dx (mm)',tooltip=dx_tooltip).widget
        qtlabel_Nx=Label('Nx',tooltip=dx_tooltip).widget
 
        qtlabel_dy=Label('dy (mm)',tooltip=dy_tooltip).widget
        qtlabel_Ny=Label('Ny',tooltip=dy_tooltip).widget
 
        qtlabel_dz=Label('dz (um)',tooltip=dz_tooltip).widget
        qtlabel_Nz=Label('Nz',tooltip=dz_tooltip).widget
 
        qtlabel_dt=Label('dt (s)',tooltip=dt_tooltip).widget
        qtlabel_Nt=Label('Nt',tooltip=dt_tooltip).widget

        self.well_grid_selector=None
        self.grid_changed("x",self.multipointController.NX)
        self.grid_changed("y",self.multipointController.NY)
        assert not self.well_grid_selector is None
 
        self.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Minimum)

        self.progress_bar=QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(0)

        grid_line2 = Grid(
            [ qtlabel_Nx, self.entry_NX, qtlabel_dx, self.entry_deltaX,],
            [ qtlabel_Ny, self.entry_NY, qtlabel_dy, self.entry_deltaY,],
            [ qtlabel_Nz, self.entry_NZ, qtlabel_dz, self.entry_deltaZ,],
            [ qtlabel_Nt, self.entry_Nt, qtlabel_dt, self.entry_dt, ],

            GridItem(self.well_grid_selector,0,4,4,1)
        )

        grid_line3 = HBox( self.list_configurations, grid_multipoint_acquisition_config )

        self.grid = Grid(
            [grid_line0],
            [grid_line1],
            [grid_line2],
            [grid_line3],
            [self.progress_bar],
        )
        self.setLayout(self.grid.layout)

    @TypecheckFunction
    def set_image_format(self,index:int):
        Acquisition.IMAGE_FORMAT=list(ImageFormat)[index]
        if Acquisition.IMAGE_FORMAT==ImageFormat.TIFF:
            self.image_compress_widget.setDisabled(False)
        else:
            self.image_compress_widget.setDisabled(True)
            self.image_compress_widget.setCheckState(False)

    @TypecheckFunction
    def set_image_compression(self,state:Union[int,bool]):
        if type(state)==int:
            state=bool(state)

        if state:
            if Acquisition.IMAGE_FORMAT==ImageFormat.TIFF:
                Acquisition.IMAGE_FORMAT=ImageFormat.TIFF_COMPRESSED
            else:
                raise Exception("enabled compression even though current image file format does not support compression. this is a bug.")
        else:
            if Acquisition.IMAGE_FORMAT==ImageFormat.TIFF_COMPRESSED:
                Acquisition.IMAGE_FORMAT=ImageFormat.TIFF
            else:
                raise Exception("disabled compression while a format that is not compressed tiff was selected. this is a bug.")

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
        size=QDesktopWidget().width()*0.06
        nx=self.multipointController.NX
        ny=self.multipointController.NY

        num_columns=nx
        num_rows=ny

        if self.well_grid_selector is None:
            self.well_grid_selector=BlankWidget(height=size,width=size,background_color="black",children=[])
            self.well_grid_selector.setFixedSize(size,size)

        if dimension=="x":
            num_columns=new_value
        elif dimension=="y":
            num_rows=new_value
        elif dimension=="z":
            pass
        elif dimension=="t":
            pass
        else:
            raise Exception()

        assert num_columns==nx
        assert num_rows==ny

        self.well_grid_items_selected=[
            [
                False 
                for c 
                in range(num_columns)
            ]
            for r 
            in range(num_rows)
        ]
        self.well_grid_items=[
            [
                None
                for c 
                in range(num_columns)
            ]
            for r 
            in range(num_rows)
        ]

        # 1px between items
        item_width=int((size-(nx-1))//nx)
        item_height=int((size-(ny-1))//ny)
        for c in range(num_columns):
            for r in range(num_rows):
                new_item=BlankWidget(
                    height=item_height,
                    width=item_width,
                    offset_top=r*item_height+r,
                    offset_left=c*item_width+c,
                    on_mousePressEvent=lambda event_data,r=r,c=c:self.toggle_well_grid_selection(event_data,row=r,column=c)
                )
                self.well_grid_items[r][c]=new_item
                self.toggle_well_grid_selection(event_data=None,row=r,column=c)

        self.well_grid_selector.set_children(flatten(self.well_grid_items))

    def toggle_well_grid_selection(self,event_data,row:int,column:int):
        grid_item=self.well_grid_items[row][column]
        if self.well_grid_items_selected[row][column]:
            grid_item.background_color="red"
            grid_item.generate_stylesheet()
            self.well_grid_items_selected[row][column]=False
        else:
            grid_item.background_color="green"
            grid_item.generate_stylesheet()
            self.well_grid_items_selected[row][column]=True

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
            # @@@ to do: add a widgetManger to enable and disable widget 
            # @@@ to do: emit signal to widgetManager to disable other widgets
            self.setEnabled_all(False)

            # get list of selected channels
            selected_channel_list:List[str]=[item.text() for item in self.list_configurations.selectedItems()]
            # 'sort' list according to current order in widget
            imaging_channel_list=[channel for channel in self.list_configurations.list_channel_names if channel in selected_channel_list]

            experiment_data_target_folder:str=self.lineEdit_experimentID.text()

            experiment_finished_signal=self.start_experiment(
                experiment_data_target_folder,
                imaging_channel_list
            )

            if experiment_finished_signal is None:
                self.setEnabled_all(True)
                QApplication.processEvents() # make sure that the GUI is up to date
                return

            self.btn_startAcquisition.setText(BUTTON_START_ACQUISITION_RUNNING_TEXT)
            QApplication.processEvents() # make sure that the text change is visible

            experiment_finished_signal.connect(self.acquisition_is_finished)
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
        for item in [
            self.btn_setSavingDir,
            self.lineEdit_savingDir,
            self.lineEdit_experimentID,
            self.entry_deltaX,
            self.entry_NX,
            self.entry_deltaY,
            self.entry_NY,
            self.entry_deltaZ,
            self.entry_NZ,
            self.entry_dt,
            self.entry_Nt,
            self.list_configurations,
            self.checkbox_withAutofocus,
        ]:
            item.setEnabled(enabled)
            
        if exclude_btn_startAcquisition is not True:
            self.btn_startAcquisition.setEnabled(enabled)

    @TypecheckFunction
    def disable_the_start_aquisition_button(self):
        self.btn_startAcquisition.setEnabled(False)

    @TypecheckFunction
    def enable_the_start_aquisition_button(self):
        self.btn_startAcquisition.setEnabled(True)
