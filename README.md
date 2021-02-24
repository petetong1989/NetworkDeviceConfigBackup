# UCN_Backup

## Introduction

UnityConfigBackup is used for collect configuration from various network device. You can use it intead ansible. Especially if you collecting within various and small number devices, it will be your nightmare.

1. Involve interaction view with function `main_interact`.

2. Function `unity_process` gonna help you to finish the backup procedure.

3. Function `back_fuc` is main function that actually taking the backup job. 

> Note, `Telnet` isn't supported, only `SSH`.

***Supports***

- [x] Cisco NXOS
- [x] Cisco WLC
- [x] Cisco IOS
- [x] Cisco UCS Fabric Interconnect
- [x] F5 Load Balancer
- [x] Broadcom DS300

## Usage

- Ensure got `Python3` installed.

- Simply excute `python unity_back.py`  involve interaction. Give the information as it request.


