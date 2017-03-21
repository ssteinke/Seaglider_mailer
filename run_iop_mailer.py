import iop_mailer
import os
import sys
import base.BaseOpts as BaseOpts


sys.path.insert(0, r'/Users/steinks/data/Glider/Seaglider/Software_Update_rev66-12_base2-09/Base-2.09')
log_name = 'p2130036.log'
cap_name = 'p2130036.cap'
nc_name = 'p2130036.nc'
path = '/Users/steinks/data/Glider/Seaglider/Transfer/Incoming/sg213/'
log_file_name = os.path.join(path, log_name)
cap_file_name = os.path.join(path, cap_name)
nc_file_name = os.path.join(path, nc_name)
comm_file_name = os.path.join(path, 'comm.log')
mail_content = iop_mailer.MailContent()
mail_content.fill_from_log(log_file_name)
mail_content.fill_from_cap(cap_file_name)
mail_content.fill_from_nc(nc_file_name)
base_opts = BaseOpts.BaseOptions(sys.argv, 'k',
                                 usage="%prog [Options] ")
base_opts.mission_dir = path
mail_content.fill_from_comm(comm_file_name, base_opts)
mail_content.read_configuration(base_opts)
dump_file = 'test.txt'
try:
    fo = open(dump_file, "w")
except:
    print("Could not open %s" % dump_file)

mail_content.dump(fo=fo)
fo.close()
with open(dump_file, 'r') as content_file:
    content = content_file.read()
print content
mail_content.send_mail(content, base_opts)
