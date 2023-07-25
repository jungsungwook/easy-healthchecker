import psutil
import time
import os
import requests
import json
import socket
from dotenv import load_dotenv
from datetime import datetime
import getpass
import schedule


print("# 업로드 클라이언트 실행중.")
path='./log/'
tm_year, tm_mon, tm_mday, tm_hour, tm_min, _, _, _, _ = time.localtime()
file_name = f'{tm_year}-{tm_mon}-{tm_mday} {tm_hour}h{tm_min}m.log'
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("google.com", 443))
hostip = sock.getsockname()[0]
hostname = getpass.getuser()
print("# 호스트 IP : ", hostip)
print("# 호스트 이름 : ", hostname)

def sending():
    try:
        print("# 전송 중...")
        load_dotenv()

        upload = os.getenv('UPLOAD_IP')
        upload_ip = f'http://{upload}/server'

        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        hdds = psutil.disk_partitions(all=True)
        hdd = []
        tcp4 = psutil.net_connections(kind='tcp4')
        tcp4_req = []
        hdd_req = []


        for i in hdds:
            device, mountpoint, fstype, opts, *_ = i
            try:
                total, used, free, percent = psutil.disk_usage(mountpoint)
                hdd.append((device, percent, used >> 30, total >> 30))
            except:
                continue

        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except OSError:
            raise

        with open(path + file_name, 'w') as f:
            f.writelines(f'Cpu: {cpu}%\n')
            f.writelines(f'Ram: {ram.percent}% {ram.used >> 20}/{ram.total >> 20} MB\n\n')

            f.writelines(f"HDD:\n")
            f.writelines(f"{'Disc' : <10}{'percent' : <10}{'use/total' : <10}\n")
            for i in hdd:
                if i[0] == 'Z:\\' or i[0] == 'Y:\\' or i[0] == 'X:\\':
                    continue
                f.writelines(f'{i[0] : <10} {i[1]}% {i[2]:>5}/{i[3]} GB\n')
                hdd_req.append({"Disc": i[0], "percent":i[1], "used":i[2], "total":i[3]})
            
            f.writelines(f"\nProcess(tcp4):\n")
            f.writelines(f"{'pid' : <10}{'name' : <40}{'port' : <10}{'status' : >5}\n")
            for i in tcp4:
                pid = i.pid
                port = i.laddr.port
                name = psutil.Process(pid).name()
                status = psutil.Process(pid).status()
                if name in ['System', 'svchost.exe', 'System Idle Process', 'firefox.exe', 'chrome.exe']:
                    continue
                f.writelines(f"{pid : <10}{name : <40}{port : <10}{status : >5}\n")
                tcp4_req.append({'pid': pid,'name': name, 'port':port, 'status':status })

        data = {}
        data["server_ip"] = hostip
        data["server_name"] = hostname
        data["cpu"] = f'{cpu}%'
        data["ram"] = f'{ram.percent}% {ram.used >> 20}/{ram.total >> 20} MB'
        data["tcp4"] = tcp4_req
        data["hdd"] = hdd_req
        data["uptime"] = datetime.today().strftime("%Y/%m/%d %H:%M:%S")
        res = requests.post(upload_ip, json=data)
        print(res)
        print("# 전송 완료 : ", datetime.today().strftime("%Y/%m/%d %H:%M:%S"))
        print("# ==============================================" )
    except Exception as e:
        print("# 전송 실패 : ", datetime.today().strftime("%Y/%m/%d %H:%M:%S"))
        print("# 실패 사유 : ", e)
        print("# ==============================================" )

load_dotenv()
upload_time = int(os.getenv('UPLOAD_TIME_MINUTE'))
schedule.every(upload_time).minutes.do(sending)
if __name__=='__main__':
    while True:
        schedule.run_pending()
        time.sleep(1)
