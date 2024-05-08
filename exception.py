# -*- coding: utf-8 -*-
class CMDException(Exception):
    def __init__(self, err_type, err_msg):
        self.err_type = err_type
        self.err_msg = err_msg

    def __str__(self):
        return f"Error: {self.err_type} : {self.err_msg}"
