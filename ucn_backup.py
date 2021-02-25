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
- 思科设备(思科IOS，WLC，NEXUS，ASA以及UCS FI)，
- F5(测试型号F5 BIGIP 3900，版本号11.5.1)，
- 博科FC交换机(测试型号DS-300， 版本号Fabric OS v6.3.2b)
'''

from packages.compnents.port_scan import multiple_scan
from packages.compnents.ftp_server import FTP_Server
from packages.cisco_product import CiscoDevice
from packages.f5_product import F5Device
from packages.broadcom_product import broadcomDevice
from multiprocessing import Process
from packages import *
import dns.resolver as dnsResolver
import getpass
import socket

timestamp = strftime("%Y%m%d%H%M%S", localtime(time()))
dateformat = '%Y-%m-%d %I:%M:%S %p'
MessageFormat = '%(asctime)s %(levelname)s: %(message)s'
logconfig(format=MessageFormat, datefmt=dateformat, level=40)


def dnsreolve(domainName):
    try:
        master_answer = dnsResolver.resolve(domainName, 'A')
        if len(master_answer) > 1:
            return 'failed'
        return master_answer[0].address
    except Exception:
        return 'failed'


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

    def infoGather(self):
        self.manufactor = input("厂  商 (Manufactor): ").upper()
        self.username = input("用户名 (Username): ")
        self.password = getpass.getpass("密  码 (Password): ")
    
    def unity_process(self):
        while True:
            count = 3
            if self.hosts:
                get_hosts = self.verify_IP(self.hosts)
            else: get_hosts = self.main_interact()
            if get_hosts == 'break': break
            elif get_hosts == 'conintue': continue
            while True:
                if get_hosts == ('conintue1', 'scanning'):
                    get_hosts = self.main_interact(scanning=True, continue1=True)
                    if 'conintue1' in get_hosts: continue
                elif get_hosts == 'conintue1':
                    get_hosts = self.main_interact(continue1=True)
                else: break
            ProcessedIPs = self.ProcessIPs(get_hosts)
            if ProcessedIPs == []:
                raise Exception("对IP地址处理完毕后未发现存在可使用的合法IP！")
            if not self.manufactor in self.manufactorlist:
                print("[-] 所提供的所属厂商不存在！"); break
            print("[+] 开始执行备份...")
            self.ftpserv_fuc(
                ftpuser='pete', ftppass='pete19890813',
                ftppath=self.backuppath)
            self.backup_fuc(ProcessedIPs)
            self.FTP_Proc.terminate()
            break

    def main_interact(self, startbackup=False, scanning=False, continue1=False):
        if not continue1:
            IP = input("扫描设备所在网段？输入SKIP或直接回车跳过 > ")
            if IP == "exit":
                return 'break'
            elif IP == "":
                startbackup = True
            elif IP == 'clear':
                if os.name == 'nt': os.system('cls')
                else: os.system('clear')    
                return 'conintue'
            elif re.match(r'skip|SKIP', IP):
                startbackup = True
            elif re.match(r'(\d{1,3}\.){3}\d{1,3}($|/\d{1,2}$)', IP):
                self.detected_IP, _ = self.verify_IP(IP)
                if _ > 0: return 'conintue'
                elif len(self.detected_IP) >= 1:
                    startbackup = True
                    scanning = True
                    print("[+] 根据{!r}探测到如下可访问的IP:".format(IP))
                    ipcount = 0
                    for ip in self.detected_IP:
                        if ip == self.detected_IP[0]:
                            print(' '*4, end='')
                        if ip == self.detected_IP[-1]:
                            print(ip)
                            break
                        print(ip + ',', end=' ')
                        ipcount += 1
                        if ipcount > 6:
                            print('\r')
                            print(' '*4, end='')
                            ipcount = 0 
            else:
                print("[-] 检测到非法字符，请重新输入！\n")
                return 'conintue'
        
        if startbackup or continue1:
            select_IP = input("配置备份设备的IP/FQDN（使用英文逗号隔开）> ")
            match_result = re.match(
                r'((\d{1,3}\.){3}\d{1,3},\s?)*(\d{1,3}\.){3}(\d{1,3})$', select_IP)
            split_IP = re.split(r',\s?|\s', select_IP)
            
            if not match_result:
                split_domains = split_IP
                IPs = []
                for domain in split_domains:
                    ipaddress = dnsreolve(domain)
                    if ipaddress == 'failed':
                        print('[-] DNS解析失败！可能是非法字符或者这个域名不存在！')
                        break
                    IPs.append(ipaddress)
                if IPs != []:
                    self.infoGather()
                    return IPs

            if match_result and scanning:
                diff = list(set(split_IP).difference(self.detected_IP))
                if match_result and not diff:
                    self.infoGather()
                    return split_IP
                else:
                    print("[-] 输入IP地址错误！'{}'不存在于已扫描到的IP地址中".format(
                        ', '.join(diff)))
                    return 'conintue1', 'scanning'
            elif match_result and not scanning:
                self.infoGather()
                return select_IP
            else:
                # print("[-] 非法IP地址，IP地址书写错误！")
                return 'conintue1'
    
    def verify_IP(self, IP):
        print("[+] 正在探测{!r}...".format(IP))
        IP_alive = multiple_scan(IP) if multiple_scan(IP) != [] else None
        if not IP_alive:
            print("[-] 地址/网段{!r}不存在可备份主机, 或者均无法访问！".format(IP))
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
            print('[+] 设备{!r}备份成功!'.format(host))
    
    def Cisco_FTP_backup(self, host):
        self_IP = self.get_selfIP(host)
        Status = self.Cisco.FTPBackup(
            self_IP,
            '{0}_{1}_{2}'.format(
                self.Cisco.hostname, host, timestamp),
            self.ftpuser,
            self.ftppass)
        if Status == 'BackupSuccess':
            print('[+] 设备{!r}备份成功!'.format(host))
            self.Cisco.temPage_len(False)
        else:
            self.Cisco.temPage_len(False)
            raise Exception('备份失败，备份对象内部错误！')
    
    def F5_SFTP_backup(self, host):
        self.F5.SFTPBackup('{0}_{1}_{2}.ucs'.format(
            self.F5.hostname, host, timestamp))
        print('[+] 设备{!r}备份成功!'.format(host))

    def Broadcom_FTP_backup(self, host):
        self_IP = self.get_selfIP(host)
        Status = self.Broadcom.FTPBackup(
            self_IP,'{}_{}_{}.txt'.format(
                self.Broadcom.hostname, host, timestamp), 
            self.ftpuser, self.ftppass)
        if Status == 'BackupSuccess':
            print('[+] 设备{!r}备份成功!'.format(host))
        else:
            raise Exception('备份失败，备份对象内部错误！')

    def backup_fuc(self, hosts):
        for host in hosts:
            print('[+] 开始备份设备{!r}'.format(host))
            try:
                if self.manufactor == "CISCO":
                    self.Cisco = CiscoDevice(host, self.username, self.password)
                    try:
                        self.Cisco_SCPAPI_backup(host)
                    except Exception as e:
                        # raise Exception(e)
                        print('[-] 尝试SCP或API备份失败，开始尝试FTP备份。')
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
                print('[-] {!r}备份失败, 错误信息：{}'.format(host, e.args[0]))
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
        print("\n[-] 程序被手动强制退出！")