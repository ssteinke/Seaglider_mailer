# Seaglider_mailer
Extension for Seaglider AUV basestation (tested with version 2.09). This extension can be triggered from the basestaion via .extensions. It parses different files generated by the basestation and sends an email with a summary of the dive.

## Mail content
The extensions generates a mail with information from different files generated by the basestation:
* comm.log: last GPS fix
* pNNNDDDD.log: Dive specific data (Retries/Errors, GPS Fix, Target depth used, end of dive reason, target used, distance to target, Altimeter data)
* pNNNDDDD.nc: Max. depth reached
* pNNNDDDD.nc: Lines containing critical errors

Example:
```
Summary for Glider: 213, mission: 175

*** Latest communication session: ****
GPS time: Fix time 08:20:03 03/15/17 AST
Dive and call cycle: Comm dive: 77:0
GPS position: GPS Fix: 27.1234,  35.1234

*** Latest dive: ****
log_file: p2130077.log
nc_file: p2130077.nc
Dive: 77
Call_cycle: 0
Fix time 10:34:56 03/11/17 AST
GPS Fix: 27.1234,  35.1234
Target depth [m]: 500
Max. depth [m]: 512
end of dive reason: TARGET_DEPTH_EXCEEDED
On way to target: Midback at 2719.000, 3531.000
Distance to target [m]: 10086
Altimeter ping: no ping
Error TT8: 1
Error roll: 1
Retries roll: 72
Error no GPS Fix: 1

*** Critical errors from capture file (if any): ****
critical_msg: 8122.141,HROLL,C,Roll completed from 0.65 deg (1931) to 57.84 deg (3954) took 13.2 sec 2mA (15mA peak) 26.2Vmin 153.26 AD/sec 528 ticks; 72 retries (37 w/o motion); 1 errors
```

## Requirements
Tested with:
* Base 2.09
* python 2.7

## Install
* drop iop_mailer.py and iop_mailer.cnf into your Basestation directory (e.g. /usr/local/basestation/)
* add your email to .iop_mailer.cnf
```
######################################################################
# Configuration for iop_mailer extension
#
######################################################################
someone@domain.org
someoneelse@domain.org
```
* add iop_mailer.py to the .extensions file in the Seaglider home (/home/sgNNN/)
```
## .extensions file
#
# Extensions listed in this file will be invoked in the order specified
#
# Extensions are listed as file names, not path and no arguments.  Extensions must reside in the
# same directory as the rest of the basestation code
#
MakeKMLLic.py
iop_mailer.py
```
