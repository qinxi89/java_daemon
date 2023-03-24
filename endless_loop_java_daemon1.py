#!/usr/bin/env python
# -*- coding: utf-8 -*-
# time: 2023/3/23 10:41
# file: supervisor-java01.py
# author: qinxi
# email: 1023495336@qq.com

import logging
import os
import sys
import time
import psutil
import subprocess
import requests
import json
import hmac
import hashlib
import base64
import datetime

# 定义项目的家目录，jar包名称，环境变量
JAR_HOME = "/data/admin-api/"
JAR_NAME = "admin-api-1.0-SNAPSHOT.jar"
ACTIVE = "dev"

SECRET = "TfzraBX6IAnyJdZ56RMsl"
FEISHU_HOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/57c3177e-7f28-4be2-8245-d18bde10420e"
LOG_FILE = JAR_NAME.strip('\n').split('-')[0] + '_supervisor.log'
NOW_TIME = datetime.datetime.now()

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# 定义Java进程启动命令
JAVA_COMMAND = ["nohup", "java", "-jar", f"-Dspring.profiles.active={ACTIVE}", JAR_HOME + JAR_NAME]
JAVA_COMMAND_STR = " ".join(JAVA_COMMAND) + " > /dev/null 2>&1 &"

def generate_signature(timestamp, secret):
    """
    生成飞书机器人消息签名
    """
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode("utf-8")
    return sign


def send_feishu_message(message):
    """
    发送text类型飞书消息通知
    """
    timestamp = int(time.time())
    title = "线上JAVA项目守护进程"
    sign = generate_signature(timestamp, SECRET)
    headers = {"Content-Type": "application/json;charset=utf-8"}
    message_body = {
        "timestamp": timestamp,
        "sign": sign,
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": [[{"tag": "text", "text": message}]]
                }
            }
        }
    }
    try:
        res = requests.post(FEISHU_HOOK_URL, data=json.dumps(message_body), headers=headers)
        res = res.json()
    except Exception as e:
        print.error("请求异常: %s" % e)
        logging.info("请求异常: %s" % e)
        res = None

    return res


def is_java_running(java_program_name):
    '''
    :param java_program_name: 注意java_program_name 传入的参数必须为JAR_HOME + JAR_NAME 全路径
    :return:
    '''

    # 使用psutil获取正在运行的进程列表
    process_list = psutil.process_iter()

    # 遍历进程列表，查找Java进程
    for process in process_list:
        try:
            # 获取进程信息
            process_info = process.as_dict(attrs=['pid', 'name', 'cmdline'])

            # 如果进程名称为"java"，且命令行参数包含Java程序名称，则表示Java程序正在运行
            if process_info["name"] == "java" and java_program_name in process_info["cmdline"]:
                print("Java程序" + java_program_name + "正在运行，进程ID为" + str(process_info["pid"]))
                logging.info("Java程序" + java_program_name + "正在运行，进程ID为" + str(process_info["pid"]))
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    else:
        print("Java程序" + java_program_name + "没有在运行中")
        logging.info("Java程序" + java_program_name + "没有在运行中")
        return False


if __name__ == '__main__':
    # 检查Java进程是否在运行
    if is_java_running(JAR_NAME):
        print(NOW_TIME + 'hz-prd02服务器上 '+JAR_NAME + ' 正在运行.....')

    else:
        if os.path.exists(JAR_HOME + JAR_NAME):
            send_feishu_message(JAR_NAME + ' 正在重启......')
            logging.info(JAR_NAME + ' 正在重启......')
            # Java进程未运行，启动它
            subprocess.Popen(JAVA_COMMAND_STR, shell=True)
            time.sleep(10)

        else:
            logging.info(JAR_HOME + JAR_NAME + '不存在')
            sys.exit(JAR_HOME + JAR_NAME + '不存在')
