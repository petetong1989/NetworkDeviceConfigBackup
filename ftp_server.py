#!/usr/bin/env python3
# -*- coding:utf8 -*-
# @Author: Pete.Zhangbin
# @Email: pete19890813@gmail.com
'''
This Script is to enable a FTP Server
'''
import logging
import os
import re
import getpass

from pyftpdlib.handlers import FTPHandler
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.servers import ThreadedFTPServer, FTPServer


class MyFTPHandler(FTPHandler):
    def on_file_received(self, file):
        if os.path.basename(file) == file:
            self.server.close_when_done()        

class FTP_Server:
    def __init__(
        self, username, password, homedir, permission='r', log=False, 
            listeningAdd='0.0.0.0'):
        self.username = username
        self.password = password
        self.homedir = homedir
        self.serverstratus = None
        self.authorizer = DummyAuthorizer()
        if log == True:
            logging.basicConfig(
                format='%(asctime)s MESSAGE_TYPE %(levelname)s: %(message)s', 
                datefmt='%m/%d/%Y %I:%M:%S %p',
                # filename=r'.\\pyftpd.log' if os.name == 'nt' else r'./pyftp.log', 
                level=logging.INFO)
        '''
        Read permissions:
        "e" = change directory (CWD, CDUP commands)
        "l" = list files (LIST, NLST, STAT, MLSD, MLST, SIZE commands)
        "r" = retrieve file from the server (RETR command)

        Write permissions:
        "a" = append data to an existing file (APPE command)
        "d" = delete file or directory (DELE, RMD commands)
        "f" = rename file or directory (RNFR, RNTO commands)
        "m" = create directory (MKD command)
        "w" = store a file to the server (STOR, STOU commands)
        "M" = change file mode / permission (SITE CHMOD command) New in 0.7.0
        "T" = change file modification time (SITE MFMT command) New in 1.5.3
        '''
        self.permission = permission
        self.listeningAdd = listeningAdd
        self.UserAdd()
    
    def permission_process(self):
        permlist = []
        for per in ' '.join(self.permission).split():
            if per in permlist:
                continue
            elif re.search(r'[elradfmwlMT]', per):
                permlist.append(per)  
        if permlist:
            self.permission = ''.join(permlist)
        else:
            print("Given permission keyword ERROR!")

    def EnableFTPServer(self):
        handler = MyFTPHandler
        handler.authorizer = self.authorizer
        self.serverstratus = ThreadedFTPServer((self.listeningAdd, 21), handler)
        self.serverstratus.serve_forever()

    def UserAdd(self, username=""):
        if username != "":
            self.username = username
            self.password = getpass.getpass("Please give user {0} a password > ".format(
                username))
            self.permission = input("What is {0}'s permission? > ".format(username))
            self.permission_process()
            self.authorizer.add_user(
                self.username, self.password, self.homedir, perm=self.permission)
        else:
            self.permission_process()
            self.authorizer.add_user(
                self.username, self.password, self.homedir, perm=self.permission)     


if __name__ == "__main__":
    FTP = FTP_Server('pete', 'pete19890813', '.', permission='elradfmwMT', log=True)
    FTP.EnableFTPServer()
