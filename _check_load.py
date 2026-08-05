import sys;sys.stdout.reconfigure(encoding='utf-8')
v=open(r'D:\PythonProjects\DesktopWidget\src\main_window.py','r',encoding='utf-8').read()
idx=v.find('def _load_images')
print(v[idx:idx+500])