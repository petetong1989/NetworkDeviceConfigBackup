#!/usr/bin/env python3
# -*- coding:utf8 -*-
# @Author: Pete.Zhangbin
# @Email: pete19890813@gmail.com
'''
SCRIPT DESCRIPTION
'''


from paramiko.client import (SSHClient, AutoAddPolicy)
from paramiko import Transport
from time import (sleep, time)
import re


class ConnProfile:
    def __init__(self, ip, username, password):
        self.ip = ip
        self.username = username
        self.password = password

    def ParamikoMethod(self):
        trans = Transport((self.ip, 22))        
        trans.connect(username=self.username, password=self.password)
        paramiko_client = SSHClient()
        paramiko_client.set_missing_host_key_policy(AutoAddPolicy())
        paramiko_client._transport = trans
        return paramiko_client


def shellrecv(shell, delay=3):
    # This is shellrecv
    recv_value = []
    while True:
        if shell.recv_ready():
            recv_value.append(shell.recv(65535).decode('utf-8'))
        elif not shell.recv_ready():
            sleep(delay)
            if shell.recv_ready():
                continue
            break
    # print(''.join(recv_value))
    if recv_value:
        return ''.join(recv_value)

def recv_expect(shell, expect, *, delay=180):
    time_now = time()
    recv_list = []
    while True:
        recv = shellrecv(shell)
        if not recv:
            if time() - time_now < float(delay):
                continue
            else: return None
        elif re.search(r'{0}'.format(expect), recv):
            recv_list.append(recv)
            return ''.join(recv_list)
        else: recv_list.append(recv)