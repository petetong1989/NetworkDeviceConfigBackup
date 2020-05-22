#!/usr/bin/env python3
# -*- coding:utf8 -*-
# @Author: Pete.Zhangbin
# @Email: pete19890813@gmail.com

'''
目前该脚本的原理为通过SSH登陆设备设定相关参数，第一次使用SCP，SFTP或API尝试备份，
失败后第二次尝试FTP备份(并非所有设备都会尝试FTP备份，视设备支持情况而定)
1、通过函数 main_interact 展现交互式界面；
2、通过调用函数 unity_process 函数完成备份过程
3、通过调用函数 backup_fuc 来执行备份操作

注意事项：
# 未对 telnet 进行支持
# 目前支持：
    思科设备(思科IOS，WLC，NEXUS，ASA以及UCS FI)，
    F5(测试型号F5 BIGIP 3900，版本号11.5.1)，
    博科FC交换机(测试型号DS-300， 版本号Fabric OS v6.3.2b)

Useage:...新人通常不喜欢写过多注释:p
'''

from time import (time, sleep, strftime, localtime)
from port_scan import multiple_scan
from ftp_server import FTP_Server
from cisco_product import CiscoDevice
from f5_product import F5Device
from broadcom_product import broadcomDevice
from multiprocessing import Process
from logging import basicConfig as logconfig
from logging import warning as warn
from logging import (info, debug, error)
import getpass
import socket
import re
import os


timestamp = strftime("%Y%m%d%H%M%S", localtime(time()))
dateformat = '%m/%d/%Y %I:%M:%S %p'
MessageFormat = '%(asctime)s %(levelname)s: %(message)s'
logconfig(format=MessageFormat, datefmt=dateformat, level=20)


class unity_backup:
    def __init__(self, *hosts, backuppath='.'):
        if not isinstance(hosts, (tuple, list)) \
            or not isinstance(backuppath, str):
            raise ValueError("某个给定的选项类型错误，请更正")
        if hosts:
            self.hosts, self.manufactor, self.username, self.password = hosts
            self.manufactor.upper()
        else:
            self.hosts = hosts
        self.backuppath = backuppath
        self.manufactorlist = ['CISCO', 'F5', 'BROADCOM']
    
    def unity_process(self):
        while True:
            if self.hosts:
                get_hosts = self.verify_IP(self.hosts)
            else: get_hosts = self.main_interact()
            if get_hosts == 'break': break
            elif get_hosts == 'conintue': continue
            ProcessedIPs = self.ProcessIPs(get_hosts)  
            if ProcessedIPs == []:
                raise Exception("对IP地址处理完毕后未发现存在可使用的合法IP！")
            if not self.manufactor in self.manufactorlist:
                warn("所提供的所属厂商不存在！"); break
            info("开始执行备份...")
            self.ftpserv_fuc(
                ftpuser='pete', ftppass='pete19890813',
                ftppath=self.backuppath)
            self.backup_fuc(ProcessedIPs)
            self.FTP_Proc.terminate()
            break

    def main_interact(self):
        IP = input("请输入需要备份配置的设备地址/网段 > ")
        if IP == "exit":
            return 'break'
        elif IP == "":
            return 'conintue'
        elif IP == 'clear':
            if os.name == 'nt': os.system('cls')
            else: os.system('clear')    
            return 'conintue'
        if re.match(r'(\d{1,3}\.){3}\d{1,3}($|/\d{1,2}$)', IP):
            detected_IP, _ = self.verify_IP(IP)
            if _ > 0: return 'conintue'
            if len(detected_IP) > 1:
                print(">>> 根据提供的{!r}探测到如下可访问的IP:\n{}".format(
                    IP, ', '.join(detected_IP)))
                select_IP = input("\n请输入确认需要备份的设备IP(使用逗号隔开) > ")
                match_result = re.match(
                    r'((\d{1,3}\.){3}\d{1,3},\s?)*(\d{1,3}\.){3}(\d{1,3})$', select_IP)
                split_IP = re.split(r',\s?', select_IP)
                diff = list(set(select_IP).difference(detected_IP))
                if match_result and diff != []:
                    self.manufactor = input("该设备所属厂商 > ").upper()
                    self.username = input("用户名: ")
                    self.password = getpass.getpass("密  码: ")
                    return split_IP
                else:
                    print(">>> 输入IP地址错误！'{}'不存在于已扫描到的IP地址中".format(
                        ', '.join(diff)))
                    return 'conintue'
            elif len(detected_IP) == 1:
                self.manufactor = input("该设备所属厂商 > ").upper()
                self.username = input("用户名: ")
                self.password = getpass.getpass("密  码: ")
                return detected_IP
        else:
            print(">>> 非法IP地址，IP地址书写错误！\n")
            return 'conintue'
    
    def verify_IP(self, IP):
        info("正在探测{!r}...".format(IP))
        IP_alive = multiple_scan(IP) if multiple_scan(IP) != [] else None
        if not IP_alive:
            warn("地址/网段{!r}不存在可备份主机, 或者均无法访问！".format(IP))
            return 'device unaccessable', 1
        return IP_alive, 0
        
    def ProcessIPs(self, IPs):
        if isinstance(IPs, str):
            split_symbol = re.search(r'([^\s\.\d/])', IPs)
            IPs = IPs.replace(' ', '').split(split_symbol.group())\
            if split_symbol else IPs.split()
        elif not isinstance(IPs, list):
            raise ValueError('某个给定的选项类型错误，请更正!')
        for IP in IPs:
            Pattern = r'(2[0-5][0-4]|1\d\d|\d\d|[0-9])'
            type_A = r'10\.{0}\.{0}\.{0}/?\d?\d?'.format(Pattern)
            type_B = r'172\.([1[6-9]|2\d|31)\.{0}\.{0}/?\d?\d?'.format(Pattern)
            type_C = r'192\.168\.{0}\.{0}/?\d?\d?'.format(Pattern)
            MatchIP = re.search(
                r'{0}|{1}|{2}'.format(type_A, type_B, type_C), IP).group()
            yield MatchIP

    def get_selfIP(self, conn_ip):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((conn_ip, 22))
            self_ip = s.getsockname()[0]
        finally:
            s.close()
        return self_ip

    def ftpserv_fuc(self, **ftpinfo):
        self.ftpuser = ftpinfo["ftpuser"]
        self.ftppass = ftpinfo["ftppass"]
        self.ftppath = ftpinfo["ftppath"]
        FTP = FTP_Server(self.ftpuser, self.ftppass,
            self.ftppath,
            permission='elradfmwMT',
            log=False)
        self.FTP_Proc = Process(target=FTP.EnableFTPServer, args='')
        self.FTP_Proc.start()

    def Cisco_SCPAPI_backup(self, host):
        if self.Cisco.Product == 'Cisco UCSM':
            self.Cisco.UCSAPIBackup('{0}_{1}_{2}.xml'.format(
            self.Cisco.hostname, host, timestamp))
        else:
            self.Cisco.SCPBackup(
                'running-config', 
                '{0}_{1}_{2}'.format(
                    self.Cisco.hostname, host, timestamp))
            info('设备{!r}备份成功!'.format(host))
    
    def Cisco_FTP_backup(self, host):
        self_IP = self.get_selfIP(host)
        Status = self.Cisco.FTPBackup(
            self_IP,
            '{0}_{1}_{2}'.format(
                self.Cisco.hostname, host, timestamp),
            self.ftpuser,
            self.ftppass)
        if Status == 'BackupSuccess':
            info('设备{!r}备份成功!'.format(host))
            self.Cisco.temPage_len(False)
        else:
            self.Cisco.temPage_len(False)
            raise Exception('备份失败，备份对象内部错误！')
    
    def F5_SFTP_backup(self, host):
        self.F5.SFTPBackup('{0}_{1}_{2}.ucs'.format(
            self.F5.hostname, host, timestamp))
        info('设备{!r}备份成功!'.format(host))

    def Broadcom_FTP_backup(self, host):
        self_IP = self.get_selfIP(host)
        Status = self.Broadcom.FTPBackup(
            self_IP,'{}_{}_{}.txt'.format(
                self.Broadcom.hostname, host, timestamp), 
            self.ftpuser, self.ftppass)
        if Status == 'BackupSuccess':
            info('设备{!r}备份成功!'.format(host))
        else:
            raise Exception('备份失败，备份对象内部错误！')

    def backup_fuc(self, hosts):
        for host in hosts:
            info('开始备份设备{!r}'.format(host))
            try:
                if self.manufactor == "CISCO":
                    self.Cisco = CiscoDevice(host, self.username, self.password)
                    try:
                        self.Cisco_SCPAPI_backup(host)
                    except Exception as e:
                        # raise Exception(e)
                        warn('尝试SCP或API备份失败，开始尝试FTP备份。')
                        self.Cisco_FTP_backup(host)
                        continue
                elif self.manufactor == 'F5':
                    self.F5 = F5Device(host, self.username, self.password)
                    self.F5_SFTP_backup(host)
                elif self.manufactor == 'BROADCOM':
                    self.Broadcom = broadcomDevice(host, self.username, self.password)
                    self.Broadcom_FTP_backup(host)
            except Exception as e:
                # raise Exception
                error('{!r}备份失败, 错误信息：{}'.format(host, e.args[0]))
                continue
        

if __name__ == "__main__":
    Backup = unity_backup()
    # sleep(1)
    try:
        Backup.unity_process()
    except Exception as e:
        Backup.FTP_Proc.terminate()
        raise Exception(e)
    except KeyboardInterrupt:
        error("程序被使用'Ctrl+C'强制退出！")