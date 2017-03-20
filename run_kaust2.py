import kaust2
import os
import sys


sys.path.insert(0, r'/Users/steinks/data/Glider/Seaglider/Software_Update_rev66-12_base2-09/Base-2.09')
log_name = 'p2130036.log'
cap_name = 'p2130036.cap'
path = '/Users/steinks/data/Glider/Seaglider/Transfer/Incoming/sg213/'
log_file_name = os.path.join(path, log_name)
cap_file_name = os.path.join(path, cap_name)
mail_content = kaust2.MailContent()
print 'Fill from log: '+ log_file_name
mail_content.fill_from_log(log_file_name, 0, 213, 50)
mail_content.fill_from_cap(cap_file_name)
mail_content.dump()
