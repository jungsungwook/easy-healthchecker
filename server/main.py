import datetime
from fastapi import FastAPI
from fastapi.responses import FileResponse
from datetime import date
from fastapi_scheduler import SchedulerAdmin
import json
from typing import Any
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.requests import Request
from fastapi_amis_admin.amis.components import Form
from fastapi_amis_admin.admin import admin
from fastapi_amis_admin.admin.settings import Settings
from fastapi_amis_admin.admin.site import AdminSite
from fastapi_amis_admin.crud.schema import BaseApiOut
from fastapi_amis_admin.models.fields import Field
from fastapi.responses import HTMLResponse
import pandas as pd
import os

with open("dbinfo.json", "r", encoding="utf8") as f:
    dbinfo = json.load(f)
serverinfo = {}
with open("serverinfo.json", "r", encoding="utf8") as f:
    serverinfo = json.load(f)

app = FastAPI()
site = AdminSite(settings=Settings(
    database_url_async='sqlite+aiosqlite:///amisadmin.db',
    language='en_US'
))

target_db_name_space = []
target_application_name_space={}
with open("target_db.json", "r", encoding="utf8") as f:
    target_db_name_space = json.load(f)

with open("target_application.json", "r", encoding="utf8") as f:
    target_application_name_space = json.load(f)
    
@site.register_admin
class UserLoginFormAdmin(admin.FormAdmin):
    page_schema = 'UserLoginForm'
    # set form information, optional
    form = Form(title='This is a test login form', submitText='login')

    # create form schema
    class schema(BaseModel):
        username: str = Field(..., title='username',
                              min_length=3, max_length=30)
        password: str = Field(..., title='password')

    # handle form submission data
    async def handle(self, request: Request, data: BaseModel, **kwargs) -> BaseApiOut[Any]:
        if data.username == 'admin' and data.password == '!@#admin123':
            return BaseApiOut(msg='Login successfully!', data={'token': 'secretToken'})
        return BaseApiOut(status=-1, msg='Incorrect username or password!')


scheduler = SchedulerAdmin.bind(site)
site.mount_app(app)
scheduler.start()


def connect_db(db_info_key):
    try:
        db_info = dbinfo[db_info_key]
        if db_info["DATABASE_TYPE"] == "oracle":
            import cx_Oracle
            try:
                dsn = cx_Oracle.makedsn(
                    db_info["DATABASE_HOST"], int(db_info["DATABASE_PORT"]), db_info["DATABASE_SID"])
                conn = cx_Oracle.connect(
                    db_info["DATABASE_USER"], db_info["DATABASE_PASSWORD"], dsn, mode=cx_Oracle.SYSDBA)
                return conn
            except Exception as e:
                # SID 대신 SERVICE_NAME을 사용하는 경우
                dsn = cx_Oracle.makedsn(
                    db_info["DATABASE_HOST"], int(db_info["DATABASE_PORT"]), service_name=db_info["DATABASE_SID"])
                conn = cx_Oracle.connect(
                    db_info["DATABASE_USER"], db_info["DATABASE_PASSWORD"], dsn, mode=cx_Oracle.SYSDBA)
                return conn
        elif db_info["DATABASE_TYPE"] == "mssql":
            # import pymssql
            # conn = pymssql.connect(server=db_info["DATABASE_HOST"], user=db_info["DATABASE_USER"],
            #                     password=db_info["DATABASE_PASSWORD"], database=db_info["DATABASE_SID"])
            return None
        else:
            return None
    except Exception as e:
        print("DB: ", db_info_key, "=>connect_db error : ", e)
        return None


@app.get("/main")
def mainpage():
    html=""
    return_data = []
    file = pd.read_csv("dbinfo.csv")
    for i, j in target_db_name_space:
        temp = file[(file["DB 명"] == i) & (file["테이블스페이스 명"] == j)]
        if len(temp) == 1:
            temp = temp.iloc[0]
            temp["여유공간 퍼센트"] = round(
                temp["여유공간(MB)"] / temp["총공간(MB)"] * 100, 2)
            return_data.append(temp.to_dict())
        else:
            return_data.append({"DB 명": i, "테이블스페이스 명": j,
                                "파일경로": "None", "사용공간(MB)": 0, "여유공간(MB)": 0, "총공간(MB)": 0, "여유공간 퍼센트": 0})

    html += "<h1>Applicaton Status</h1>"
    # tcp 리스트를 통해 포트를 확인하고, 헬스체크
    for key in serverinfo.keys():
        # 만약 target_application_name_space에 key가 없다면 continue
        if key not in target_application_name_space:
            continue
        server = serverinfo[key]
        info = os.listdir("logs/"+server["user"])
        log_list = os.listdir("logs/"+server["user"])
        log_list.sort()
        info = json.load(
            open("logs/"+server["user"]+"/"+log_list[-1], "r", encoding="utf8"))
        html += "<table border=1>"
        html += "<tr>"
        html += "<th>서버</th>"
        html += "<th>IP</th>"
        html += "<th>업타임</th>"
        html += "</tr><tr>"
        html += "<td>"+str(server["user"])+"</td>"
        html += "<td>"+str(server["ip"])+"</td>"
        html += "<td>"+str(info["uptime"])+"</td></tr>"
        html += "<tr><th>PORT</th>"
        html += "<th>pid</th>"
        html += "<th>service name</th>"
        html += "<th>tcp name</th>"
        html += "<th>status</th></tr>"
        alreadyPort = []
        tcplist = info["tcp4"]
        for tcp in tcplist:
            targetList = target_application_name_space[server["user"]]
            for target in targetList:
                if tcp["port"] == target["port"]:
                    if tcp["port"] in alreadyPort:
                        continue
                    html += "<tr>"
                    html += "<td>"+str(tcp["port"])+"</td>"
                    html += "<td>"+str(tcp["pid"])+"</td>"
                    html += "<td>"+str(target["service_name"])+"</td>"
                    html += "<td>"+str(tcp["name"])+"</td>"
                    html += "<td style='background:green;'></td>" if str(tcp["status"]) == "running" else "<td style='background:red;'></td>"
                    alreadyPort.append(tcp["port"])
                    break
            html += "</tr>"
        html += "</table>"
        html += "<br><br>"
    # return_data를 html에서 표로 보여줌
    html += "<h1>DB Status</h1>"
    # logs/db 경로 안의 모든 폴더를 가져오고 그 안의 log_*.json 파일을 가져온다.
    db_list = os.listdir("logs/db")
    for db in db_list:
        db_logs = os.listdir("logs/db/"+db)
        db_logs.sort()
        db_info = json.load(
            open("logs/db/"+db+"/"+db_logs[-1], "r", encoding="utf8"))
        html += "<table border=1>"
        html += "<tr>"
        html += "<th>DB 명</th>"
        html += "<th>인스턴스 명</th>"
        html += "<th>Status</th>"
        html += "<th>업타임</th>"
        html += "</tr><tr>"
        html += "<td>"+str(db)+"</td>"
        html += "<td>"+str(db_info["instance_name"])+"</td>"
        if(db_info["status"] == "OPEN" and db_info["database_status"] == "ACTIVE"):
            html += "<td style='background:green;'></td>"
        else:
            html += "<td style='background:red;'></td>"
        uptime = str(db_logs[-1].split(".")[0].split("_")[1])
        uptime = uptime[0:4]+"-"+uptime[4:6]+"-"+uptime[6:8]+" "+uptime[8:10] + \
            ":"+uptime[10:12]+":"+uptime[12:14]
        html += "<td>"+uptime+"</td></tr>"
        html += "</table>"
        html += "<br>"

    html += "<a href='/download/db'>DB 정보 다운로드</a><br><br>"
    html += "<table border=1>"
    html += "<tr>"
    for i in return_data[0].keys():
        html += "<th>"+i+"</th>"
    html += "</tr>"
    for i in return_data:
        html += "<tr>"
        for j in i.values():
            html += "<td>"+str(j)+"</td>"
        html += "</tr>"
    html += "</table>"
    html += "<br><br>"
    html += "<h1>Server Status</h1>"
    html += "<a href='/download/server'>Server 정보 다운로드</a><br><br>"
    for key in serverinfo.keys():
        server = serverinfo[key]
        info = os.listdir("logs/"+server["user"])
        log_list = os.listdir("logs/"+server["user"])
        log_list.sort()
        info = json.load(
            open("logs/"+server["user"]+"/"+log_list[-1], "r", encoding="utf8"))
        # 수정일이 하루가 지나면 빨간색 동그라미를 표시
        # if (datetime.datetime.now() - datetime.datetime.strptime(info["uptime"], "%Y/%m/%d %H:%M:%S")).days > 0:
        #     html += "업타입 : <span style='color:red'>●</span>&nbsp;&nbsp;&nbsp;"
        # else:
        #     html += "업타입 : <span style='color:green'>●</span>&nbsp;&nbsp;&nbsp;"
        # 수정일이 1시간이 지나면 빨간색 동그라미를 표시
        if (datetime.datetime.now() - datetime.datetime.strptime(info["uptime"], "%Y/%m/%d %H:%M:%S")).seconds > 3600:
            html += "업타입 : <span style='color:red'>●</span>&nbsp;&nbsp;&nbsp;"
        else:
            html += "업타입 : <span style='color:green'>●</span>&nbsp;&nbsp;&nbsp;"

        # 디스크 사용률이 90% 이상이면 빨간색 동그라미를 표시
        for hdd in info["hdd"]:
            if hdd["percent"] > 90:
                html += str(hdd["Disc"]) + \
                    "디스크 사용률 : <span style='color:red'>●</span>&nbsp;&nbsp;&nbsp;"
            else:
                html += str(hdd["Disc"]) + \
                    "디스크 사용률 : <span style='color:green'>●</span>&nbsp;&nbsp;&nbsp;"

        # 이름 | IP | CPU 사용률 | 메모리 사용률
        html += "<table border=1>"
        html += "<tr>"
        html += "<th>이름</th>"
        html += "<th>IP</th>"
        html += "<th>CPU 사용률</th>"
        html += "<th>메모리 사용률</th>"
        html += "<th>수정일</th>"
        html += "</tr>"
        html += "<tr>"
        html += "<td>"+server["user"]+"</td>"
        html += "<td>"+server["ip"]+"</td>"
        html += "<td>"+str(info["cpu"])+"</td>"
        html += "<td>"+str(info["ram"])+"</td>"
        html += "<td>"+str(info["uptime"])+"</td></tr>"
        # 디스크 종류 | 디스크 사용률 | 디스크 여유공간 | 디스크 총공간 | 디스크 여유공간 퍼센트
        html += "<tr><th>디스크 종류</th>"
        html += "<th>디스크 사용률(%)</th>"
        html += "<th>디스크 사용량(GB)</th>"
        html += "<th>디스크 여유공간(GB)</th>"
        html += "<th>디스크 총공간(GB)</th></tr>"
        for hdd in info["hdd"]:
            html += "<tr>"
            html += "<td>"+str(hdd["Disc"])+"</td>"
            html += "<td>"+str(hdd["percent"])+"</td>"
            html += "<td>"+str(hdd["used"])+"</td>"
            html += "<td>"+str(hdd["total"] - hdd["used"])+"</td>"
            html += "<td>"+str(hdd["total"])+"</td>"
            html += "</tr>"
        html += "</table>"
        html += "<br><br>"
    return HTMLResponse(content=html, status_code=200)


@app.get("/db")
def show_db():
    target_db_name_space = []
    with open("target_db.json", "r", encoding="utf8") as f:
        target_db_name_space = json.load(f)
    # DB 정보(file)
    # {
    #     "DB 명": "DEVDBUTF8",
    #     "테이블스페이스 명": "MSUITE4_DAT",
    #     "파일경로": "/u01/app/oracle/oradata/DEVDBUTF8/MSUITE4_DAT.dbf",
    #     "사용공간(MB)": 0,
    #     "여유공간(MB)": 0,
    #     "총공간(MB)": 0,
    #     "여유공간 퍼센트": 0,
    # }
    return_data = []
    file = pd.read_csv("dbinfo.csv")
    for i, j in target_db_name_space:
        temp = file[(file["DB 명"] == i) & (file["테이블스페이스 명"] == j)]
        if len(temp) == 1:
            temp = temp.iloc[0]
            temp["여유공간 퍼센트"] = round(
                temp["여유공간(MB)"] / temp["총공간(MB)"] * 100, 2)
            return_data.append(temp.to_dict())
        else:
            return_data.append({"DB 명": i, "테이블스페이스 명": j,
                                "파일경로": "None", "사용공간(MB)": 0, "여유공간(MB)": 0, "총공간(MB)": 0, "여유공간 퍼센트": 0})

    # return_data를 html에서 표로 보여줌
    html = "<table border=1>"
    html += "<tr>"
    for i in return_data[0].keys():
        html += "<th>"+i+"</th>"
    html += "</tr>"
    for i in return_data:
        html += "<tr>"
        for j in i.values():
            html += "<td>"+str(j)+"</td>"
        html += "</tr>"
    html += "</table>"
    return HTMLResponse(content=html, status_code=200)


class ServerInfo(BaseModel):
    server_name: str
    server_ip: str
    cpu: str
    ram: str
    hdd: list
    tcp4: list
    uptime: str


@app.post("/server")
def set_server(server_info: ServerInfo):
    try:
        get_info = json.loads(server_info.json())
        if not os.path.isdir("logs/"+get_info["server_name"]):
            os.mkdir("logs/"+get_info["server_name"])
        with open("logs/"+get_info["server_name"]+"/log_"+str(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))+".json", "x", encoding="utf8") as f:
            json.dump(get_info, f, ensure_ascii=False)
        print("# Saved!")
        return {"result": "success"}
    except Exception as e:
        print(e)
        return {"result": "fail", "error": str(e)}


@app.get("/server")
def get_server():
    try:
        # serverinfo.json에서 서버 목록들을 가져온다.
        server_list = []
        for key in serverinfo.keys():
            server_list.append(
                [serverinfo[key]["user"], serverinfo[key]["ip"]])
        # 가져온 서버 목록들을 나열하고 클릭 시 해당 서버의 정보를 가져오는 url로 이동시키는 html 코드를 생성
        html = "<html><body>"
        for server in server_list:
            html += "<a href='/server/" + \
                server[0]+"'>"+server[0]+"("+server[1]+")"+"</a><br><br/>"
        html += "</body></html>"
        return HTMLResponse(html)
    except Exception as e:
        print(e)
        return {"result": "fail", "error": str(e)}


@app.get("/server/{server_name}")
def show_server(server_name: str):
    try:
        # serverinfo.json에서 해당 서버의 정보를 가져온다.
        server = serverinfo[server_name]
        # logs/서버명 폴더에서 가장 최근에 저장된 로그 파일을 가져온다.
        # 파일명은 log_yyyymmddhhmmss.json 형식으로 저장되어 있으므로 파일명을 기준으로 정렬하여 가장 마지막 파일을 가져온다.
        log_list = os.listdir("logs/"+server_name)
        log_list.sort()
        server_info = json.load(
            open("logs/"+server_name+"/"+log_list[-1], "r", encoding="utf8"))
        # 가져온 정보를 html 코드로 생성
        html = "<html><body>"
        html += "<h1>"+server_name+"</h1>"
        html += "<h3>UpdatedAt: "+server_info["uptime"]+"</h3>"
        html += "<h3>IP: "+server["ip"]+"</h3>"
        html += "<h3>NAME: "+server["user"]+"</h3>"
        html += "<h3>CPU: "+server_info["cpu"]+"</h3>"
        html += "<h3>RAM: "+server_info["ram"]+"</h3>"
        # HDD = [{'Disc': 'C:\\', 'percent': 48.8, 'used': 232, 'total': 476}, {'Disc': 'D:\\', 'percent': 35.8, 'used': 333, 'total': 931}]
        # 표로 만들기
        html += "<h3>HDD : </h3>"
        html += "<table border='1'><tr><th>Disc</th><th>percent</th><th>used(GB)</th><th>total(GB)</th></tr>"
        for hdd in server_info["hdd"]:
            html += "<tr><td>"+hdd["Disc"]+"</td><td>"+str(hdd["percent"])+"</td><td>"+str(
                hdd["used"])+"</td><td>"+str(hdd["total"])+"</td></tr>"
        # tcp4 = [{'pid': 7676, 'port': 5500, 'status': 'running'}, {'pid': 1398448, 'port': 52952, 'status': 'running'}]
        # 표로 만들기
        html += "</table>"
        html += "<h3>TCP4 : </h3>"
        html += "<table border='1'><tr><th>pid</th><th>name</th><th>port</th><th>status</th></tr>"
        for tcp4 in server_info["tcp4"]:
            html += "<tr><td>"+str(tcp4["pid"])+"</td><td>"+str(tcp4["name"])+"</td><td>"+str(
                tcp4["port"])+"</td><td>"+str(tcp4["status"])+"</td></tr>"
        html += "</table>"
        html += "</body></html>"
        return HTMLResponse(html)
    except Exception as e:
        print(e)
        return {"result": "fail", "error": str(e)}


@app.get("/dbinfo")
def get_dbinfo():
    try:
        result_info = {}
        for key in dbinfo.keys():
            conn = connect_db(key)
            if (conn == None):
                continue
            cursor = conn.cursor()
            cursor.execute("SELECT A.TABLESPACE_NAME, A.FILE_NAME, (A.BYTES - B.FREE) / (1024 * 1024), B.FREE / (1024 * 1024), A.BYTES / (1024 * 1024), TO_CHAR((B.FREE / A.BYTES * 100), '999.99') || '%' FROM (SELECT FILE_ID, TABLESPACE_NAME, FILE_NAME, SUBSTR(FILE_NAME, 1, 200) FILE_NM, SUM(BYTES) BYTES FROM DBA_DATA_FILES GROUP BY FILE_ID, TABLESPACE_NAME, FILE_NAME, SUBSTR(FILE_NAME, 1, 200)) A, (SELECT TABLESPACE_NAME, FILE_ID, SUM(NVL(BYTES, 0)) FREE FROM DBA_FREE_SPACE GROUP BY TABLESPACE_NAME, FILE_ID) B WHERE A.TABLESPACE_NAME = B.TABLESPACE_NAME AND A.FILE_ID = B.FILE_ID")
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            result_info[key] = result
    except Exception as e:
        result_info["error"] = str(e)
        print(e)

    # result_info는 테이블스페이스명, 파일경로, 사용공간(MB), 여유 공간(MB), 총크기(MB), 여유공간 의 정보를 가지고 있음
    # 해당 정보를 보기 좋게 가공해서 리턴
    result = []
    for key in result_info.keys():
        for row in result_info[key]:
            result.append({
                "DB 명": key,
                "테이블스페이스 명": row[0],
                "파일경로": row[1],
                "사용공간(MB)": row[2],
                "여유공간(MB)": row[3],
                "총공간(MB)": row[4],
                "여유공간 퍼센트": row[5]
            })
    # 해당 정보를 csv 파일로 저장
    with open("dbinfo.csv", "w", encoding="utf8") as f:
        f.write("DB 명,테이블스페이스 명,파일경로,사용공간(MB),여유공간(MB),총공간(MB),여유공간 퍼센트\n")
        for row in result:
            f.write(row["DB 명"]+","+row["테이블스페이스 명"]+","+row["파일경로"]+","+str(row["사용공간(MB)"]) +
                    ","+str(row["여유공간(MB)"])+","+str(row["총공간(MB)"])+","+row["여유공간 퍼센트"]+"\n")
    return result


@app.get('/download/{type}')
def download(type: str):
    if type == "server":
        servers=[]
        for key in serverinfo.keys():
            server = serverinfo[key]
            info = os.listdir("logs/"+server["user"])
            log_list = os.listdir("logs/"+server["user"])
            log_list.sort()
            info = json.load(
                open("logs/"+server["user"]+"/"+log_list[-1], "r", encoding="utf8"))
            server_name = server["user"]
            server_ip = server["ip"]
            cpu = info["cpu"]
            ram = info["ram"]
            uptime = info["uptime"]
            hddlist = []
            for hdd in info["hdd"]:
                disc = str(hdd["Disc"])
                percent = str(hdd["percent"])
                used = str(hdd["used"])
                free = str(hdd["total"] - hdd["used"])
                total = str(hdd["total"])
                hddlist.append({"Disc": disc, "percent": percent,
                                "used": used, "free": free, "total": total})
            server_result = {"server_name": str(server_name), "server_ip": str(server_ip), "cpu": str(
                cpu), "ram": str(ram), "uptime": str(uptime), "hddlist": hddlist}
            servers.append(server_result)
        # servers를 csv 파일로 저장

        with open("./upload/servers.csv", "w", encoding="utf8") as f:
            f.write("server_name,server_ip,cpu,ram,uptime,Disc,used(%),used(GB),free(GB),total(GB)\n")
            for row in servers:
                # f.write(row["server_name"]+","+row["server_ip"]+","+row["cpu"]+","+row["ram"]+","+row["uptime"]+","+str(row["hddlist"])+"\n")
                content = row["server_name"]+","+row["server_ip"]+","+row["cpu"]+","+row["ram"]+","+row["uptime"]+","
                f.write(content)
                chk = False
                for hdd in row["hddlist"]:
                    if(chk):
                        f.write(",,,,,")
                    discinfo = hdd["Disc"]+","+hdd["percent"]+","+hdd["used"]+","+hdd["free"]+","+hdd["total"]+","
                    f.write(discinfo+"\n")
                    chk = True
        return FileResponse("./upload/servers.csv")
    elif type == "db":
        return FileResponse("./dbinfo.csv")
# 1시간 간격으로 실행
def check_oracle_status(key, value):
    import cx_Oracle
    try:
        connection = connect_db(key)
        if(connection == None):
            if not os.path.isdir("logs/db/"+key):
                os.mkdir("logs/db/"+key)
            with open("logs/db/"+key+"/log_"+str(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))+".json", "x", encoding="utf8") as f:
                json.dump({"instance_name": value["DATABASE_SID"], "status": "None", "database_status": "None"}, f, ensure_ascii=False)
            return
        # 상태 정보 가져오기
        cursor = connection.cursor()
        cursor.execute('SELECT instance_name, status, database_status FROM v$instance')
        result = cursor.fetchone()

        # 결과 출력
        if result:
            instance_name, status, database_status = result
            if not os.path.isdir("logs/db/"+key):
                os.mkdir("logs/db/"+key)
            with open("logs/db/"+key+"/log_"+str(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))+".json", "x", encoding="utf8") as f:
                json.dump({"instance_name": instance_name, "status": status, "database_status": database_status}, f, ensure_ascii=False)
        else:
            with open("logs/db/"+key+"/log_"+str(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))+".json", "x", encoding="utf8") as f:
                json.dump({"instance_name": value["DATABASE_SID"], "status": "None", "database_status": "None"}, f, ensure_ascii=False)
            print("No data available.")
        
        # 연결 종료
        cursor.close()
        connection.close()

    except cx_Oracle.Error as error:
        with open("logs/db/"+key+"/log_"+str(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))+".json", "x", encoding="utf8") as f:
            json.dump({"instance_name": value["DATABASE_SID"], "status": "None", "database_status": "None"}, f, ensure_ascii=False)
        print("Error connecting to Oracle Database:", error)
        return

@scheduler.scheduled_job('interval', seconds=3600)
def interval_task():
    logs_data = []
    for key, value in dbinfo.items():
        if(key == "DEVDB19C"):
            continue
        if(value["DATABASE_TYPE"] == "oracle"):
            check_oracle_status(key, value)
    # with open("logs/log_"+str(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))+".json", "w", encoding="utf8") as f:
    #     json.dump(logs_data, f)
    # print("# [Auto Save] log_"+str(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))+".json")
