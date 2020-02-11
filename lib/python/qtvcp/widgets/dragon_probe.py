#!/usr/bin/env python
import os
import hal
from PyQt5.QtCore import QProcess, QByteArray
from PyQt5 import QtGui
from qtvcp.core import Action
from qtvcp import logger

ACTION = Action()
LOG = logger.getLogger(__name__)
current_dir =  os.path.dirname(__file__)
SUBPROGRAM = os.path.abspath(os.path.join(current_dir, 'dragon_probe_subprog.py'))

class Probe:
    def __init__(self, halcomp, widgets):
        self.w = widgets
        self.halcomp = halcomp
        self.valid = QtGui.QDoubleValidator(0.0, 999.999, 3)
        self.probe_list = ["OUTSIDE CORNERS", "INSIDE CORNERS", "BOSS and POCKETS", "RIDGE and VALLEY",
                           "EDGE ANGLE", "ROTARY AXIS", "CALIBRATE"]

        self.basic_data = ['probe_tool', 'max_z', 'max_xy', 'xy_clearance', 'z_clearance',
                           'step_off', 'extra_depth', 'probe_feed', 'probe_rapid', 'calibration_offset']
        self.rv_data = ['x_hint', 'y_hint', 'diameter_hint', 'edge_width']
        self.bp_data = ['x_hint_0', 'y_hint_0', 'diameter_hint', 'edge_width']
        self.cal_data = ['cal_diameter', 'cal_x_width', 'cal_y_width']
        self.process_busy = False
        
    def init_widgets(self):
        self.w.cmb_probe_select.activated.connect(self.cmb_probe_select_changed)
        self.w.outside_buttonGroup.buttonClicked.connect(self.probe_btn_clicked)
        self.w.inside_buttonGroup.buttonClicked.connect(self.probe_btn_clicked)
        self.w.skew_buttonGroup.buttonClicked.connect(self.probe_btn_clicked)
        self.w.boss_pocket_buttonGroup.buttonClicked.connect(self.boss_pocket_clicked)
        self.w.ridge_valley_buttonGroup.buttonClicked.connect(self.probe_btn_clicked)
        self.w.cal_buttonGroup.buttonClicked.connect(self.cal_btn_clicked)
        self.w.clear_buttonGroup.buttonClicked.connect(self.clear_results_clicked)
        self.w.probe_help_prev.clicked.connect(self.probe_help_prev_clicked)
        self.w.probe_help_next.clicked.connect(self.probe_help_next_clicked)

        self.w.cmb_probe_select.clear()
        self.w.cmb_probe_select.addItems(self.probe_list)
        self.w.stackedWidget_probe_buttons.setCurrentIndex(0)
        for i in self.basic_data:
            self.w['lineEdit_' + i].setValidator(self.valid)
        for i in self.rv_data:
            self.w['lineEdit_' + i].setValidator(self.valid)
        for i in self.bp_data:
            self.w['lineEdit_' + i].setValidator(self.valid)
        for i in self.cal_data:
            self.w['lineEdit_' + i].setValidator(self.valid)

    def get_prefs(self):
        self.w.lineEdit_probe_tool.setText(str(self.w.PREFS_.getpref('Probe tool', 0, int, 'PROBE OPTIONS')))
        self.w.lineEdit_probe_rapid.setText(str(self.w.PREFS_.getpref('Probe rapid', 10, float, 'PROBE OPTIONS')))
        self.w.lineEdit_max_xy.setText(str(self.w.PREFS_.getpref('Probe max xy', 10, float, 'PROBE OPTIONS')))
        self.w.lineEdit_max_z.setText(str(self.w.PREFS_.getpref('Probe max z', 2, float, 'PROBE OPTIONS')))
        self.w.lineEdit_extra_depth.setText(str(self.w.PREFS_.getpref('Probe extra depth', 0, float, 'PROBE OPTIONS')))
        self.w.lineEdit_step_off.setText(str(self.w.PREFS_.getpref('Probe step off', 10, float, 'PROBE OPTIONS')))
        self.w.lineEdit_probe_feed.setText(str(self.w.PREFS_.getpref('Probe feed', 10, float, 'PROBE OPTIONS')))
        self.w.lineEdit_xy_clearance.setText(str(self.w.PREFS_.getpref('Probe xy clearance', 10, float, 'PROBE OPTIONS')))
        self.w.lineEdit_z_clearance.setText(str(self.w.PREFS_.getpref('Probe z clearance', 10, float, 'PROBE OPTIONS')))
        self.w.lineEdit_edge_width.setText(str(self.w.PREFS_.getpref('Probe edge width', 10, float, 'PROBE OPTIONS')))
        self.start_process()

    def put_prefs(self):
        self.w.PREFS_.putpref('Probe tool', float(self.w.lineEdit_probe_tool.text()), int, 'PROBE OPTIONS')
        self.w.PREFS_.putpref('Probe rapid', float(self.w.lineEdit_probe_rapid.text()), float, 'PROBE OPTIONS')
        self.w.PREFS_.putpref('Probe max xy', float(self.w.lineEdit_max_xy.text()), float, 'PROBE OPTIONS')
        self.w.PREFS_.putpref('Probe max z', float(self.w.lineEdit_max_z.text()), float, 'PROBE OPTIONS')
        self.w.PREFS_.putpref('Probe extra depth', float(self.w.lineEdit_extra_depth.text()), float, 'PROBE OPTIONS')
        self.w.PREFS_.putpref('Probe step off', float(self.w.lineEdit_step_off.text()), float, 'PROBE OPTIONS')
        self.w.PREFS_.putpref('Probe feed', float(self.w.lineEdit_probe_feed.text()), float, 'PROBE OPTIONS')
        self.w.PREFS_.putpref('Probe xy clearance', float(self.w.lineEdit_xy_clearance.text()), float, 'PROBE OPTIONS')
        self.w.PREFS_.putpref('Probe z clearance', float(self.w.lineEdit_z_clearance.text()), float, 'PROBE OPTIONS')
        self.w.PREFS_.putpref('Probe edge width', float(self.w.lineEdit_edge_width.text()), float, 'PROBE OPTIONS')
        self.proc.terminate()

#############################################
# process control
#############################################
    def start_process(self):
        self.proc = QProcess()
        self.proc.setReadChannel(QProcess.StandardOutput)
        self.proc.started.connect(self.process_started)
        self.proc.readyReadStandardOutput.connect(self.read_stdout)
        self.proc.readyReadStandardError.connect(self.read_stderror)
        self.proc.finished.connect(self.process_finished)
        self.proc.start('python {}'.format(SUBPROGRAM))

    def start_probe(self, cmd):
        if self.process_busy is True:
            LOG.error("Probing processor is busy")
            return
        string_to_send = cmd.encode('utf-8') + '\n'
#        print("String to send ", string_to_send)
        self.proc.writeData(string_to_send)
        self.process_busy = True

    def process_started(self):
        LOG.info("Probe subprogram started with PID {}\n".format(self.proc.processId()))

    def read_stdout(self):
        qba = self.proc.readAllStandardOutput()
        line = qba.data().encode('utf-8')
        self.parse_input(line)
        self.process_busy = False

    def read_stderror(self):
        qba = self.proc.readAllStandardError()
        line = qba.data().encode('utf-8')
        self.parse_input(line)

    def process_finished(self, exitCode, exitStatus):
        print("Probe Process signals finished exitCode {} exitStatus {}".format(exitCode, exitStatus))

    def parse_input(self, line):
        self.process_busy = False
        if "ERROR" in line:
            print(line)
        elif "DEBUG" in line:
            print(line)
        elif "INFO" in line:
            print(line)
        elif "COMPLETE" in line:
            LOG.info("Probing routine completed without errors")
            self.show_results()
        else:
            LOG.error("Error parsing return data from sub_processor. Line={}".format(line))

    def send_error(self, w, kind, text):
        message ='ERROR {},{} \n'.format(kind,text)
        self.proc.writeData(message)

# Main button handler routines
    def cmb_probe_select_changed(self, index):
        self.w.stackedWidget_probe_buttons.setCurrentIndex(index)

    def probe_help_prev_clicked(self):
        i = self.w.probe_help_widget.currentIndex()
        if i > 0:
            self.w.probe_help_widget.setCurrentIndex(i - 1)

    def probe_help_next_clicked(self):
        i = self.w.probe_help_widget.currentIndex()
        if i < 5:
            self.w.probe_help_widget.setCurrentIndex(i + 1)

    def probe_btn_clicked(self, button):
        mode = int(self.w.btn_probe_mode.isChecked() is True)
        ngc = button.property('filename').encode('utf-8')
        parms = self.get_parms() + self.get_rv_parms() + '[{}]'.format(mode)
        cmd = "PROBE {} {}".format(ngc, parms)
        self.start_probe(cmd)

    def boss_pocket_clicked(self, button):
        mode = int(self.w.btn_probe_mode.isChecked() is True)
        ngc = button.property('filename').encode('utf-8')
        parms = self.get_parms() + self.get_bp_parms() + '[{}]'.format(mode)
        cmd = "PROBE {} {}".format(ngc, parms)
        self.start_probe(cmd)

    def cal_btn_clicked(self, button):
        mode = int(self.w.btn_probe_mode.isChecked() is True)
        sub = button.property('filename').encode('utf-8')
        if self.w.cal_avg_error.isChecked():
            avg = '[0]'
        elif self.w.cal_x_error.isChecked():
            avg = '[1]'
        else:
            avg = '[2]'
        parms = self.get_parms() + self.get_rv_parms() + '[{}]'.format(mode)
        parms += self.get_cal_parms() + avg
        cmd = "PROBE {} {}".format(ngc, parms)
        self.start_probe(cmd)
        
    def clear_results_clicked(self, button):
        sub = button.property('filename').encode('utf-8')
        cmd = "o< {} > call".format(sub)
        ACTION.CALL_OWORD(cmd)
        self.show_results()

# Helper functions
    def init_hal_pins(self):
        self.halcomp.newpin("x_width", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("y_width", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("avg_diameter", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("edge_angle", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("edge_delta", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("x_minus", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("y_minus", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("z_minus", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("x_plus", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("y_plus", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("x_center", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("y_center", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("cal_offset", hal.HAL_FLOAT, hal.HAL_IN)

    def get_parms(self):
        p = ""
        for i in self.basic_data:
            next = self.w['lineEdit_' + i].text()
            if next == '':
                next = 0.0
            p += '[{}]'.format(next)
        return p

    def get_rv_parms(self):
        p = ""
        for i in self.rv_data:
            next = self.w['lineEdit_' + i].text()
            if next == '':
                next = 0.0
            p += '[{}]'.format(next)
        return p

    def get_bp_parms(self):
        p = ""
        for i in self.bp_data:
            next = self.w['lineEdit_' + i].text()
            if next == '':
                next = 0.0
            p += '[{}]'.format(next)
        return p

    def get_cal_parms(self):
        p = ""
        for i in self.cal_data:
            next = self.w['lineEdit_' + i].text()
            if next == '':
                next = 0.0
            p += '[{}]'.format(next)
        return p

    def show_results(self):
        self.w.status_xminus.setText('{:.3f}'.format(self.halcomp['x_minus']))
        self.w.status_xplus.setText('{:.3f}'.format(self.halcomp['x_plus']))
        self.w.status_xcenter.setText('{:.3f}'.format(self.halcomp['x_center']))
        self.w.status_xwidth.setText('{:.3f}'.format(self.halcomp['x_width']))
        self.w.status_yminus.setText('{:.3f}'.format(self.halcomp['y_minus']))
        self.w.status_yplus.setText('{:.3f}'.format(self.halcomp['y_plus']))
        self.w.status_ycenter.setText('{:.3f}'.format(self.halcomp['y_center']))
        self.w.status_ywidth.setText('{:.3f}'.format(self.halcomp['y_width']))
        self.w.status_z.setText('{:.3f}'.format(self.halcomp['z_minus']))
        self.w.status_angle.setText('{:.3f}'.format(self.halcomp['edge_angle']))
        self.w.status_delta.setText('{:.3f}'.format(self.halcomp['edge_delta']))
        self.w.status_diameter.setText('{:.3f}'.format(self.halcomp['avg_diameter']))

    ##############################
    # required class boiler code #
    ##############################
    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)


