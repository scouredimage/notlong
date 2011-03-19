import sys
import site
import os

sys.stdout = sys.stderr

ROOT='/opt/shortener_env'

prev_sys_path = list(sys.path)

# Add site-packages of our virtualenv as a site directory
site.addsitedir(ROOT + '/venv/lib/python2.6/site-packages/')

# Add application directory to PYTHONPATH
sys.path.append(ROOT)
sys.path.append(ROOT + '/notlong')

# Reorder sys.path so added directories take precedence
new_sys_path = [p for p in sys.path if p not in prev_sys_path]
for item in new_sys_path:
  sys.path.remove(item)
sys.path[:0] = new_sys_path

# Set Python egg cache directory as apache runs a user:nobody
os.environ['PYTHON_EGG_CACHE'] = ROOT + '/egg.cache'

os.environ['DJANGO_SETTINGS_MODULE'] = 'notlong.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
