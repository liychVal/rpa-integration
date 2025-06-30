import sys
sys.path.append('')

import socket
import threading
import time
import json
from RpaTools import *

class CenterServer:
    MAX_NETWORK_CONNECTIONS = 5

    def __init__(self, host="0.0.0.0", port=55338):
        self.host = host
        self.port = port
        self.clients = {}
        self.work_items = {}
        self.superman_items = config.get_superman_items()  # 从配置中获取
        self.web_thread = None
        self.web_lock = threading.Lock()

    # 启动服务器
    def start_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(self.MAX_NETWORK_CONNECTIONS)
        print(f"服务器监听中：{self.host}:{self.port}")

        self.web_thread = threading.Thread(target=self.web_control)
        self.web_thread.start()

        while True:
            client_socket, addr = server_socket.accept()
            print(f"接收到来自 {addr} 的连接")

            username = client_socket.recv(1024).decode().strip()
            self.clients[username] = client_socket
            print(f"客户端 {username} 已连接")

            threading.Thread(target=self.communicate_client, args=(username,)).start()

    # Web 控制线程
    def web_control(self):
        print("Web 控制线程已启动")

        if not init_bpm_client():
            print("BPM 平台认证失败")
            return

        need_sleep = False
        while True:
            if need_sleep:
                time.sleep(30)
            else:
                time.sleep(2)

            need_sleep = True
            if validate_work_item(self.work_items, self.superman_items):
                print(f"检测到待处理任务项 -- {self.work_items}")

                # UI 控制锁
                with self.web_lock:
                    for key in self.work_items:
                        work_item_tuple = self.work_items[key]
                        if work_item_tuple[1] == 0:
                            task_id = work_item_tuple[0]
                            print(f"开始处理任务项 -- {key}")
                            time.sleep(1)

                            rpa_data = get_work_item_data_superman(key)
                            rpa_data["taskId"] = task_id
                            print(f"获取RPA数据 -- {key} -- 数据内容: {rpa_data}")

                            # 尝试发送任务
                            if self.send_work_item(rpa_data):
                                # 只有发送成功才标记为已处理
                                self.work_items[key] = (task_id, 1)

                need_sleep = False
            else:
                print("当前无任务项")

    def send_work_item(self, data):
        username = data["userName"]
        if username in self.clients:
            json_data = json.dumps(data)
            try:
                self.clients[username].sendall(json_data.encode("utf-8"))
                print(f"已发送任务 {data['taskName']} 给用户 {username}")
                return True
            except Exception as e:
                print(f"发送数据失败：{e}")
                return False
        else:
            print("用户对应的RPA客户端不存在！")
            return False

    # 网络通信线程
    def communicate_client(self, username):
        print(f"与客户端 {username} 的通信线程已启动")
        client_socket = self.clients[username]
        while True:
            try:
                json_data = client_socket.recv(1024).decode("utf-8")
                data = json.loads(json_data)
                if data["state"] == "completed":
                    print(f"收到来自 {username} 的任务完成通知")
                    self.click_complete_button(data)
                else:
                    print(f"收到来自 {username} 的未知消息: {data}")
            except json.JSONDecodeError:
                continue
            except ConnectionResetError:
                print(f"客户端 {username} 已断开连接")
                del self.clients[username]
                break
            except Exception as e:
                print(f"与客户端 {username} 通信时发生错误：{e}")
                break

    def click_complete_button(self, data):
        key = f"RPA_{data['userName']}_{data['taskName']}"
        if key not in self.work_items:
            return

        # UI 控制锁
        with self.web_lock:
            work_item_tuple = self.work_items[key]
            task_id = work_item_tuple[0]

            complete_task_by_id(task_id)

        print(f"任务完成确认 -- {key}")
        del self.work_items[key]


if __name__ == "__main__":
    server = CenterServer()
    server.start_server()
