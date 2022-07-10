import os
import shutil


command = 'pyinstaller -F -i music-notes.ico main10.pyw --noconsole'
os.system(command)
os.remove('main10.spec')
shutil.rmtree('build')
shutil.rmtree('__pycache__')
os.remove('main10.exe')
shutil.move('dist\\main10.exe', os.getcwd())
shutil.rmtree('dist') 