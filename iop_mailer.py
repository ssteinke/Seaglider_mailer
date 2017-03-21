#! /usr/bin/env python
"""IOP mail extension for Seaglider Basestation
   Author: Sebastian Steinke, 21.03.2017
"""
import sys
import os
from scipy.io import netcdf
import BaseNetCDF
import numpy as np
import time
import BaseOpts
from BaseLog import *
import FileMgr
from CalibConst import getSGCalibrationConstants
import CommLog as CommLog
import Utils as Utils
import Conf
import collections
import Base as Base
import re
import ConfigParser
import io


surface_pos = collections.namedtuple('surface_pos', ['gps_fix_lon', 'gps_fix_lat', 'gps_fix_time', 'dive_num', 'call_cycle'])


class MailContent:
    """Object representing content for automated mail
    """
    def __init__(self):
        self.glider = None
        self.mission = None
        self.dive = None
        self.call_cycle = None
        self.gps_time = None
        self.gps_position = None
        self.comm_gps_time = None
        self.comm_gps_position = None
        self.comm_dive_call_cycle = None
        self.target_depth = None
        self.max_depth = None
        self.end_dive_reason = None
        self.target = None
        self.target_latLon = None
        self.distance_target = None
        self.altimeter_ping = 'no ping'
        self.altimeter_bottom_depth = None
        self.errors = None
        self.critical_msg = None
        self.log_file = None
        self.nc_file = None

        self.error_buffer_overrun = None
        self.error_TT8 = None
        self.error_CFOpeningFiles = None
        self.error_CFWritingFiles = None
        self.error_CFClosingFiles = None
        self.retries_CFOpeningFiles = None
        self.retries_CFWritingFiles = None
        self.retries_CFClosingFiles = None
        self.error_pit = None
        self.error_rol = None
        self.error_vbd = None
        self.retries_pit = None
        self.retries_rol = None
        self.retries_vbd = None
        self.error_noGPSFix = None
        self.error_sensor_timeout = None
        self.mails = None


    def dump(self, fo=sys.stdout):
        """Dumps out the structure
        """
        #if self.mails != None:
        #    print >>fo, "Mails: %s" % (self.mails)
        if self.glider != None and self.mission != None:
            print >>fo, "Summary for Glider: %s, mission: %s" % (self.glider, self.mission)
        else:
            if self.glider != None:
                print >>fo, "Summary for Glider: %s" % (self.glider)
            if self.mission != None:
                print >>fo, "mission: %s" % (self.mission)
        print >>fo, "\n*** Latest communication session: ****"
        if self.comm_gps_time != None:
            print >>fo, "GPS time: %s" % (self.comm_gps_time)
        if self.comm_dive_call_cycle != None:
            print >>fo, "Dive and call cycle: %s" % (self.comm_dive_call_cycle)
        if self.comm_gps_position != None:
            print >>fo, "GPS position: %s" % (self.comm_gps_position)
        print >>fo, "\n*** Latest dive: ****"
        if self.log_file != None:
            print >>fo, "log_file: %s" % (self.log_file)
        if self.nc_file != None:
            print >>fo, "nc_file: %s" % (self.nc_file)
        if self.dive != None:
            print >>fo, "Dive: %s" % (self.dive)
        if self.call_cycle != None:
            print >>fo, "Call_cycle: %s" % (self.call_cycle)
        if self.gps_time != None:
            print >>fo, "%s" % (self.gps_time)
        if self.gps_position != None:
            print >>fo, "%s" % (self.gps_position)
        if self.target_depth != None:
            print >>fo, "Target depth [m]: %s" % (self.target_depth)
        if self.max_depth != None:
            print >>fo, "Max. depth [m]: %d" % (self.max_depth)
        if self.end_dive_reason != None:
            print >>fo, "End of dive reason: %s" % (self.end_dive_reason)
        if self.target != None and self.target_latLon != None:
            print >>fo, "On way to target: %s at %s, %s" % (self.target, self.target_latLon[0], self.target_latLon[1])
        if self.distance_target != None:
            print >>fo, "Distance to target [m]: %s" % (self.distance_target)
        if self.altimeter_ping != None:
            print >>fo, "Altimeter ping: %s" % (self.altimeter_ping)
        if self.altimeter_bottom_depth != None:
            print >>fo, "Altimeter bottom depth: %s" % (self.altimeter_bottom_depth)
        if self.error_buffer_overrun != None:
            print >>fo, "Error buffer overrun: %s" % (self.error_buffer_overrun)
        if self.error_TT8 != None:
            print >>fo, "Error TT8: %s" % (self.error_TT8)
        if self.error_CFOpeningFiles != None:
            print >>fo, "Error CF opening files: %s" % (self.error_CFOpeningFiles)
        if self.error_CFWritingFiles != None:
            print >>fo, "Error CF writing files: %s" % (self.error_CFWritingFiles)
        if self.error_CFClosingFiles != None:
            print >>fo, "Error CF closing files: %s" % (self.error_CFClosingFiles)
        if self.retries_CFOpeningFiles != None:
            print >>fo, "Retries CF opening files: %s" % (self.retries_CFOpeningFiles)
        if self.retries_CFWritingFiles != None:
            print >>fo, "Retries CF writing files: %s" % (self.retries_CFWritingFiles)
        if self.retries_CFClosingFiles != None:
            print >>fo, "Retries CF closing files: %s" % (self.retries_CFClosingFiles)
        if self.error_pit != None:
            print >>fo, "Error pitch: %s" % (self.error_pit)
        if self.error_rol != None:
            print >>fo, "Error roll: %s" % (self.error_rol)
        if self.error_vbd != None:
            print >>fo, "Error VBD: %s" % (self.error_vbd)
        if self.retries_pit != None:
            print >>fo, "Retries pitch: %s" % (self.retries_pit)
        if self.retries_rol != None:
            print >>fo, "Retries roll: %s" % (self.retries_rol)
        if self.retries_vbd != None:
            print >>fo, "Retries VBD: %s" % (self.retries_vbd)
        if self.error_noGPSFix != None:
            print >>fo, "Error no GPS Fix: %s" % (self.error_noGPSFix)
        if self.error_sensor_timeout != None:
            print >>fo, "Error sensor timeout: %s" % (self.error_sensor_timeout)

        print >>fo, "\n*** Critical errors from capture file (if any): ****"
        if self.critical_msg != None:
            print >>fo, "%s" % (self.critical_msg)
        else:
            print >>fo, "None"


    def fill_from_log(self, logfile):
        """ Get information from log file
        """
        if os.path.isfile(logfile):
            log_info("Reading from log file %s..." % logfile)
            head, tail = os.path.split(os.path.abspath(os.path.expanduser(logfile)))
            self.log_file = tail
            for line in open(logfile, 'r'):
                line = line.strip('\n')
                # TODO: add $D_GRID (to show if bathy or target depth was used)
                if re.search('\$ID,', line):
                    self.glider = line.split(',')[-1]
                if re.search('MISSION', line):
                    self.mission = line.split(',')[-1]
                if re.search('\$DIVE,', line):
                    self.dive = line.split(',')[-1]
                if re.search('_CALLS', line):
                    self.call_cycle = line.split(',')[-1]
                if re.search('TGT_NAME', line):
                    self.target = line.split(',')[-1]
                if re.search('TGT_LATLONG', line):
                    self.target_latLon = line.split(',')[1:]
                if re.search('D_TGT', line):
                    self.target_depth = line.split(',')[-1]
                if re.search('\$ERRORS', line):
                    # Translate numbers into errors/retries
                    self.errors = line.split(',')[1:]
                    str_arr = line.split(',')[1:]
                    if len(str_arr) != 16:
                        log_error("Could not read Errors line from log file. Length != 16. Line: %s" % line,'exc')
                    else:
                        if str_arr[0] != '0':
                            self.error_buffer_overrun = str_arr[0]
                        if str_arr[1] != '0':
                            self.error_TT8 = str_arr[1]
                        if str_arr[2] != '0':
                            self.error_CFOpeningFiles = str_arr[2]
                        if str_arr[3] != '0':
                            self.error_CFWritingFiles = str_arr[3]
                        if str_arr[4] != '0':
                            self.error_CFClosingFiles = str_arr[4]
                        if str_arr[5] != '0':
                            self.retries_CFOpeningFiles = str_arr[5]
                        if str_arr[6] != '0':
                            self.retries_CFWritingFiles = str_arr[6]
                        if str_arr[7] != '0':
                            self.retries_CFClosingFiles = str_arr[7]
                        if str_arr[8] != '0':
                            self.error_pit = str_arr[8]
                        if str_arr[9] != '0':
                            self.error_rol = str_arr[9]
                        if str_arr[10] != '0':
                            self.error_vbd = str_arr[10]
                        if str_arr[11] != '0':
                            self.retries_pit = str_arr[11]
                        if str_arr[12] != '0':
                            self.retries_rol = str_arr[12]
                        if str_arr[13] != '0':
                            self.retries_vbd = str_arr[13]
                        if str_arr[14] != '0':
                            self.error_noGPSFix = str_arr[14]
                        if str_arr[15] != '0':
                            self.error_sensor_timeout = str_arr[15]
                if re.search('MHEAD_RNG_PITCHd_Wd', line):
                    # get distance to target
                    self.distance_target = line.split(',')[2]
                if re.search(',end dive', line):
                    self.end_dive_reason = line.split(',')[-1]
                if re.search('\$ALTIM_BOTTOM_PING,', line):
                    str_arr = line.split(',')
                    if len(str_arr) == 3:
                        # ping and response...
                        self.altimeter_ping = line.split(',')[1]
                        self.altimeter_bottom_depth = float(line.split(',')[1]) + float(line.split(',')[2])
                    elif len(str_arr) == 2:
                        # ping and no response...
                        self.altimeter_ping = line.split(',')[1]
                        self.altimeter_bottom_depth = 'no bottom detected'


    def fill_from_cap(self, capfile):
        """ Get lines with critical messages from capture file
        """
        if os.path.isfile(capfile):
            log_info("Reading from cap file %s..." % capfile)
            for line in open(capfile, 'r'):
                line = line.strip('\n')
                if re.search(',C,', line):
                    if self.critical_msg == None:
                        self.critical_msg = line + '\n'
                    else:
                        self.critical_msg = self.critical_msg + line + '\n'


    def fill_from_comm(self, commfile, base_opts):
        """ Get latest GPS fix from comm.log file
        """
        (comm_log, start_post, _, _) = CommLog.process_comm_log(os.path.join(base_opts.mission_dir, 'comm.log'), base_opts)
        if(comm_log == None):
            log_warning("Could not process comm.log")

        surface_positions = []
        if(comm_log != None):
            for session in comm_log.sessions:
                if(session.gps_fix != None and session.gps_fix.isvalid):
                    surface_positions.append(surface_pos(Utils.ddmm2dd(session.gps_fix.lon),Utils.ddmm2dd(session.gps_fix.lat),time.mktime(session.gps_fix.datetime), session.dive_num, session.call_cycle))
        surface_positions = sorted(surface_positions, key=lambda position: position.gps_fix_time)
        last_surface_position = surface_positions[-1] if len(surface_positions) else None
        if last_surface_position:
            self.comm_dive_call_cycle = "Comm dive: %d:%d" % (last_surface_position.dive_num, last_surface_position.call_cycle)
            self.comm_gps_position = ("GPS Fix: %.4f,  %.4f" % (last_surface_position.gps_fix_lat, last_surface_position.gps_fix_lon))
            self.comm_gps_time = ("Fix time " + str(time.strftime("%H:%M:%S %m/%d/%y %Z",time.gmtime(last_surface_position.gps_fix_time))))
        return comm_log, last_surface_position


    def fill_from_nc(self, nc_name):
        head, tail = os.path.split(os.path.abspath(os.path.expanduser(nc_name)))
        dive_num = int(tail[4:8])
        nc_file_parsable = True
        try:
            nc = Utils.open_netcdf_file(nc_name, 'r')
            status = 1
        except:
            log_error("Unable to open %s" % nc_name,'exc')
            nc_file_parsable = False
            ncf_file_exists = False
            ncf_file_time = 0

        if nc_file_parsable:
            log_debug("Reading data from %s" % nc_name)
            self.nc_file = tail
            gps_lat_start = gps_lon_start = gps_time_start = gps_lat_end = gps_lon_end = gps_time_end = None
            try:
                gps_lat_one = nc.variables['log_gps_lat'][0]
                gps_lon_one = nc.variables['log_gps_lon'][0]
                gps_time_one = nc.variables['log_gps_time'][0]
                gps_lat_start = nc.variables['log_gps_lat'][1]
                gps_lon_start = nc.variables['log_gps_lon'][1]
                gps_time_start = nc.variables['log_gps_time'][1]
                gps_lat_end = nc.variables['log_gps_lat'][2]
                gps_lon_end = nc.variables['log_gps_lon'][2]
                gps_time_end = nc.variables['log_gps_time'][2]
                self.gps_position = "GPS Fix: %.4f,  %.4f" % (gps_lat_end, gps_lon_end)
                self.gps_time = ("Fix time " + str(time.strftime("%H:%M:%S %m/%d/%y %Z",time.gmtime(gps_time_end))))
            except:
                log_error("Could not process %s due to missing variables" % (nc_name))
                log_error(traceback.format_exc())
            try:
                d = nc.variables['depth']
                max_depth = np.nanmax(d[:])
                self.max_depth = max_depth
                # TODO: add some min-max outputs for sensor data (e.g. Temperature) for quick qc check..
            except:
                log_error("Could not process %s due to missing variables" % (nc_name))
                log_error(traceback.format_exc())
            nc.close()


    def read_configuration(self, base_opts):
        cnf_file_name = '.iop_mailer.cnf'
        try:
            cnf_file_name = os.path.join(base_opts.mission_dir, cnf_file_name)
            if(not os.path.exists(cnf_file_name)):
                log_info("No .iop_mailer.cnf file found - skipping .iop_mailer.cnf processing")
            else:
                try:
                    cnf_file = open(cnf_file_name, "r")
                except IOError, exception:
                    log_error("Could not open %s (%s) - no mail sent" % (cnf_file_name,exception.args))
                else:
                    self.mails = []
                    for cnf_line in cnf_file:
                        cnf_line = cnf_line.rstrip()
                        log_debug(".iop_mailer.cnf line = (%s)" % cnf_line)
                        if (cnf_line == ""):
                            continue
                        if(cnf_line[0] != '#'):
                            log_info("Processing .iop_mailer.cnf line (%s)" % cnf_line)
                            email_addr = cnf_line
                            self.mails += [email_addr]

        except Exception:
            log_error("Problems reading information from %s" % cnf_file_name)
            raise


    def send_mail(self, content, base_opts):
        try:
            if self.mails != None:
                for i, mail in enumerate(self.mails):
                    log_info("Sending mail to %s" % mail)
                    subject = "SG%03d dive %03d: summary" % (float(self.glider), float(self.dive))
                    Base.send_email(base_opts, float(self.glider), mail,
                                    subject, content)
        except Exception:
            log_error("Problems sending emails ")
            log_error(traceback.format_exc())
            raise


def main(instrument_id=None, base_opts=None, sg_calib_file_name=None, dive_nc_file_names=None, nc_files_created=None,
         processed_other_files=None, known_mailer_tags=None, known_ftp_tags=None):
    """App to extract data from different basestation files and send result via mail...

    Returns:
        0 for success (although there may have been individual errors in
            file processing).
        Non-zero for critical problems.

    Raises:
        Any exceptions raised are considered critical errors and not expected
    """

    if base_opts is None:
        base_opts = BaseOpts.BaseOptions(sys.argv, 'k',
                                         usage="%prog [Options] ")
    BaseLogger("iop_mailer", base_opts)

    args = BaseOpts.BaseOptions._args

    if(not base_opts.mission_dir):
        print main.__doc__
        return 1

    processing_start_time = time.time()
    log_info("Started processing " + time.strftime("%H:%M:%S %d %b %Y %Z", time.gmtime(time.time())))
    log_info("Config name = %s" % base_opts.config_file_name)

    if(not dive_nc_file_names):
        dive_nc_file_names = MakeDiveProfiles.collect_nc_perdive_files(base_opts)

    content = MailContent()
    # Read data from comm.log
    comm_log, last_surface_position = content.fill_from_comm(os.path.join(base_opts.mission_dir, 'comm.log'), base_opts)

    # Read latest netCDF file
    if(dive_nc_file_names and len(dive_nc_file_names) > 0):
        dive_nc_file_names.sort()
        # Use last dive
        dive_nc_file_name = dive_nc_file_names[-1]
        content.fill_from_nc(dive_nc_file_name)

    if(instrument_id == None):
        if(comm_log != None):
            instrument_id = comm_log.get_instrument_id()
        if(instrument_id < 0 and dive_nc_file_names and len(dive_nc_file_names) > 0):
            instrument_id = FileMgr.get_instrument_id(dive_nc_file_names[0])
        if(instrument_id < 0):
            log_error("Could not get instrument id - bailing out")
            return 1

    # find log file and read information:
    log_name = 'p%03d%04d.log' % (instrument_id, last_surface_position.dive_num)
    log_file_name = os.path.join(base_opts.mission_dir, log_name)
    if os.path.isfile(log_file_name):
        content.fill_from_log(log_file_name)

    content.read_configuration(base_opts)
    dump_file = os.path.join(base_opts.mission_dir, 'iop_mailer.txt')
    try:
        fo = open(dump_file, "w")
    except:
        log_error("Could not open %s" % dump_file)
        log_error(traceback.format_exc())

    content.dump(fo=fo)
    fo.close()
    with open(dump_file, 'r') as content_file:
        mail_content = content_file.read()
    content.send_mail(mail_content, base_opts)

    log_info("Finished processing " + time.strftime("%H:%M:%S %d %b %Y %Z", time.gmtime(time.time())))
    log_info("Run time %f seconds" % (time.time() - processing_start_time))
    return 0

if __name__ == "__main__":
    retval = 1
    os.environ['TZ'] = 'UTC'
    time.tzset()
    try:
        retval = main()
    except Exception:
        log_critical("Unhandled exception in main -- exiting")

    sys.exit(retval)
