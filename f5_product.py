#!/usr/bin/env python3
# -*- coding:utf8 -*-
# @Author: Pete.Zhangbin
# @Email: pete19890813@gmail.com
'''
F5 Product Class
'''

from conn_profile import (ConnProfile, shellrecv, recv_expect)
from time import sleep
import re


class F5Device(ConnProfile):
    def __init__(self, host, username, password):
        ConnProfile.__init__(self, host, username, password)
        self.sshconn = self.ParamikoMethod()
        self.shell = self.ParamikoMethod().invoke_shell()
        self.prompt = self.PromptDetect()
        self.version = self.GetVersion()
        self.hostname = self.get_hostname()

    def PromptDetect(self):
        recv_val = shellrecv(self.shell).split('\n')
        if re.search(r'\(tmos.*\)#', recv_val[-1]):
            return 'tmsh'
        elif re.search(r'\s#', recv_val[-1]):
            return 'bash'
    
    def Promptfixed(self, prompt):
        # prompt only support string "bash" and "tmsh"
        if prompt == 'tmsh' and self.prompt == 'bash':
            self.shell('tmsh\n')
            self.prompt = 'tmsh'
        elif prompt == 'bash' and self.prompt == 'tmsh':
            self.shell.send("run util bash\n")
            self.prompt == 'bash'
        else:
            raise ValueError("给定的参数'prompt'值{!r}值错误".format(prompt))

    def GetVersion(self):
        if self.prompt == 'tmsh':
            self.shell.send(
                "show /sys version|grep -E '[[:space:]]+Version'\n")
            return re.search(
                r'\d+\.\d+\.\d+', 
                shellrecv(self.shell)).group()
        elif self.prompt == 'bash':
            self.shell.send(
                "cat /etc/issue|egrep '^BIG-IP[[:space:]][0-9]'\n")
            return re.search(
                r'\d+\.\d+\.\d+', 
                shellrecv(self.shell)).group()
    
    def get_hostname(self):
        self.Promptfixed('bash')
        self.shell.send("echo $HOSTNAME\n")
        return shellrecv(self.shell).split('\n')[-2].strip('\r')

    def generateUCS(self):
        self.shell.send(
            "tmsh save sys ucs $(date +%Y%m-%H%M%S)\n")
        recv = recv_expect(self.shell, r'saved\.')
        return re.search(
            r'(.+)/([^/]+\.ucs)\sis\ssaved', recv).groups()
    
    def SFTPBackup(self, backup_file):
        sftp_client = self.sshconn.open_sftp()
        fname, path = self.generateUCS()
        remotepath = '/'.join((fname, path))
        sftp_client.get(remotepath, backup_file)