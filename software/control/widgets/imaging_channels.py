from typing import Optional, Callable, List, Dict
from enum import Enum
import time

from qtpy.QtCore import Qt, QEvent
from qtpy.QtWidgets import QMainWindow, QWidget, QSizePolicy, QApplication

from control._def import MACHINE_CONFIG, TriggerMode, WELLPLATE_NAMES, WellplateFormatPhysical, WELLPLATE_FORMATS, Profiler
TRIGGER_MODES_LIST=list(TriggerMode)
from control.gui import ObjectManager, HBox, VBox, TabBar, Tab, Button, Dropdown, Label, FileDialog, FILTER_JSON, BlankWidget, Dock, SpinBoxDouble, SpinBoxInteger, Checkbox, Grid, GridItem, flatten, format_seconds_nicely
from control.core import Core, ReferenceFile, CameraWrapper
from control.core.configuration import Configuration, ConfigurationManager
import control.widgets as widgets
from control.widgets import ComponentLabel
from control.typechecker import TypecheckFunction

import numpy

BRIGHTNESS_ADJUST_MIN:float=0.1
BRIGHTNESS_ADJUST_MAX:float=5.0

CONTRAST_ADJUST_MIN:float=0.1
CONTRAST_ADJUST_MAX:float=5.0

FPS_MIN=1.0
FPS_MAX=30.0 # documentation for MER2-1220-32U3M-W90 says 32.5 fps is max, but we likely will never reach that with the manual trigger method that we use

CHANNEL_COLORS={
    0:"grey", # bf led full
    1:"grey", # bf led left half
    2:"grey", # bf led right half
    15:"darkRed", # 730
    13:"red", # 638
    14:"green", # 561
    12:"blue", # 488
    11:"purple", # 405
}

class ImagingChannels:
    live_display:widgets.ImageDisplayWindow
    live_config:QWidget
    channel_display:widgets.ImageArrayDisplayWindow
    channel_config:QWidget

    def __init__(self,
        configuration_manager:ConfigurationManager,
        camera_wrapper:CameraWrapper,

        on_live_status_changed:Optional[Callable[[],bool]]=None,
    ):
        self.configuration_manager = configuration_manager
        self.camera_wrapper=camera_wrapper
        self.camera=camera_wrapper.camera

        self.on_live_status_changed=on_live_status_changed

        self.interactive_widgets=ObjectManager()

        self.channel_display=widgets.ImageArrayDisplayWindow(self.configuration_manager)

        self.imaging_mode_config_managers:Dict[int,Configuration]=dict()

        imaging_modes_widget_list=[]
        imaging_modes_wide_widgets=[]
        for config_num,config in enumerate(self.configuration_manager.configurations):
            config_manager=ObjectManager()

            imaging_modes_wide_widgets.extend([
                GridItem(
                    Label(config.name,tooltip=config.automatic_tooltip(),text_color=CHANNEL_COLORS[config.illumination_source]).widget,
                    row=config_num*2,colSpan=2
                ),
                GridItem(
                    config_manager.snap == Button(ComponentLabel.BTN_SNAP_LABEL,tooltip=ComponentLabel.BTN_SNAP_TOOLTIP,
                        on_clicked=lambda btn_state,c=config: self.snap_single(btn_state,config=self.configuration_manager.config_by_name(c.name))
                    ).widget,
                    row=config_num*2,column=2,colSpan=2
                )
            ])

            imaging_modes_widget_list.extend([
                [
                    GridItem(None,colSpan=4),
                    Label(ComponentLabel.ILLUMINATION_LABEL,tooltip=ComponentLabel.ILLUMINATION_TOOLTIP).widget,
                    config_manager.illumination_strength == SpinBoxDouble(
                        minimum=0.1,maximum=100.0,step=0.1,
                        default=config.illumination_intensity,
                        tooltip=ComponentLabel.ILLUMINATION_TOOLTIP,
                        on_valueChanged=[
                            lambda val,c=config: self.configuration_manager.config_by_name(c.name).set_illumination_intensity(val),
                            self.configuration_manager.save_configurations,
                        ]
                    ).widget,
                ],
                [   
                    Label(ComponentLabel.EXPOSURE_TIME_LABEL,tooltip=ComponentLabel.EXPOSURE_TIME_TOOLTIP).widget,
                    config_manager.exposure_time == SpinBoxDouble(
                        minimum=self.camera.EXPOSURE_TIME_MS_MIN,
                        maximum=self.camera.EXPOSURE_TIME_MS_MAX,step=1.0,
                        default=config.exposure_time_ms,
                        tooltip=ComponentLabel.EXPOSURE_TIME_TOOLTIP,
                        on_valueChanged=[
                            lambda val,c=config: self.configuration_manager.config_by_name(c.name).set_exposure_time(val),
                            self.configuration_manager.save_configurations,
                        ]
                    ).widget,
                    Label(ComponentLabel.ANALOG_GAIN_LABEL,tooltip=ComponentLabel.ANALOG_GAIN_TOOLTIP).widget,
                    config_manager.analog_gain == SpinBoxDouble(
                        minimum=0.0,maximum=24.0,step=0.1,
                        default=config.analog_gain,
                        tooltip=ComponentLabel.ANALOG_GAIN_TOOLTIP,
                        on_valueChanged=[
                            lambda val,c=config: self.configuration_manager.config_by_name(c.name).set_analog_gain(val),
                            self.configuration_manager.save_configurations,
                        ]
                    ).widget,
                    Label(ComponentLabel.CHANNEL_OFFSET_LABEL,tooltip=ComponentLabel.CHANNEL_OFFSET_TOOLTIP).widget,
                    config_manager.z_offset == SpinBoxDouble(
                        minimum=-30.0,maximum=30.0,step=0.1,
                        default=config.channel_z_offset,
                        tooltip=ComponentLabel.CHANNEL_OFFSET_TOOLTIP,
                        on_valueChanged=[
                            lambda val,c=config: self.configuration_manager.config_by_name(c.name).set_offset(val),
                            self.configuration_manager.save_configurations,
                        ]
                    ).widget,
                ]
            ])

            self.imaging_mode_config_managers[config.mode_id]=config_manager

        def create_snap_selection_popup(
            configuration_manager,
            channel_included_in_snap_all_flags,
            parent,
        ):
            somewidget=QMainWindow(parent)

            vbox_widgets=[
                Label("Tick the channels you want to image.\n(this menu will not initiate imaging)")
            ]

            for config_i,config in enumerate(configuration_manager.configurations):
                def toggle_selection(i):
                    channel_included_in_snap_all_flags[i]=not channel_included_in_snap_all_flags[i]

                vbox_widgets.append(Checkbox(config.name,checked=channel_included_in_snap_all_flags[config_i],on_stateChanged=lambda _btn,i=config_i:toggle_selection(i)))
                            
            somewidget.setCentralWidget(VBox(*vbox_widgets).widget)
            somewidget.show()

        self.channel_included_in_snap_all_flags=[True for c in self.configuration_manager.configurations]

        self.snap_channels=HBox(
            self.interactive_widgets.snap_all_button == Button(
                ComponentLabel.BTN_SNAP_ALL_LABEL,
                tooltip=ComponentLabel.BTN_SNAP_ALL_TOOLTIP,
                on_clicked=self.snap_selected
            ).widget,
            self.interactive_widgets.snap_all_channel_selection == Button(
                ComponentLabel.BTN_SNAP_ALL_CHANNEL_SELECT_LABEL,
                tooltip=ComponentLabel.BTN_SNAP_ALL_CHANNEL_SELECT_TOOLTIP,
                on_clicked=lambda _btn:create_snap_selection_popup(
                    configuration_manager=self.configuration_manager,
                    channel_included_in_snap_all_flags=self.channel_included_in_snap_all_flags,
                    parent=self.channel_config,
                )
            ).widget,
            self.interactive_widgets.snap_all_with_offset_checkbox == Checkbox(
                label=ComponentLabel.BTN_SNAP_ALL_OFFSET_CHECKBOX_LABEL,
                tooltip=ComponentLabel.BTN_SNAP_ALL_OFFSET_CHECKBOX_TOOLTIP
            ).widget,
        ).widget
        self.channel_config=Dock(
            Grid(
                *flatten([
                    imaging_modes_widget_list,
                    imaging_modes_wide_widgets
                ])
            ).widget,
            "Imaging mode settings"
        ).widget
        self.live_display=widgets.ImageDisplayWindow()
        self.live_config=Dock(
            VBox(
                self.interactive_widgets.imageEnhanceWidget == HBox(
                    self.interactive_widgets.imageBrightnessAdjust == HBox(
                        Label("View Brightness:"),
                        SpinBoxDouble(
                            minimum=BRIGHTNESS_ADJUST_MIN,
                            maximum=BRIGHTNESS_ADJUST_MAX,
                            default=1.0,
                            step=0.1,
                            on_valueChanged=self.set_brightness,
                        )
                    ).layout,
                    self.interactive_widgets.imageContrastAdjust == HBox(
                        Label("View Contrast:"),
                        SpinBoxDouble(
                            minimum=CONTRAST_ADJUST_MIN,
                            maximum=CONTRAST_ADJUST_MAX,
                            default=1.0,
                            step=0.1,
                            on_valueChanged=self.set_contrast,
                        )
                    ).layout,
                    self.interactive_widgets.histogramLogScaleCheckbox == Checkbox(
                        label="Histogram Log scale",
                        checked=Qt.Checked,
                        tooltip="Display Y-Axis of the histogram with a logrithmic scale? (uses linear scale if disabled/unchecked)",
                        on_stateChanged=self.set_histogram_log_scale,
                    ),
                ).widget,
                HBox(
                    self.interactive_widgets.live_button == Button(ComponentLabel.LIVE_BUTTON_IDLE_TEXT,checkable=True,checked=False,tooltip=ComponentLabel.LIVE_BUTTON_TOOLTIP,on_clicked=self.toggle_live).widget,
                    self.interactive_widgets.live_channel_dropdown == Dropdown(items=[config.name for config in self.configuration_manager.configurations],current_index=0).widget,
                    Label("max. FPS",tooltip=ComponentLabel.FPS_TOOLTIP),
                    self.interactive_widgets.live_fps == SpinBoxDouble(minimum=FPS_MIN,maximum=FPS_MAX,step=0.1,default=5.0,num_decimals=1,tooltip=ComponentLabel.FPS_TOOLTIP).widget,
                ),
            ).widget,
            "Live Imaging"
        ).widget

    @TypecheckFunction
    def get_all_interactive_widgets(self)->List[QWidget]:
        return [
            self.snap_channels,
            self.channel_config,

            self.interactive_widgets.imageEnhanceWidget,
            self.interactive_widgets.live_button,
            self.interactive_widgets.live_channel_dropdown,
            self.interactive_widgets.live_fps,
        ]
    
    def set_channel_configurations(self,new_configs:List[Configuration]):
        """
        load new configurations
        
        this just overwrites the settings for existing configurations, it does not influence the order of acquisition or add/remove channels
        i.e.:
            1. if a channel exists in the program but not in the config file, it will be left unchanged
            2. if a channel does not exist in the program but does exist in the config file, it will not be loaded into the program
        """
        for config in new_configs:
            config_exists_in_program=config.mode_id in self.imaging_mode_config_managers
            if config_exists_in_program:
                self.imaging_mode_config_managers[config.mode_id].illumination_strength.setValue(config.illumination_intensity)
                self.imaging_mode_config_managers[config.mode_id].exposure_time.setValue(config.exposure_time_ms)
                self.imaging_mode_config_managers[config.mode_id].analog_gain.setValue(config.analog_gain)
                self.imaging_mode_config_managers[config.mode_id].z_offset.setValue(config.channel_z_offset)

            overwrote_present_config=False
            for present_config in self.configuration_manager.configurations:
                if present_config.mode_id==config.mode_id:
                    present_config.illumination_intensity=config.illumination_intensity
                    present_config.exposure_time_ms=config.exposure_time_ms
                    present_config.analog_gain=config.analog_gain
                    present_config.channel_z_offset=config.channel_z_offset

                    overwrote_present_config=True
                    break

            assert config_exists_in_program==overwrote_present_config

            if not overwrote_present_config:
                print("! warning (?) - could not load imaging channel {config.name} from a config file because it does not exist in the program. (this should not happen.)")


    def get_channel_configurations(self)->List[Configuration]:
        return self.configuration_manager.configurations

    def toggle_live(self,btn_pressed):
        if btn_pressed:
            if not self.on_live_status_changed is None:
                self.on_live_status_changed(True)

            self.stop_requested=False

            channel_index=self.interactive_widgets.live_channel_dropdown.currentIndex()
            live_config=self.configuration_manager.configurations[channel_index]

            max_fps=self.interactive_widgets.live_fps.value()
            min_time_between_images=1.0/max_fps

            last_image_time=0.0
            with self.camera_wrapper.ensure_streaming():
                while not self.stop_requested:
                    time_since_last_image=time.monotonic()-last_image_time
                    while time_since_last_image<min_time_between_images:
                        time.sleep(5e-3)
                        QApplication.processEvents()
                        time_since_last_image=time.monotonic()-last_image_time

                    last_image_time=time.monotonic()
                    self.snap_single(_btn_state=None,config=live_config)
                    QApplication.processEvents()

            if not self.on_live_status_changed is None:
                self.on_live_status_changed(False)
        else:
            self.stop_requested=True

    def snap_selected(self,_btn_state):
        with self.camera_wrapper.ensure_streaming():
            for config_i,config in enumerate(self.configuration_manager.configurations):
                if self.channel_included_in_snap_all_flags[config_i]:
                    image=self.snap_single(_btn_state=None,config=config)
                    self.channel_display.display_image(image,channel_index=config.illumination_source)

    def snap_single(self,_btn_state,config:Configuration,profiler:Optional[Profiler]=None)->numpy.ndarray:
        with Profiler("do_snap",parent=profiler) as dosnapprof:
            image=self.camera_wrapper.live_controller.snap(config=config,profiler=dosnapprof)
        with Profiler("display",parent=profiler):
            self.live_display.display_image(image,name=config.name)
        return image

    def set_brightness(self,new_value):
        print("stub def set_brightness(self,new_value):")
    def set_contrast(self,new_value):
        print("stub def set_contrast(self,new_value):")
    def set_histogram_log_scale(self,new_value):
        print("stub def set_histogram_log_scale(self,new_value):")
