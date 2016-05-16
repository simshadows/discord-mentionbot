# Thanks to Stack Overflow user `Anurag Uniyal` for the base code.
# Link: http://stackoverflow.com/questions/1057431/loading-all-modules-in-a-fol
#       der-in-python

from os.path import dirname, basename, isfile
import glob

modules = glob.glob(dirname(__file__)+"/*.py")
__all__ = [basename(f)[:-3] for f in modules if isfile(f)]