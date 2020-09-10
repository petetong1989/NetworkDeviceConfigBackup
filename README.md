# UnityConfigBackup Introduction

UnityConfigBackup is used for collection configuration from various network device. You can use it intead of ansible, I mean if your environment has network device from multiple vender, and each of the number is not too many. 

Trust me that if you collect the configuration within that kind of environment. that will be your nightmare.

UnityConfigBackup 是用来自动收集多种网络设备的配置, 如果你的网络场景中有多种厂商设备，但是数量都不多，这时候你用Ansible就非常不方便了

目前该脚本的原理为通过SSH登陆设备设定相关参数，第一次使用SCP，SFTP或API尝试备份，失败后第二次尝试FTP备份(并非所有设备都会尝试FTP备份，视设备支持情况而定)

1. 通过函数`main_interact`展现交互式界面；

> Get in interaction view with function `main_interact`.

2. 通过调用函数`unity_process`函数完成备份过程;

> function `unity_process` gonna help you to finish the backup procedure.

3. 通过调用函数`backup_fuc`来执行备份操作;

> function `back_fuc` is the main function that actually taking the backup job. 

👉 注意：不支持`Telnet`连接，仅支持`SSH`连接

> 👉 Notice: Not supports `Telnet` connection, only `SSH` supports.

Currently supports (当前支持)

- [x] Cisco NXOS
- [x] Cisco WLC
- [x] Cisco IOS
- [x] Cisco UCS FI
- [x] F5 LoadBalance
- [x] Broadcom DS300 FC Switch

# Useage

请确保你的环境中安装有`Python3`

> Make sure that you got `Python3` installed.

直接执行`python unity_back.py`进入交互界面。提供界面中需要你输入的信息即可

> Simply excute `python unity_back.py` for get in to the view of interaction. provide the information with the program request.


