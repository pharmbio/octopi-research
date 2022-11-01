from qtpy.QtCore import Qt, QThread, QObject
from qtpy.QtWidgets import QApplication

# app specific libraries
import control.camera as camera
import control.core as core
import control.microcontroller as microcontroller
from control._def import *

from control.typechecker import TypecheckFunction

from typing import List, Tuple, Callable

class HCSController(QObject):
    def __init__(self):
        super().__init__()

        # load objects
        try:
            self.camera = camera.Camera(rotate_image_angle=MACHINE_CONFIG.ROTATE_IMAGE_ANGLE,flip_image=MACHINE_CONFIG.FLIP_IMAGE)
            self.camera.open()
        except Exception as e:
            print('! camera not detected !')
            raise e

        try:
            self.microcontroller:microcontroller.Microcontroller = microcontroller.Microcontroller(version=MACHINE_CONFIG.CONTROLLER_VERSION)
        except Exception as e:
            print("! microcontroller not detected !")
            raise e

        # reset the MCU
        self.microcontroller.reset()
        
        # configure the actuators
        self.microcontroller.configure_actuators()

        self.configurationManager:    core.ConfigurationManager    = core.ConfigurationManager(filename='./channel_configurations.xml')
        self.streamHandler:           core.StreamHandler           = core.StreamHandler(display_resolution_scaling=MACHINE_DISPLAY_CONFIG.DEFAULT_DISPLAY_CROP/100)
        self.liveController:          core.LiveController          = core.LiveController(self.camera,self.microcontroller,self.configurationManager)
        self.navigationController:    core.NavigationController    = core.NavigationController(self.microcontroller)
        self.slidePositionController: core.SlidePositionController = core.SlidePositionController(self.navigationController,self.liveController)
        self.autofocusController:     core.AutoFocusController     = core.AutoFocusController(self.camera,self.navigationController,self.liveController)
        self.multipointController:    core.MultiPointController    = core.MultiPointController(self.camera,self.navigationController,self.liveController,self.autofocusController,self.configurationManager)
        self.imageSaver:              core.ImageSaver              = core.ImageSaver()

        self.navigationController.home()

        self.num_running_experiments=0

    @TypecheckFunction
    def acquire(self,
        well_list:List[Tuple[int,int]],
        channels:List[str],
        experiment_id:str,
        grid_data={
            'x':{'d':0.9,'N':1},
            'y':{'d':0.9,'N':1},
            'z':{'d':0.9,'N':1},
            't':{'d':0.9,'N':1},
        },
        af_channel:Optional[str]=None,
        plate_type:ClosedSet[int](6,12,24,96,384)=MUTABLE_MACHINE_CONFIG.WELLPLATE_FORMAT,
    )->Optional[QThread]:
        # set objective and well plate type from machine config (or.. should be part of imaging configuration..?)
        # set wells to be imaged <- acquire.well_list argument
        # set grid per well to be imaged
        # set lighting settings per channel
        # set selection and order of channels to be imaged <- acquire.channels argument

        wellplate_format=WELLPLATE_FORMATS[plate_type]

        well_list_names:List[str]=[wellplate_format.well_name(c[0],c[1]) for c in well_list]
        well_list_physical_pos:List[Tuple[float,float]]=[wellplate_format.convert_well_index(c[0],c[1]) for c in well_list]

        for i in well_list_names:
            print(f"{i}")
        for i in well_list_physical_pos:
            print(f"{i}")

        if af_channel is None:
            self.multipointController.set_af_flag(False)
        else:
            assert af_channel in [c.name for c in self.configurationManager.configurations], f"{af_channel} is not a valid (AF) channel"
            self.multipointController.autofocus_channel_name=af_channel
            self.multipointController.set_af_flag(True)
            # TODO change autofocuscontroller settings

        self.multipointController.set_NX(grid_data['x']['N'])
        self.multipointController.set_NY(grid_data['y']['N'])
        self.multipointController.set_NZ(grid_data['z']['N'])
        self.multipointController.set_Nt(grid_data['t']['N'])
        self.multipointController.set_deltaX(grid_data['x']['d'])
        self.multipointController.set_deltaY(grid_data['y']['d'])
        self.multipointController.set_deltaZ(grid_data['z']['d'])
        self.multipointController.set_deltat(grid_data['t']['d'])

        self.multipointController.set_selected_configurations(channels)
        self.multipointController.set_base_path(path="/home/pharmbio/Downloads")
        self.multipointController.prepare_folder_for_new_experiment(experiment_ID=experiment_id) # todo change this to a callback (so that each image can be handled in a callback, not as batch or whatever)

        return self.multipointController.run_experiment((well_list_names,well_list_physical_pos))

    @TypecheckFunction
    def close(self):
        # move the objective to a defined position upon exit
        self.navigationController.move_x(0.1) # temporary bug fix - move_x needs to be called before move_x_to if the stage has been moved by the joystick
        self.microcontroller.wait_till_operation_is_completed(5, 0.005)

        self.navigationController.move_x_to(30.0)
        self.microcontroller.wait_till_operation_is_completed(5, 0.005)

        self.navigationController.move_y(0.1) # temporary bug fix - move_y needs to be called before move_y_to if the stage has been moved by the joystick
        self.microcontroller.wait_till_operation_is_completed(5, 0.005)

        self.navigationController.move_y_to(30.0)
        self.microcontroller.wait_till_operation_is_completed(5, 0.005)

        self.liveController.stop_live()
        self.camera.close()
        self.imageSaver.close()
        self.microcontroller.close()

        QApplication.quit()

    # todo add callbacks to be triggered on image acquisition (e.g. for histograms, saving to disk etc.)
