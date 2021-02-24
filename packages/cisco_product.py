#!/usr/bin/env python3
# -*- coding:utf8 -*-
# @Author: Pete.Zhangbin
# @Email: pete19890813@gmail.com
'''
Cisco Product Class
'''

from packages import *
from packages.compnents.conn_profile import (ConnProfile, shellrecv, recv_expect)

class CiscoDevice(ConnProfile):
    def __init__(self, ip, username, password, Product=None):
        ConnProfile.__init__(self, ip, username, password)
        self.sshconn = self.ParamikoMethod()
        self.shell = self.ParamikoMethod().invoke_shell()
        self.PromptStaus = self.PromptHandler()
        if self.PromptStaus == 'WLC_Login':
            self.shell.send('{}\n'.format(username))
            self.shell.send('{}\n'.format(password))
        if Product != None:
            self.Product = Product
        else:
            self.Product = self.ProductDetect()
        if self.Product == 'Cisco UCSM':
            self.UCSMhandle = UcsHandle(ip, username, password)
            self.UCSMhandle.login()
        self.temPage_len()
        self.temWidth()
        self.SCPStatus = False
        self.hostname = self.get_hostname()
    
    def PromptHandler(self):
        prompt = shellrecv(self.shell).split('\n')
        # if re.search(
        #     r'(copied|[Ss]uccess(fully)?|Copy\scomplete)', 
        #     '\n'.join(prompt[-4:])):
        #     return 'Accomplished'
        if 'User:' in prompt[-1]:
            return 'WLC_Login'
        # elif 'Password:' in prompt[-1]:
        #     return 'PW_require'
        elif '/system #' in prompt[-1]:
            return 'UCSM_SysSocpe'
        elif '#' in prompt[-1]:
            return 'UserPriviledgeExec'
        elif '>' in prompt[-1]:
            return 'UserViewExec'
        else:
            return 'Notdetected'

    def ProductDetect(self):
        if self.PromptStaus[0] == 'UserViewExec':
            self.shell.send('enable\n')
            self.shell.send('\nshow inventory\n')
        else:
            self.shell.send('\nshow inventory\n')
            self.shell.send('\nshow system version\n')
        recv_value = shellrecv(self.shell)
        if re.search(r'ASA\d{4}', recv_value):
            return 'Cisco ASA'
        elif re.search(r'CISCO\d{4}/K\d{1}', recv_value):
            return 'Cisco IOS'
        elif re.search(r'WS-C\d{4}\w?-\d{2}\w{0,3}-\w?', recv_value):
            return 'Cisco IOS'
        elif re.search(r'N\dK-C\d{4}\w?', recv_value):
            return 'Cisco Nexus'
        elif re.search(r'AIR-CT\d{4}-K\d', recv_value):
            return 'Cisco WLC'
        elif re.search(r'UCSM:', recv_value):
            return 'Cisco UCSM'

    def get_hostname(self):
        if self.Product == 'Cisco IOS':
            self.shell.send('\nshow version\n')
            recv_value = shellrecv(self.shell)
            hostname = re.search(
                r'\w+-\w+-\w+(-\w+)?-\d+', recv_value).group()
            return hostname
        elif self.Product == 'Cisco Nexus' \
            or self.Product == 'Cisco ASA':
            self.shell.send('\nshow hostname\n')
            recv_value = shellrecv(self.shell)
            hostname = recv_value.split("\n")[-2].strip('\r').strip()
            return hostname
        elif self.Product == 'Cisco WLC':
            return 'WLC'
        elif self.Product == 'Cisco UCSM':
            self.shell.send('\nshow system detail\n')
            recv_value = shellrecv(self.shell)
            hostname = re.search(
                r'Name:\s(.*)\n', recv_value).groups()[0].strip('\r')
            return hostname

    def temPage_len(self, disable=True):
        length = '0' if disable else '35'
        if self.Product == 'Cisco ASA':
            self.shell.send(f'\t\nterminal pager {length}\n')
        elif self.Product == 'Cisco Nexus':
            self.shell.send(f'q\nterminal length {length}\n')
        elif self.Product == 'Cisco IOS':
            self.shell.send(f'\t\nterminal length {length}\n')
    
    def temWidth(self, disable=True):
        width = '500' if disable else '80'
        if self.Product == 'Cisco ASA':
            self.shell.send(f'\tconfig t\nterminal width {width}\n')
        elif self.Product == 'Cisco Nexus':
            self.shell.send(f'q\nerminal width {width}')
        elif self.Product == 'Cisco ':
            self.shell.send(f'\t\nterminal width {width}')

    def get_srcport(self):
        if self.Product == 'Cisco ASA':
            self.shell.send('\nshow ip addr\n')
            ip = self.ip.replace('.', r'\.')
            source_port = re.search(
                r'\s+(\w+\d?)\s+{0}.*'.format(ip), 
                shellrecv(self.shell)).groups()[0]
            return source_port
        elif self.Product == 'Cisco Nexus':
            self.shell.send(f'\nshow ip int br vrf all | xml\n')
            XMLStrRecv = shellrecv(self.shell)
            XML = self.nexusXML_format(XMLStrRecv)
            for interface in XML.findall('ROW_intf'):
                ip = interface.find('prefix').text
                if ip == self.ip:
                    source_port = interface.find('vrf-name-out').text
                    return source_port
        elif self.Product == 'Cisco WLC' or self.Product == 'Cisco IOS':
            shellrecv(self.shell)
        
    def nexusXML_format(self, XMLStrRecv):
        if re.search(r'<TABLE_vrf>', XMLStrRecv):
            # 专用于处理旧版本NXOS所生成show ip interface brief vrf all的XML格式字符串
            # 收集VRF的element，并在头尾加上一个<root></root>标签，用于生成一个完整的XML文档
            XMLStrip_vrf = ET.fromstring('<root>' + ''.join(re.findall(
                r'<TABLE_vrf>\s{0,}\n.*\n.*\n.*\n.*/TABLE_vrf>',
                XMLStrRecv)) + '</root>')
            # 收集接口的element，在头尾加上一个<TABLE_intf></TABLE_intf>标签，
            # 用于生成一个带主体根标签的XML
            XMLStrip_intf = ET.fromstring('<TABLE_intf>'+''.join(re.findall(
                r'<ROW_intf>\s{0,}\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n.*/ROW_intf>', 
                XMLStrRecv)) + '</TABLE_intf>')
            for num in range(len(XMLStrip_vrf)):
                # 遍历VRF的XML，去除VRF相关信息加入到接口的element对象中
                SubXML = ET.SubElement(XMLStrip_intf[num], 'vrf-name-out')
                SubXML.text = XMLStrip_vrf[num][0].find('vrf-name-out').text
            XML = XMLStrip_intf
            return XML
        else:
            # 处理新版本的NXOS所生成show ip interface brief vrf all的XML格式字符串
            XMLStrip = re.search(
                r'<TABLE_intf>(.|\n)*/TABLE_intf>',
                XMLStrRecv).group()
            XML = ET.fromstring(XMLStrip)
            return XML

    def SCPFunc(self, enable=True):
        command = '' if enable else 'no '
        self.SCPStatus = True if enable else False
        if self.Product == 'Cisco ASA':
            self.shell.send('\nconfig t\n')
            self.shell.send(f'\n{command}ssh scopy enable\n')
            self.shell.send('\nend\n')
        elif self.Product == 'Cisco IOS':
            self.shell.send('\nconfig t\n')
            self.shell.send(f'\n{command}ip scp server enable\n')
            self.shell.send('\nend\n')
        elif self.Product == 'Cisco Nexus':
            self.shell.send('\nconfig t\n')
            self.shell.send(f'\n{command}feature scp-server\n')
            self.shell.send('\nend\n')
            
    def SCPBackup(self, source_file, dest_file):
        self.SCPFunc(enable=True)
        scp_connection = SCPClient(
            self.sshconn.get_transport(), socket_timeout=20)
        sleep(0.5)
        try:
            scp_connection.get(f'system:{source_file}', dest_file)
        # except Exception as e:
        #     print("Exeption is captured!")
        #     raise Exception(e)
        finally:
            self.SCPFunc(enable=False)
            shellrecv(self.shell)

    def IOSftpbackup(self, *backupinfo, deplay=15):
        FTPaddress, filename, ftpuser, ftppass = backupinfo
        self.shell.send(
            'copy running-config ftp://{0}:{1}@{2}/{3}{4}'.format(
                ftpuser, ftppass, FTPaddress, filename, '\n'*5))
        recv_str = recv_expect(self.shell, r'bytes\scopied|%Error')
        if recv_str.find('bytes copied') > -1:
            return 'BackupSuccess'
        else: return 'BackupFailed'

    def ASAftpbackup(self, *backupinfo):
        FTPaddress, filename, ftpuser, ftppass = backupinfo
        self.shell.send(
            'copy /noconfirm running-config ftp://{0}:{1}@{2}/{3}\n'.format(
                ftpuser, ftppass, FTPaddress, filename))
        recv_str = recv_expect(self.shell, r'bytes\scopied|%Error')
        if recv_str.find('bytes copied') > -1:
            return 'BackupSuccess'
        else: return 'BackupFailed'

    def NXOSftpbackup(self, *backupinfo):
        FTPaddress, filename, ftpuser, ftppass, Source = backupinfo
        self.shell.send(
            'copy running-config ftp://{0}:{1}@{2}/{3} vrf {4}\n'.format(
                ftpuser, ftppass, FTPaddress, filename, Source))
        recv_str = recv_expect(
            self.shell, r'Successfully|Copy\scomplete|file\saborted|Password:')
        print(recv_str)
        if re.search(r'Password:', recv_str):
            self.shell.send(ftppass + '\n')
            recv_str = recv_expect(
                self.shell, r'Successfully|Copy\scomplete|file\saborted')
        if re.search(r'Successfully|Copy\scomplete', recv_str):
            return 'BackupSuccess'
        else: return 'BackupFailed'

    def UCSMftpbackup(self, *backupinfo):
        FTPaddress, filename, ftpuser, ftppass = backupinfo
        if self.PromptStaus != 'UCSM_SysSocpe':
            self.shell.send('scope system\n')
        self.shell.send('show backup | grep {}\n'.format(FTPaddress))
        if shellrecv(self.shell).find(FTPaddress) != -1:
            self.shell.send('delete backup {}\n'.format(FTPaddress))
            self.shell.send('commit-buffer\n')
        self.shell.send(
            'create backup ftp://{0}:{1}@{2}/{3}.xml {4} enabled\n'.format(
                ftpuser, ftppass, FTPaddress, filename, 'all-configuration'))
        recv_str = recv_expect(self.shell, r'Backup\sUpload|Backup\sSuccess|Password:')
        if recv_str.find('Password:') > -1:
            self.shell.send(ftppass + '\n')
            self.shell.send('commit-buffer\n')
            sleep(1.7); self.shell.send("show fsm status | grep 'Previous Status'\n")
            recv_str = recv_expect(self.shell, r'Backup\sUpload|Backup\sSuccess')
        if recv_str.find('Backup Success') > -1:
            return 'BackupSuccess'
        else: return 'BackupFailed'
    
    def WLCftpbackup(self, *backupinfo):
        FTPaddress, filename, ftpuser, ftppass = backupinfo
        self.shell.send('transfer upload mode ftp\n')
        self.shell.send('transfer upload username {}\n'.format(ftpuser))
        self.shell.send('transfer upload password {}\n'.format(ftppass))
        self.shell.send('transfer upload datatype config\n')
        self.shell.send('transfer upload filename {}\n'.format(filename))
        self.shell.send('transfer upload path .\n')
        self.shell.send('transfer upload serverip {}\n'.format(FTPaddress))
        self.shell.send('transfer upload start\ny\n')
        recv_str = recv_expect(self.shell, r'successfully|%\sError')
        if recv_str.find('successfully') > -1:
            return 'BackupSuccess'
        else: return 'BackupFailed'
    
    # def addionalPassReuqire(self, password):
    #     self.PromptStaus = self.PromptHandler()
    #     if self.PromptStaus == 'PW_require':
    #         self.shell.send(password + '\n')

    def FTPBackup(self, FTPaddress, filename, ftpuser, ftppass):
        backupinfo = (FTPaddress, filename, ftpuser, ftppass)
        if self.SCPStatus:
            self.SCPFunc(False)
            # sleep(1)
        src_port = self.get_srcport()
        if self.Product == 'Cisco IOS':
            status = self.IOSftpbackup(*backupinfo)
        elif self.Product == 'Cisco ASA':
            status = self.ASAftpbackup(*backupinfo)
        elif self.Product == 'Cisco WLC':
            status = self.WLCftpbackup(*backupinfo)
        elif self.Product == 'Cisco Nexus':
            status = self.NXOSftpbackup(*backupinfo, src_port)
        elif self.Product == 'Cisco UCSM':
            status = self.UCSMftpbackup(*backupinfo)
        return status

    def UCSAPIBackup(self, filename, backupdir=os.getcwd()):
        if len(backupdir + filename) > 65:
            raise Exception('备份文件名加路径总长度超出65个字符, 无法执行备份！')
        backup_ucs(self.UCSMhandle, backup_type='config-all', 
            file_dir=backupdir, file_name=filename)
        self.UCSMhandle.logout()
