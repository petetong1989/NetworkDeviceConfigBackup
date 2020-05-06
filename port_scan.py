#!/usr/bin/env python3
# -*- coding:utf8 -*-
# @Author: Pete.Zhangbin
# @Email: pete19890813@gmail.com

from datetime import datetime
from multiprocessing.pool import ThreadPool
import ipaddress
import socket

def scan_func(ip, port):
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    scan_pkt = (str(ip), int(port))
    scan_result = a_socket.connect_ex(scan_pkt)
    return scan_result

def multiple_scan(network, port=22):
    net = ipaddress.ip_network(network)
    pool = ThreadPool(processes=150)
    result_obj_dict = {}
    for ip in net:
        result_obj = pool.apply_async(scan_func, args=(ip, port))
        result_obj_dict[str(ip)] = result_obj
    pool.close()
    pool.join()
    active_ip = []
    for ip, obj in result_obj_dict.items():
        if obj.get() == 0:
            active_ip.append(ip)
    return active_ip


if __name__ == "__main__":
    # result = scan_func('10.21.106.2', '22')
    # if result == 0:
    #     print('端口 ‘22’ 通讯正常！')
    # else:
    #     print('端口 ‘22’ 通讯有问题！')
    result = multiple_scan("10.21.107.0/24")
    print(result)
