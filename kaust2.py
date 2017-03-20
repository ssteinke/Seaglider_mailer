#! /usr/bin/env python
"""Routines for KAUST extension of Basestation
"""
import sys
import os
from scipy.io import netcdf
import base.BaseNetCDF
import numpy as np
import time
import base.BaseOpts
import base.BaseLog
import base.FileMgr
from base.CalibConst import getSGCalibrationConstants
#import MakeDiveProfiles
import base.CommLog
import base.Utils
import base.Conf
import collections
import base.Base
import re


# TODO: Remove base.* for all imports
# TODO: Clean (remove config part)
# TODO: Change process to use MailContent

dive_gps_position = collections.namedtuple('dive_gps_position', ['gps_lat_one', 'gps_lon_one', 'gps_time_one',
                                                                 'gps_lat_start', 'gps_lon_start', 'gps_time_start',
                                                                 'gps_lat_end', 'gps_lon_end', 'gps_time_end', 'dive_num'])
surface_pos = collections.namedtuple('surface_pos', ['gps_fix_lon', 'gps_fix_lat', 'gps_fix_time', 'dive_num', 'call_cycle'])

__version__ = filter(str.isdigit, "$Revision: 3731 $")

m_per_deg = 111120.

# Setup the config file section and contents
make_kaust_section = 'makekaust'
make_kaust_default_dict = {'color' : ['00ffff', None]}


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


    def dump(self, fo=sys.stdout):
        """Dumps out the logfile
        """
        # print >>fo, "version: %2.2f" % ( self.version)
        if self.glider != None:
            print >>fo, "glider: %s" % (self.glider)
        if self.mission != None:
            print >>fo, "mission: %s" % (self.mission)
        if self.dive != None:
            print >>fo, "dive: %s" % (self.dive)
        if self.call_cycle != None:
            print >>fo, "call_cycle: %s" % (self.call_cycle)
        if self.gps_time != None:
            print >>fo, "gps_time: %d" % (self.gps_time)
        if self.gps_position != None:
            print >>fo, "gps_position: %d" % (self.gps_position)
        if self.target_depth != None:
            print >>fo, "target_depth [m]: %s" % (self.target_depth)
        if self.max_depth != None:
            print >>fo, "max_depth [m]: %d" % (self.max_depth)
        if self.end_dive_reason != None:
            print >>fo, "end_dive_reason: %s" % (self.end_dive_reason)
        if self.target != None:
            print >>fo, "target: %s" % (self.target)
        if self.target_latLon != None:
            print >>fo, "target_latLon: %s" % (self.target_latLon)
        if self.distance_target != None:
            print >>fo, "distance_target [m]: %s" % (self.distance_target)
        if self.altimeter_ping != None:
            print >>fo, "altimeter_ping: %s" % (self.altimeter_ping)
        if self.altimeter_bottom_depth != None:
            print >>fo, "altimeter_bottom_depth: %s" % (self.altimeter_bottom_depth)
        if self.errors != None:
            print >>fo, "errors: %s" % (self.errors)
        if self.error_buffer_overrun != None:
            print >>fo, "error_buffer_overrun: %s" % (self.error_buffer_overrun)
        if self.error_TT8 != None:
            print >>fo, "error_TT8: %s" % (self.error_TT8)
        if self.error_CFOpeningFiles != None:
            print >>fo, "error_CFOpeningFiles: %s" % (self.error_CFOpeningFiles)
        if self.error_CFWritingFiles != None:
            print >>fo, "error_CFWritingFiles: %s" % (self.error_CFWritingFiles)
        if self.error_CFClosingFiles != None:
            print >>fo, "error_CFClosingFiles: %s" % (self.error_CFClosingFiles)
        if self.retries_CFOpeningFiles != None:
            print >>fo, "retries_CFOpeningFiles: %s" % (self.retries_CFOpeningFiles)
        if self.retries_CFWritingFiles != None:
            print >>fo, "retries_CFWritingFiles: %s" % (self.retries_CFWritingFiles)
        if self.retries_CFClosingFiles != None:
            print >>fo, "retries_CFClosingFiles: %s" % (self.retries_CFClosingFiles)
        if self.error_pit != None:
            print >>fo, "error_pit: %s" % (self.error_pit)
        if self.error_rol != None:
            print >>fo, "error_rol: %s" % (self.error_rol)
        if self.error_vbd != None:
            print >>fo, "error_vbd: %s" % (self.error_vbd)
        if self.retries_pit != None:
            print >>fo, "retries_pit: %s" % (self.retries_pit)
        if self.retries_rol != None:
            print >>fo, "retries_rol: %s" % (self.retries_rol)
        if self.retries_vbd != None:
            print >>fo, "retries_vbd: %s" % (self.retries_vbd)
        if self.error_noGPSFix != None:
            print >>fo, "error_noGPSFix: %s" % (self.error_noGPSFix)
        if self.error_sensor_timeout != None:
            print >>fo, "error_sensor_timeout: %s" % (self.error_sensor_timeout)
        if self.critical_msg != None:
            print >>fo, "critical_msg: %s" % (self.critical_msg)


    def fill_from_log(self, logfile, call_cycle, instrument_id, dive_number):
        if os.path.isfile(logfile):
            for line in open(logfile, 'r'):
                line = line.strip('\n')
                # $D_GRID,900 (bathy or target depth)
                # $GPS,130317,142902,2716.761,3524.448,24,0.9,24,3.9
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
                    self.errors = line.split(',')[1:]
                    str_arr = line.split(',')[1:]
                    if len(str_arr) != 16:
                        print 'error line not 16..'+line
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
                    self.distance_target = line.split(',')[2]
                if re.search(',end dive', line):
                    self.end_dive_reason = line.split(',')[-1]
                if re.search('\$ALTIM_BOTTOM_PING,', line):
                    str_arr = line.split(',')
                    if len(str_arr) == 3:
                        self.altimeter_ping = line.split(',')[1]
                        self.altimeter_bottom_depth = float(line.split(',')[1]) + float(line.split(',')[2])
                    elif len(str_arr) == 2:
                        self.altimeter_ping = line.split(',')[1]
                        self.altimeter_bottom_depth = 'no bottom detected'


    def fill_from_cap(self, capfile):
        if os.path.isfile(capfile):
            for line in open(capfile, 'r'):
                line = line.strip('\n')
                if re.search(',C,', line):
                    if self.critical_msg == None:
                        self.critical_msg = line + '\n'
                    else:
                        self.critical_msg = self.critical_msg + line + '\n'

def extractGPSPositions(dive_nc_file_name, dive_num):
    """ A hack - printDive does this and reads many more variables.  This needs to be expanded and
    printDive needs to work off the data structure this feeds OR it needs to be determined that we can have
    many (1000) netCDF files opened at once.
    """
    try:
        nc = Utils.open_netcdf_file(dive_nc_file_name, 'r')
    except:
        log_error("Could not read %s" % (dive_nc_file_name))
        log_error(traceback.format_exc())
        log_error("Skipping...")
        return dive_gps_position(None, None, None, None, None, None, None, None, None, None)

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
    except:
        log_error("Could not process %s due to missing variables" % (dive_nc_file_name))
        log_error(traceback.format_exc())

    return dive_gps_position(gps_lat_one, gps_lon_one, gps_time_one, gps_lat_start, gps_lon_start, gps_time_start, gps_lat_end, gps_lon_end, gps_time_end, dive_num)


def main(instrument_id=None, base_opts=None, sg_calib_file_name=None, dive_nc_file_names=None, nc_files_created=None,
         processed_other_files=None, known_mailer_tags=None, known_ftp_tags=None):
    """Command line app for ...

    Returns:
        0 for success (although there may have been individual errors in
            file processing).
        Non-zero for critical problems.

    Raises:
        Any exceptions raised are considered critical errors and not expected
    """
    global make_kaust_conf

    if base_opts is None:
        base_opts = BaseOpts.BaseOptions(sys.argv, 'k',
                                         usage="%prog [Options] ")
    BaseLogger("MakeKaust", base_opts) # initializes BaseLog

    args = BaseOpts.BaseOptions._args # positional arguments

    if(not base_opts.mission_dir):
        print main.__doc__
        return 1

    processing_start_time = time.time()
    log_info("Started processing " + time.strftime("%H:%M:%S %d %b %Y %Z", time.gmtime(time.time())))
    log_info("Config name = %s" % base_opts.config_file_name)

    if(sg_calib_file_name == None):
        sg_calib_file_name = os.path.join(base_opts.mission_dir, "sg_calib_constants.m")

    #make_kaust_conf = Conf.conf(make_kaust_section, make_kaust_default_dict)
    #if(make_kaust_conf.parse_conf_file(base_opts.config_file_name) and base_opts.config_file_name):
    #    log_error("Count not process %s - continuing with defaults" % base_opts.config_file_name)
    #make_kaust_conf.dump_conf_vars()

    # Read sg_calib_constants file
    calib_consts = getSGCalibrationConstants(sg_calib_file_name)
    if(not calib_consts):
        log_error("Could not process %s - skipping creation of KAUST file" % sg_calib_file_name)
        return 1

    if(not dive_nc_file_names):
        dive_nc_file_names = MakeDiveProfiles.collect_nc_perdive_files(base_opts)

    (comm_log, start_post, _, _) = CommLog.process_comm_log(os.path.join(base_opts.mission_dir, 'comm.log'), base_opts)
    if(comm_log == None):
        log_warning("Could not process comm.log")

    if((dive_nc_file_names == None or len(dive_nc_file_names) <= 0) and comm_log == None):
        log_critical("No matching netCDF files or comm.log found - exiting")
        return 1

    if(instrument_id == None):
        if(comm_log != None):
            instrument_id = comm_log.get_instrument_id()
        if(instrument_id < 0 and dive_nc_file_names and len(dive_nc_file_names) > 0):
            instrument_id = FileMgr.get_instrument_id(dive_nc_file_names[0])
        if(instrument_id < 0):
            log_error("Could not get instrument id - bailing out")
            return 1

    mission_title = Utils.ensure_basename(calib_consts['mission_title'])
    mission_title_raw = calib_consts['mission_title']

    mission_kaust_name = os.path.join(base_opts.mission_dir,'kaust_mail.txt')

    try:
        fo = open(mission_kaust_name, "w")
    except:
        log_error("Could not open %s" % mission_kaust_name,'exc')
        log_info("Bailing out...")
        return 1

    fo.write("SG%03d %s\n" % (instrument_id, mission_title_raw))
    subject = "SG%03d %s" % (instrument_id, mission_title_raw)

    # Attempt to collect surfacing positions from comm.log
    # Do this here to get any dive0 entries
    surface_positions = []
    if(comm_log != None):
        for session in comm_log.sessions:
            if(session.gps_fix != None and session.gps_fix.isvalid):
                surface_positions.append(surface_pos(Utils.ddmm2dd(session.gps_fix.lon),Utils.ddmm2dd(session.gps_fix.lat),time.mktime(session.gps_fix.datetime), session.dive_num, session.call_cycle))

    # Sort by time
    surface_positions = sorted(surface_positions, key=lambda position: position.gps_fix_time)
    last_surface_position = surface_positions[-1] if len(surface_positions) else None
    # We will see surface positions as heads of drift locations

    dive_gps_positions = {}
    #fo.write('SG%0.3dDives ' % (instrument_id, instrument_id))

    # Pull out the GPS positions
    if(dive_nc_file_names and len(dive_nc_file_names) > 0):
        dive_nc_file_names.sort()

        # GPS positions
        for dive_index in range(len(dive_nc_file_names)):
            dive_nc_file_name = dive_nc_file_names[dive_index]
            head, tail = os.path.split(os.path.abspath(os.path.expanduser(dive_nc_file_name)))
            dive_num = int(tail[4:8])
            dive_gps_positions[dive_num] = extractGPSPositions(dive_nc_file_name, dive_num)


    # Print the last known position outside the tree structure
    if last_surface_position:
        try:
            #fo.write(("Seaglider SG" + str(instrument_id)+ '\n'))
            fo.write(("Dive/CallCycle %d:%d\n" % (last_surface_position.dive_num, last_surface_position.call_cycle)))
            fo.write(("Fix time " + str(time.strftime("%H:%M:%S %m/%d/%y %Z",time.gmtime(last_surface_position.gps_fix_time)))+ '\n'))
            fo.write(("GPS Fix: %.4f, " % last_surface_position.gps_fix_lat))
            fo.write((" %.4f\n" % last_surface_position.gps_fix_lon))

            subject += (", Dive/CallCycle %d:%d" % (last_surface_position.dive_num, last_surface_position.call_cycle))
            subject += (", Fix time " + str(time.strftime("%H:%M:%S %m/%d/%y %Z",time.gmtime(last_surface_position.gps_fix_time))))
        except:
            log_error("Could not print surface position placemark",'exc')
    ###################
    # Remove any dive 0 related positions and resort
    surface_positions = filter(lambda i: i.dive_num != 0, surface_positions)


    if(dive_nc_file_names and len(dive_nc_file_names) > 0):
        dive_nc_file_names.sort()
        # Use last dive
        dive_nc_file_name = dive_nc_file_names[-1]
        head, tail = os.path.split(os.path.abspath(os.path.expanduser(dive_nc_file_name)))
        dive_num = int(tail[4:8])
        # fo.write('SG%03d dive %03d' % (instrument_id, dive_num))
        nc_file_parsable = True # assume the best
        try:
            dive_nc_file = Utils.open_netcdf_file(dive_nc_file_name, 'r')
            try:
                version = getattr(dive_nc_file,'file_version')
            except:
                version = 1.0
            if version <  required_nc_fileversion:
                log_error("%s is a version %.02f netCDF file - this basestation requires %.02f or later" % (nc_dive_file_name, version, required_nc_fileversion))
                dive_nc_file.close() # close the file
                nc_file_parsable = False # can't really trust our inversion scheme so re-read from raw files
                status = 0 # unable to read
            if version < mission_per_dive_nc_fileversion:
                log_info("%s is a version %.02f netCDF file - requires updating to %.02f" % (nc_dive_file_name, version, mission_per_dive_nc_fileversion))
                status = 2 # requires update
            else:
                status = 1 # looks up-to-date
        except: # can't open file
            log_error("Unable to open %s" % dive_nc_file_name,'exc')
            nc_file_parsable = False
            ncf_file_exists = False
            ncf_file_time = 0

        if nc_file_parsable:
            log_debug("Reading data from %s" % dive_nc_file_name)
            d = dive_nc_file.variables['depth']
            max_depth = np.nanmax(d[:])
            fo.write(('Max. depth: %03d' % max_depth))

            fo.write('\n')
            #fo.write('dive_nc_file_names:\n')
            #fo.write(str(dive_nc_file_names))
            #fo.write('nc_files_created:\n')
            #fo.write(str(nc_files_created))
            #fo.write('\n')
            #fo.write('processed_other_files:\n')
            #fo.write(str(processed_other_files))
            #fo.write('\n')
            dive_nc_file.close()

        # find log file
        log_name = 'p%03d%04d.log' % (instrument_id, last_surface_position.dive_num)
        # $STATE,3849,end dive,TARGET_DEPTH_EXCEEDED)
        # TODO: distance to target (from log)
        log_file_name = os.path.join(base_opts.mission_dir, log_name)
        if os.path.isfile(log_file_name):
            fo.write('\nFound log file: '+log_name+'\n')
            for line in open(log_file_name, 'r'):
                if re.search('TGT_NAME', line):
                    fo.write(line)
                if re.search('D_TGT', line):
                    fo.write(line)
                if re.search('ERRORS', line):
                    fo.write(line)
                if re.search('MHEAD_RNG_PITCHd_Wd', line):
                    fo.write(line)
                if re.search('end dive', line):
                    fo.write(line)

    fo.close()
    # Send mail with file as body...
    with open(mission_kaust_name, 'r') as content_file:
        content = content_file.read()
    Base.send_email(base_opts, instrument_id, 'sebastian.steinke@kaust.edu.sa',
                    subject, content)

    #lf = LogFile.parse_log_file(file_name, mission_dir)

    log_info("Finished processing " + time.strftime("%H:%M:%S %d %b %Y %Z", time.gmtime(time.time())))
    log_info("Run time %f seconds" % (time.time() - processing_start_time))
    return 0

if __name__ == "__main__":
    retval = 1

    # Force to be in UTC
    os.environ['TZ'] = 'UTC'
    time.tzset()

    try:
        retval = main()
    except Exception:
        log_critical("Unhandled exception in main -- exiting")

    sys.exit(retval)
