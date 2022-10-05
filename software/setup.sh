echo "installing prerequisite software packages"
sudo usermod -aG dialout $USER # allow communication with arduino boards without superuser access
sudo apt update
sudo apt install -y tree curl git micro htop # basic tools that should be installed
sudo apt install -y python3-pip python3-pyqtgraph python3-pyqt5 # squid software dependencies
sudo apt install -y libreoffice virtualenv make gcc build-essential libgtk-3-dev openjdk-11-jdk-headless default-libmysqlclient-dev libnotify-dev libsdl2-dev # dependencies for cellprofiler

echo "installing cellprofiler"
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH=$PATH:/home/ubuntu/.local/bin

cd ~

# the microscopy software does not work inside a virtualenv
pip3 install --upgrade setuptools pip
pip3 install pyqt5 pyqtgraph scipy numpy==1.23 matplotlib qtpy pyserial pandas imageio opencv-python opencv-contrib-python lxml crc # python dependencies for squid software

virtualenv orange_venv
source orange_venv/bin/activate
pip3 install --upgrade setuptools pip
pip3 install orange3

virtualenv cellprofiler_venv
source cellprofiler_venv/bin/activate
pip3 install numpy==1.23 matplotlib qtpy pyserial pandas imageio opencv-python opencv-contrib-python lxml crc # python dependencies for squid software, installed into cellprofiler virtualenv
wget https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-20.04/wxPython-4.1.0-cp38-cp38-linux_x86_64.whl
pip3 install wxPython-4.1.0-cp38-cp38-linux_x86_64.whl
pip3 install cellprofiler==4.2.4 # install cellprofiler into virtualenv (requires numpy to be installed before start of this command, otherwise installation of python-javabridge will fail)

echo "installing microscope software and firmware"
cd ~/Downloads
git clone https://github.com/hongquanli/octopi-research # download squid software and firmware repo
# from https://forum.squid-imaging.org/t/setting-up-arduino-teensyduino-ide-for-uploading-firmware/36
echo "downloading arduino software" # required to flash firmware onto arduino boards (not to use them)
curl https://downloads.arduino.cc/arduino-1.8.19-linux64.tar.xz -o arduino-1.8.19.tar.xz
tar -xf arduino-1.8.19.tar.xz
echo "installing arduino udev rules" # for arduino board communication
curl https://www.pjrc.com/teensy/00-teensy.rules -o 00-teensy.rules 
sudo cp 00-teensy.rules /etc/udev/rules.d/
echo "installing teensyduino board package"
curl https://www.pjrc.com/teensy/td_157/TeensyduinoInstall.linux64 -o teensyduino-install.linux64
chmod +x teensyduino-install.linux64
./teensyduino-install.linux64 --dir=arduino-1.8.19
cd arduino-1.8.19
echo "installing arduino software"
chmod +x install.sh
sudo ./install.sh

echo "manual instructions: in the now open window, manually comment #include 'def_octopi.h' and uncomment #include 'def_octopi_80120.h', then switch to correct board (teensy 4.1) then install the packages PacketSerial and FastLED (both in Tools), then flash firmware"
cd ~/Downloads/octopi-research/firmware/octopi_firmware_v2/main_controller_teensy41
arduino main_controller_teensy41.ino
echo "copying basic configuration" # needs manual tweaks to be used with HCS software
cd ~/Downloads/octopi-research/software
cp configurations/configuration_HCS_v2.txt configuration.txt
echo "installing camera driver"
cd ~/Downloads/octopi-research/software/drivers\ and\ libraries/daheng\ camera/Galaxy_Linux-x86_Gige-U3_32bits-64bits_1.2.1911.9122
echo -e "\ny\nEn\n" | sudo ./Galaxy_camera.run
cd ~/Downloads/octopi-research/software

echo "done"

echo '
run_microscope() {
  cd ~/Downloads/octopi-research/software
  python3 main.py
}
run_hcs() {
  cd ~/Downloads/octopi-research/software
  python3 main_hcs.py
}
run_cellprofiler() {
  source ~/cellprofiler_venv/bin/activate
  python3 -m cellprofiler
}
run_orange() {
  source ~/orange_venv/bin/activate
  python3 -m Orange.canvas
}
' >> ~/.bashrc
source ~/.bashrc

echo '[Desktop Entry]
Type=Application
Terminal=false
Name=cellprofiler
Icon=utilities-terminal
Exec=~/Documents/cellprofiler.sh
Categories=Application;
' > ~/Desktop/cellprofiler.desktop
echo '[Desktop Entry]
Type=Application
Terminal=true
Name=hcs
Icon=utilities-terminal
Exec=~/Documents/hcs.sh
Categories=Application;
' > ~/Desktop/hcs.desktop
echo '[Desktop Entry]
Type=Application
Terminal=false
Name=orange
Icon=utilities-terminal
Exec=~/Documents/orange.sh
Categories=Application;
' > ~/Desktop/orange.desktop
echo '#!/bin/bash
run_cellprofiler
' > ~/Documents/cellprofiler.sh
echo '#!/bin/bash
run_hcs
sleep 10
' > ~/Documents/hcs.sh
echo '#!/bin/bash
run_orange
' > ~/Documents/orange.sh
chmod +x ~/Desktop/orange.desktop ~/Desktop/hcs.desktop ~/Desktop/cellprofiler.desktop ~/Documents/cellprofiler.sh ~/Documents/orange.sh ~/Documents/hcs.sh


