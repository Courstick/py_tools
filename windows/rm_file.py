# -*- coding: utf-8 -*-
import os
import stat
import shutil


class RMFileOnWindows(object):

    @staticmethod
    def onerror(func, path, exc_info):
        """
        Error handler for shutil.rmtree.
        """
        if not os.access(path, os.W_OK):
            # Is the error caused by read-only permission?
            os.chmod(path, stat.S_IWUSR)
            func(path)  # try again
        else:
            raise

    def rm(self):
        # path is too long
        shutil.rmtree(f'\\\\?\\{os.getcwd()}', onerror=self.onerror)
