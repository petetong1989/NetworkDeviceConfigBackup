#!/usr/bin/env python3
# -*- coding:utf8 -*-
# @Author: Pete.Zhangbin
# @Email: pete19890813@gmail.com
'''
SCRIPT DESCRIPTION
'''


from conn_profile import (ConnProfile, shellrecv, recv_expect)
import re


class broadcomDevice(ConnProfile):
    def __init__(self, ip, username, password):
        ConnProfile.__init__(self, ip, username, password)
        self.sshconn = self.ParamikoMethod()
        self.shell = self.ParamikoMethod().invoke_shell()
        self.PromptStatus = self.PromptHandler()
        if self.PromptStatus == 'password_change_require':
            self.shell.send(chr(3))
        self.hostname = self.get_hostname()
    
    def PromptHandler(self):
        prompt = shellrecv(self.shell)
        if re.search(r'.+:[a-zA-Z]+>', prompt):
            return 'normal_promot'
        elif re.search(r'Please\schange', prompt):
            return 'password_change_require'

    def get_hostname(self):
        self.shell.send("switchname\n")
        return shellrecv(self.shell).split('\n')[-2].strip('\r')

    def FTPBackup(self, ftpaddr, filename, ftpuser, ftppass):
        self.shell.send(
            "configupload -all -ftp {},{},{},{}\n".format(
                ftpaddr, ftpuser, filename, ftppass))
        recv_str = recv_expect(
            self.shell, r'Terminated|configUpload\scomplete')
        if recv_str.find('configUpload complete') > -1:
            return 'BackupSuccess'
        else: return 'BackupFailed'