#! /usr/bin/env python
"""Routines for KAUST extension of Basestation
"""
import sys
import os
from scipy.io import netcdf
from BaseNetCDF import *
import numpy as np
import time
import glob
import BaseOpts
from BaseLog import *
import FileMgr
from CalibConst import getSGCalibrationConstants
import MakeDiveProfiles
import BaseGZip
import zipfile
import CommLog
import Utils
import Conf
import LogFile
import collections
import Base
import LogFile

dive_gps_position = collections.namedtuple('dive_gps_position', ['gps_lat_one', 'gps_lon_one', 'gps_time_one',
                                                                 'gps_lat_start', 'gps_lon_start', 'gps_time_start',
                                                                 'gps_lat_end', 'gps_lon_end', 'gps_time_end', 'dive_num'])
surface_pos = collections.namedtuple('surface_pos', ['gps_fix_lon', 'gps_fix_lat', 'gps_fix_time', 'dive_num', 'call_cycle'])

__version__ = filter(str.isdigit, "$Revision: 3731 $")

m_per_deg = 111120.

# Setup the config file section and contents
make_kaust_section = 'makekaust'
make_kaust_default_dict = {'color' : ['00ffff', None]}


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

    make_kaust_conf = Conf.conf(make_kaust_section, make_kaust_default_dict)
    if(make_kaust_conf.parse_conf_file(base_opts.config_file_name) and base_opts.config_file_name):
        log_error("Count not process %s - continuing with defaults" % base_opts.config_file_name)
    make_kaust_conf.dump_conf_vars()

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
            if(session.gps_fix != None and session.gps_fix.isvalid ):
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
            fo.write('nc_files_created:\n')
            fo.write(str(nc_files_created))
            fo.write('\n')
            fo.write('processed_other_files:\n')
            fo.write(str(processed_other_files))
            fo.write('\n')
            log_name = 'p%03d%04d.log' % (instrument_id, last_surface_position.dive_num)
            fo.write(log_name)
            # TODO: target (from log)
            # TODO: $ERRORS,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
            # $TGT_NAME,End
            # TODO: reason (from log)
            # $STATE,3849,end dive,TARGET_DEPTH_EXCEEDED)
            # TODO: distance to target (from log)
            dive_nc_file.close()
            # finalize the data structures

        # find log file
        #log_name = 'p%03d%04d.log' % (instrument_id, last_surface_position.dive_num)

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
