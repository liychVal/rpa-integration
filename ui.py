import flet as ft
import json
import subprocess
import threading
import sys
import os
from datetime import datetime

class RPAIntegrationUI:
    # 封装一些函数
    def __init__(self):
        self.config_path = "config.json"
        self.current_process = None
        self.current_script = None  # 直接利用这个变量判断日志类型
        self.page = None
        self.log_output = None
        self.history_log_output = None
        self.config_data = self.load_config()
        self.log_dir = os.path.join(os.path.dirname(self.config_path), "logs")
        self.history_log_type = None  # 当前查看的历史日志类型
        self.log_level_filter = "ALL"
        self.log_level_dropdown = None
        # 用于跟踪键值对容器的引用
        self.keyvalue_containers = {}
        os.makedirs(self.log_dir, exist_ok=True)

    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            error_message = f"配置文件未找到: {self.config_path}，请先创建配置文件！"
            if self.log_output:
                self.log_message(error_message, "error")
            raise FileNotFoundError(error_message)

    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            self.log_message("配置保存成功！", "success")
            # 显示保存成功的提示
            if self.page:
                self.show_snack_bar("配置保存成功！", ft.colors.GREEN)
        except Exception as e:
            error_msg = f"配置保存失败: {e}"
            self.log_message(error_msg, "error")
            if self.page:
                self.show_snack_bar(error_msg, ft.colors.RED)

    def show_snack_bar(self, message, color):
        """显示提示消息"""
        snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.colors.WHITE),
            bgcolor=color,
            duration=3000,
        )
        self.page.overlay.append(snack_bar)
        snack_bar.open = True
        self.page.update()

    def get_log_file_path(self):
        """根据当前脚本类型获取日志文件路径"""
        if not self.current_script:
            return os.path.join(self.log_dir, "system.log")

        # 从脚本路径提取类型
        if "IOP_integration/client.py" in self.current_script:
            log_type = "iop_client"
        elif "IBP_integration/client_rpa.py" in self.current_script:
            log_type = "ibp_client"
        elif "IBP_integration/service_user.py" in self.current_script:
            log_type = "ibp_service"
        else:
            log_type = "system"

        return os.path.join(self.log_dir, f"{log_type}.log")

    def log_message(self, message, msg_type="info"):
        """添加日志消息（自动根据当前脚本选择日志文件）"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_text = f"[{timestamp}] [{msg_type.upper()}] {message}"

        # 1. 输出到UI界面
        if self.log_output:
            color = {
                "info": ft.colors.BLUE,
                "success": ft.colors.GREEN,
                "error": ft.colors.RED,
                "warning": ft.colors.ORANGE
            }.get(msg_type, ft.colors.BLACK)

            log_entry = ft.Text(log_text, color=color, size=12)
            self.log_output.controls.append(log_entry)
            if len(self.log_output.controls) > 100:
                self.log_output.controls.pop(0)
            try:
                if self.page and hasattr(self.log_output, 'page') and self.log_output.page: # 避免保存配置时错误
                    self.log_output.scroll_to(offset=-1)
            except:
                pass

        # 2. 持久化到日志文件
        try:
            with open(self.get_log_file_path(), 'a', encoding='utf-8') as f:
                f.write(log_text + '\n')
        except Exception as e:
            print(f"日志写入失败: {e}")

        if self.page:
            self.page.update()

    def create_config_form(self):
        """创建配置表单"""
        config_fields = []

        # 服务器配置
        config_fields.append(ft.Text("服务器配置", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE))
        config_fields.append(ft.TextField(
            label="服务器主机",
            value=self.config_data["server"]["host"],
            on_change=lambda e: self.update_config_value("server.host", e.control.value)
        ))
        config_fields.append(ft.TextField(
            label="服务器端口",
            value=str(self.config_data["server"]["port"]),
            on_change=lambda e: self.update_config_value("server.port",
                                                         int(e.control.value) if e.control.value.isdigit() else 55332)
        ))
        config_fields.append(ft.TextField(
            label="最大连接数",
            value=str(self.config_data["server"]["max_connections"]),
            on_change=lambda e: self.update_config_value("server.max_connections",
                                                         int(e.control.value) if e.control.value.isdigit() else 5)
        ))
        config_fields.append(ft.TextField(
            label="客户端主机",
            value=self.config_data["server"]["client_host"],
            on_change=lambda e: self.update_config_value("server.client_host", e.control.value)
        ))

        # Superman Items配置 - 动态键值对
        config_fields.append(ft.Divider(height=20))
        config_fields.append(ft.Text("Superman Items配置", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE))
        superman_items_section = self.create_keyvalue_section("superman_items", "Superman Items")
        config_fields.append(superman_items_section)

        # Camunda8配置
        config_fields.append(ft.Divider(height=20))
        config_fields.append(ft.Text("Camunda8配置", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE))
        config_fields.append(ft.TextField(
            label="BASE URL",
            value=self.config_data["camunda8"]["base_url"],
            on_change=lambda e: self.update_config_value("camunda8.base_url", e.control.value)
        ))
        config_fields.append(ft.TextField(
            label="用户名",
            value=self.config_data["camunda8"]["username"],
            on_change=lambda e: self.update_config_value("camunda8.username", e.control.value)
        ))
        config_fields.append(ft.TextField(
            label="密码",
            value=self.config_data["camunda8"]["password"],
            password=True,
            can_reveal_password=True,
            on_change=lambda e: self.update_config_value("camunda8.password", e.control.value)
        ))

        # Camunda7配置
        config_fields.append(ft.Divider(height=20))
        config_fields.append(ft.Text("Camunda7配置", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE))
        config_fields.append(ft.TextField(
            label="平台",
            value=self.config_data["camunda7"]["platform"],
            on_change=lambda e: self.update_config_value("camunda7.platform", e.control.value)
        ))
        config_fields.append(ft.TextField(
            label="Base URL",
            value=self.config_data["camunda7"]["base_url"],
            on_change=lambda e: self.update_config_value("camunda7.base_url", e.control.value)
        ))
        config_fields.append(ft.TextField(
            label="用户名",
            value=self.config_data["camunda7"]["username"],
            on_change=lambda e: self.update_config_value("camunda7.username", e.control.value)
        ))
        config_fields.append(ft.TextField(
            label="密码",
            value=self.config_data["camunda7"]["password"],
            password=True,
            can_reveal_password=True,
            on_change=lambda e: self.update_config_value("camunda7.password", e.control.value)
        ))

        # 时间配置
        config_fields.append(ft.Divider(height=20))
        config_fields.append(ft.Text("时间配置", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE))
        config_fields.append(ft.TextField(
            label="睡眠间隔(秒)",
            value=str(self.config_data["timing"]["sleep_interval"]),
            on_change=lambda e: self.update_config_value("timing.sleep_interval",
                                                         int(e.control.value) if e.control.value.isdigit() else 60)
        ))
        config_fields.append(ft.TextField(
            label="短睡眠时间(秒)",
            value=str(self.config_data["timing"]["short_sleep"]),
            on_change=lambda e: self.update_config_value("timing.short_sleep",
                                                         int(e.control.value) if e.control.value.isdigit() else 2)
        ))
        config_fields.append(ft.TextField(
            label="RPA检查间隔(秒)",
            value=str(self.config_data["timing"]["rpa_check_interval"]),
            on_change=lambda e: self.update_config_value("timing.rpa_check_interval",
                                                         int(e.control.value) if e.control.value.isdigit() else 2)
        ))

        # UiPath配置
        config_fields.append(ft.Divider(height=20))
        config_fields.append(ft.Text("UiPath配置", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE))

        # 新增method字段
        config_fields.append(ft.TextField(
            label="方法",
            value=self.config_data["uipath"]["method"],
            on_change=lambda e: self.update_config_value("uipath.method", e.control.value)
        ))

        # 新增folder_path字段
        config_fields.append(ft.TextField(
            label="文件夹路径",
            value=self.config_data["uipath"]["folder_path"],
            on_change=lambda e: self.update_config_value("uipath.folder_path", e.control.value)
        ))

        config_fields.append(ft.TextField(
            label="组织",
            value=self.config_data["uipath"]["organization"],
            on_change=lambda e: self.update_config_value("uipath.organization", e.control.value)
        ))
        config_fields.append(ft.TextField(
            label="租户",
            value=self.config_data["uipath"]["tenant"],
            on_change=lambda e: self.update_config_value("uipath.tenant", e.control.value)
        ))
        config_fields.append(ft.TextField(
            label="Personal Access Token",
            value=self.config_data["uipath"]["pat"],
            password=True,
            can_reveal_password=True,
            on_change=lambda e: self.update_config_value("uipath.pat", e.control.value)
        ))
        config_fields.append(ft.TextField(
            label="文件夹ID",
            value=str(self.config_data["uipath"]["folder_id"]),
            on_change=lambda e: self.update_config_value("uipath.folder_id",
                                                         int(e.control.value) if e.control.value.isdigit() else 0)
        ))
        config_fields.append(ft.TextField(
            label="机器人ID",
            value=str(self.config_data["uipath"]["robot_id"]),
            on_change=lambda e: self.update_config_value("uipath.robot_id",
                                                         int(e.control.value) if e.control.value.isdigit() else 0)
        ))

        # UiPath设置配置
        config_fields.append(ft.Divider(height=20))
        config_fields.append(ft.Text("UiPath设置", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE))
        config_fields.append(ft.TextField(
            label="轮询间隔(秒)",
            value=str(self.config_data["uipath_settings"]["poll_interval"]),
            on_change=lambda e: self.update_config_value("uipath_settings.poll_interval",
                                                         int(e.control.value) if e.control.value.isdigit() else 5)
        ))
        config_fields.append(ft.TextField(
            label="最大尝试次数",
            value=str(self.config_data["uipath_settings"]["max_attempts"]),
            on_change=lambda e: self.update_config_value("uipath_settings.max_attempts",
                                                         int(e.control.value) if e.control.value.isdigit() else 60)
        ))

        # RPA文件名映射配置 - 动态键值对
        config_fields.append(ft.Divider(height=20))
        config_fields.append(ft.Text("RPA文件名映射", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE))
        rpa_mapping_section = self.create_keyvalue_section("rpa_filename_mapping", "RPA文件名映射")
        config_fields.append(rpa_mapping_section)

        # 新增RPA进程ID映射配置 - 动态键值对
        config_fields.append(ft.Divider(height=20))
        config_fields.append(ft.Text("RPA进程ID映射", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE))
        rpa_processid_mapping_section = self.create_keyvalue_section("rpa_processid_mapping", "RPA进程ID映射")
        config_fields.append(rpa_processid_mapping_section)

        # 保存按钮
        config_fields.append(ft.Divider(height=30))
        config_fields.append(ft.ElevatedButton(
            "保存配置",
            icon=ft.icons.SAVE,
            on_click=lambda e: self.save_config(),
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE_600
            )
        ))

        return ft.Column(
            controls=config_fields,
            scroll=ft.ScrollMode.AUTO,
            spacing=10
        )

    def create_keyvalue_section(self, config_key, section_name):
        """创建动态键值对配置区域"""
        # 获取当前配置数据
        current_data = self.config_data.get(config_key, {})

        # 创建键值对行的列表
        keyvalue_rows = []

        # 为现有的键值对创建编辑行
        for key, value in current_data.items():
            row = self.create_keyvalue_row(config_key, key, str(value))
            keyvalue_rows.append(row)

        # 创建包含所有键值对行的容器
        keyvalue_container = ft.Column(
            controls=keyvalue_rows,
            spacing=5
        )

        # 保存容器引用用于后续操作
        self.keyvalue_containers[config_key] = keyvalue_container

        # 添加新键值对按钮
        add_button = ft.ElevatedButton(
            f"添加新的{section_name}项",
            icon=ft.icons.ADD,
            on_click=lambda e: self.add_keyvalue_pair(config_key),
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.GREEN_400,
                text_style=ft.TextStyle(size=12)
            )
        )

        return ft.Column([
            keyvalue_container,
            ft.Container(height=10),
            add_button
        ], spacing=0)

    def create_keyvalue_row(self, config_key, key="", value=""):
        """创建单个键值对编辑行"""
        original_key = key  # 保存原始键值用于后续操作

        key_field = ft.TextField(
            label="键",
            value=key,
            width=200,
            height=50,
            on_blur=lambda e: self.update_keyvalue_on_blur(config_key, original_key, e.control.value, value_field.value)
        )

        value_field = ft.TextField(
            label="值",
            value=value,
            width=300,
            height=50,
            on_blur=lambda e: self.update_keyvalue_on_blur(config_key, original_key, key_field.value, e.control.value)
        )

        delete_button = ft.IconButton(
            icon=ft.icons.DELETE,
            icon_color=ft.colors.RED,
            tooltip="删除此项",
            on_click=lambda e: self.delete_keyvalue_pair(config_key, original_key, row)
        )

        row = ft.Row([
            key_field,
            value_field,
            delete_button
        ], spacing=10, alignment=ft.MainAxisAlignment.START)

        # 在创建时设置字段的引用，以便删除时能正确更新
        row.data = {
            'original_key': original_key,
            'key_field': key_field,
            'value_field': value_field
        }

        return row

    def update_keyvalue_on_blur(self, config_key, original_key, new_key, value):
        """当字段失去焦点时更新键值对"""
        if config_key not in self.config_data:
            self.config_data[config_key] = {}

        # 如果原始键存在且与新键不同，删除原始键
        if original_key and original_key != new_key and original_key in self.config_data[config_key]:
            del self.config_data[config_key][original_key]

        # 只有当键不为空时才设置新的键值对
        if new_key.strip():
            self.config_data[config_key][new_key] = value
            # 更新该行的original_key引用
            for row in self.keyvalue_containers[config_key].controls:
                if hasattr(row, 'data') and row.data['original_key'] == original_key:
                    row.data['original_key'] = new_key
                    break

    def add_keyvalue_pair(self, config_key):
        """添加新的键值对"""
        if config_key not in self.keyvalue_containers:
            return

        new_row = self.create_keyvalue_row(config_key, "", "")
        self.keyvalue_containers[config_key].controls.append(new_row)
        self.page.update()

    def delete_keyvalue_pair(self, config_key, key, row):
        """删除键值对"""
        # 从配置数据中删除
        if key and config_key in self.config_data and key in self.config_data[config_key]:
            del self.config_data[config_key][key]

        # 从UI容器中移除行
        if config_key in self.keyvalue_containers:
            container = self.keyvalue_containers[config_key]
            if row in container.controls:
                container.controls.remove(row)

        self.page.update()
        self.log_message(f"已删除键值对: {key}", "info")

    def update_config_value(self, key_path, value):
        """更新配置值"""
        keys = key_path.split('.')
        current = self.config_data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def run_script(self, script_name):
        """运行脚本"""
        if self.current_process and self.current_process.poll() is None:
            self.log_message("已有脚本在运行中，请先停止当前脚本！", "warning")
            return

        if not os.path.exists(script_name):
            self.log_message(f"脚本文件 {script_name} 不存在！", "error")
            return

        try:
            self.clear_log()
            self.current_script = script_name
            self.log_message(f"开始运行脚本: {script_name}", "info")

            # 在新线程中运行脚本
            thread = threading.Thread(target=self._run_script_thread, args=(script_name,))
            thread.daemon = True
            thread.start()

        except Exception as e:
            self.log_message(f"运行脚本失败: {e}", "error")

    def _run_script_thread(self, script_name):
        """在线程中运行脚本"""
        try:
            # 设置环境变量强制使用UTF-8编码
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            self.current_process = subprocess.Popen(
                [sys.executable, script_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                encoding='utf-8',  # 明确指定编码
                errors='replace',  # 遇到无法解码的字符时用替代字符替换
                env=env  # 传递环境变量
            )

            # 创建线程来分别处理stdout和stderr
            def read_stdout():
                try:
                    for line in iter(self.current_process.stdout.readline, ''):
                        if line.strip():  # 只处理非空行
                            self.log_message(f"[{os.path.basename(self.current_script)}] {line.strip()}", "info")
                except Exception as e:
                    self.log_message(f"读取标准输出异常: {e}", "error")

            def read_stderr():
                try:
                    for line in iter(self.current_process.stderr.readline, ''):
                        if line.strip():  # 只处理非空行
                            self.log_message(f"[{os.path.basename(self.current_script)}] {line.strip()}", "error")
                except Exception as e:
                    self.log_message(f"读取标准错误输出异常: {e}", "error")

            # 启动读取线程
            stdout_thread = threading.Thread(target=read_stdout)
            stderr_thread = threading.Thread(target=read_stderr)
            stdout_thread.daemon = True
            stderr_thread.daemon = True

            stdout_thread.start()
            stderr_thread.start()

            # 等待进程结束
            self.current_process.wait()

            # 等待读取线程结束
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)

            if self.current_process.returncode == 0:
                self.log_message(f"脚本 {script_name} 执行完成", "success")
            else:
                self.log_message(f"脚本 {script_name} 执行失败，返回码: {self.current_process.returncode}", "error")

        except Exception as e:
            self.log_message(f"脚本执行异常: {e}", "error")
        finally:
            self.current_process = None
            self.current_script = None

    def stop_script(self):
        """停止当前运行的脚本"""
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
                self.log_message(f"脚本 {self.current_script} 已停止", "warning")
            except Exception as e:
                self.log_message(f"停止脚本失败: {e}", "error")
        else:
            self.log_message("没有正在运行的脚本", "warning")

    def clear_log(self):
        """清空日志"""
        if self.log_output:
            self.log_output.controls.clear()
            self.page.update()

    def create_run_view(self):
        """创建运行视图"""
        # IOP区域
        iop_section = ft.Column([
            ft.Text("IOP", size=16, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_700),
            ft.Container(height=15),  # 间距
            ft.ElevatedButton(
                "运行 IOP Client",
                icon=ft.icons.PLAY_ARROW,
                height=45,
                width=180,
                on_click=lambda e: self.run_script("IOP_integration/client.py"),
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.GREEN_400,
                    text_style=ft.TextStyle(size=14)
                )
            ),
        ], spacing=0)

        # IBP区域
        ibp_section = ft.Column([
            ft.Text("IBP", size=16, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_700),
            ft.Container(height=15),  # 间距
            ft.ElevatedButton(
                "运行 IBP Client",
                icon=ft.icons.PLAY_ARROW,
                height=45,
                width=180,
                on_click=lambda e: self.run_script("IBP_integration/client_rpa.py"),
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.GREEN_400,
                    text_style=ft.TextStyle(size=14)
                )
            ),
            ft.Container(height=12),  # 按钮间距
            ft.ElevatedButton(
                "运行 IBP Service",
                icon=ft.icons.PLAY_ARROW,
                height=45,
                width=180,
                on_click=lambda e: self.run_script("IBP_integration/service_user.py"),
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.GREEN_400,
                    text_style=ft.TextStyle(size=14)
                )
            ),
        ], spacing=0)

        # 底部控制按钮
        bottom_controls = ft.Column([
            ft.ElevatedButton(
                "停止脚本",
                icon=ft.icons.STOP,
                height=45,
                width=180,
                on_click=lambda e: self.stop_script(),
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.RED_300,
                    text_style=ft.TextStyle(size=14)
                )
            ),
            ft.Container(height=12),  # 按钮间距
            ft.ElevatedButton(
                "清空日志",
                icon=ft.icons.CLEAR,
                height=45,
                width=180,
                on_click=lambda e: self.clear_log(),
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.ORANGE_300,
                    text_style=ft.TextStyle(size=14)
                )
            )
        ], spacing=0)

        # 脚本控制面板
        script_controls = ft.Column([
            iop_section,
            ft.Container(height=30),  # 区域间距
            ibp_section,
            ft.Container(expand=True),  # 占据剩余空间，将底部控制推到底部
            bottom_controls
        ], spacing=0, expand=True)

        # 日志输出区域
        if(self.log_output == None):
            self.log_output = ft.Column([], scroll=ft.ScrollMode.AUTO, spacing=2)
        log_container = ft.Container(
            content=self.log_output,
            bgcolor=ft.colors.GREY_50,
            border=ft.border.all(1, ft.colors.GREY_400),
            border_radius=5,
            padding=10,
            width=900, # None为自适应
            height=600,  # 固定高度
        )

        return ft.Row([
            ft.Container(
                content=script_controls,
                width=220,
                padding=ft.padding.all(15),
                height=700
            ),
            ft.VerticalDivider(width=1),
            ft.Container(
                content=ft.Column([
                    ft.Text("运行日志", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE),
                    log_container
                ], spacing=10),
                expand=True,
                padding=10
            )
        ], expand=True)

    def _reset_log_filter(self):
        """原子化重置筛选条件"""
        self.log_level_filter = "ALL"
        if hasattr(self, 'log_level_dropdown'):
            self.log_level_dropdown.value = "ALL"
            self.log_level_dropdown.update()
        self.page.update()

    def _update_date_filter(self, e):
        """更新选择的日期"""
        self.selected_date = e.control.value
        self.load_history_log(self.history_log_type)

    def _clear_date_filter(self):
        """清除日期筛选"""
        self.selected_date = None
        self.date_picker.value = None
        self.load_history_log(self.history_log_type)



    def create_history_log_view(self):
        """创建历史日志视图"""

        if(self.log_level_dropdown == None):
            # 日志级别筛选控件
            self.log_level_dropdown = ft.Dropdown(
                width=150,
                height=40,
                value="ALL",
                options=[
                    ft.dropdown.Option("ALL", text="全部日志"),
                    ft.dropdown.Option("INFO", text="信息"),
                    ft.dropdown.Option("SUCCESS", text="成功"),
                    ft.dropdown.Option("WARNING", text="警告"),
                    ft.dropdown.Option("ERROR", text="错误"),
                ],
                text_size=12,
                border_color=ft.colors.WHITE,
                focused_border_color=ft.colors.WHITE,  # 聚焦时保持相同颜色
                border_radius=4,
                content_padding=10,
                bgcolor=ft.colors.GREY_50,
                filled=True,  # 启用填充背景色
                color=ft.colors.BLACK,  # 文字颜色
                on_change=lambda e: self.filter_history_log(e.control.value),
            )

        # 历史日志按钮区域
        history_controls = ft.Column([
            ft.Text("历史日志", size=16, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_700),
            ft.Container(height=15),
            ft.ElevatedButton(
                "查看系统日志",
                icon=ft.icons.HISTORY,
                height=45,
                width=180,
                on_click=lambda e: [
                    self._reset_log_filter(),
                    self.load_history_log("system"),
                ],
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.BLUE_400,
                    text_style=ft.TextStyle(size=14)
                )
            ),
            ft.Container(height=12),
            ft.ElevatedButton(
                "查看IOP Client日志",
                icon=ft.icons.HISTORY,
                height=45,
                width=180,
                on_click=lambda e: [
                    self._reset_log_filter(),
                    self.load_history_log("iop_client"),
                ],
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.BLUE_400,
                    text_style=ft.TextStyle(size=14)
                )
            ),
            ft.Container(height=12),
            ft.ElevatedButton(
                "查看IBP Client日志",
                icon=ft.icons.HISTORY,
                height=45,
                width=180,
                on_click=lambda e: [
                    self._reset_log_filter(),
                    self.load_history_log("ibp_client"),
                ],
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.BLUE_400,
                    text_style=ft.TextStyle(size=14)
                )
            ),
            ft.Container(height=12),
            ft.ElevatedButton(
                "查看IBP Service日志",
                icon=ft.icons.HISTORY,
                height=45,
                width=180,
                on_click=lambda e: [
                    self._reset_log_filter(),
                    self.load_history_log("ibp_service"),
                ],
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.BLUE_400,
                    text_style=ft.TextStyle(size=14)
                )
            )
        ], spacing=0)

        # 历史日志显示区域
        if(self.history_log_output == None):
            self.history_log_output = ft.Column([], scroll=ft.ScrollMode.AUTO, spacing=2)
        history_log_container = ft.Container(
            content=self.history_log_output,
            bgcolor=ft.colors.GREY_50,
            border=ft.border.all(1, ft.colors.GREY_400),
            border_radius=5,
            padding=10,
            width=900, # None为自适应
            height=600,  # 固定高度
        )

        title_row = ft.Row([
            ft.Text("历史日志", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE),
            ft.Container(expand=True),  # 占位空间
            ft.Row([
                ft.Text("筛选:", size=14),
                self.log_level_dropdown
            ], spacing=10)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        return ft.Row([
            ft.Container(
                content=history_controls,
                width=220,
                padding=ft.padding.all(15),
                height=700
            ),
            ft.VerticalDivider(width=1),
            ft.Container(
                content=ft.Column([
                    title_row,
                    history_log_container
                ], spacing=10),
                expand=True,
                padding=10
            )
        ], expand=True)

    def filter_history_log(self, level):
        """确保筛选条件同步到属性和控件"""
        self.log_level_filter = level
        if hasattr(self, 'log_level_dropdown'):
            self.log_level_dropdown.value = level
        self.load_history_log(self.history_log_type)


    def load_history_log(self, log_type):
        """从文件加载历史日志"""
        self.history_log_type = log_type
        log_file = os.path.join(self.log_dir, f"{log_type}.log")

        # 确保历史日志输出区域已初始化
        if not self.history_log_output:
            return

        # 清空现有日志
        self.history_log_output.controls.clear()

        # 检查文件是否存在
        if not os.path.exists(log_file):
            self.history_log_output.controls.append(
                ft.Text(f"-------------------空-------------------", color=ft.colors.BLUE, size=12)
            )
            self.page.update()
            return

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 如果文件存在但为空
            if not lines:
                self.history_log_output.controls.append(
                    ft.Text("-------------------空-------------------", color=ft.colors.BLUE, size=12)
                )
            else:
                for line in lines:
                    # 根据筛选条件显示日志
                    if self.log_level_filter == "ALL" or f"[{self.log_level_filter}]" in line:
                        # 根据日志级别自动着色
                        if "[ERROR]" in line:
                            color = ft.colors.RED
                        elif "[WARNING]" in line:
                            color = ft.colors.ORANGE
                        elif "[SUCCESS]" in line:
                            color = ft.colors.GREEN
                        elif "[INFO]" in line:
                            color = ft.colors.BLUE
                        else:
                            color = ft.colors.BLACK

                        self.history_log_output.controls.append(
                            ft.Text(line.strip(), color=color, size=12)
                        )

            self.history_log_output.scroll_to(offset=-1)

        except Exception as e:
            self.history_log_output.controls.append(
                ft.Text(f"加载日志失败: {e}", color=ft.colors.RED)
            )

        self.page.update()


    def main(self, page: ft.Page):
        self.page = page
        page.title = "RPA Integation"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window.width = 1200
        page.window.height = 800
        page.window.min_width = 800
        page.window.min_height = 600
        page.window.maximizable = False # 最大化禁止

        def nav_click(nav_item, view_content):# 在main内定义 才能用nav_rail等容器
            # 更新导航样式
            for nav in nav_rail.controls:
                if hasattr(nav, 'bgcolor'):
                    nav.bgcolor = ft.colors.TRANSPARENT
            nav_item.bgcolor = ft.colors.BLUE_100

            # 更新内容区域
            content_area.content = view_content
            page.update()

        # 导航栏
        config_nav = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.SETTINGS, color=ft.colors.BLUE_600),
                ft.Text("配置", size=16, color=ft.colors.BLUE_600)
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=15, vertical=12),
            border_radius=8,
            bgcolor=ft.colors.BLUE_100,
            on_click=lambda e: nav_click(config_nav, self.create_config_form())
        )

        run_nav = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.PLAY_CIRCLE, color=ft.colors.BLUE_600),
                ft.Text("运行", size=16, color=ft.colors.BLUE_600)
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=15, vertical=12),
            border_radius=8,
            bgcolor=ft.colors.TRANSPARENT,
            on_click=lambda e: nav_click(run_nav, self.create_run_view())
        )

        # 在导航栏中添加历史日志按钮
        history_nav = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.HISTORY, color=ft.colors.BLUE_600),
                ft.Text("历史日志", size=16, color=ft.colors.BLUE_600)
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=15, vertical=12),
            border_radius=8,
            bgcolor=ft.colors.TRANSPARENT,
            on_click=lambda e: nav_click(history_nav, self.create_history_log_view())
        )

        nav_rail = ft.Column([
            ft.Container(
                content=ft.Text("RPA-integration", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_700),
                padding=ft.padding.symmetric(horizontal=15, vertical=20)
            ),
            ft.Divider(height=1, color=ft.colors.GREY_300),
            config_nav,
            run_nav,
            history_nav
        ], spacing=5)


        # 内容区域
        content_area = ft.Container(
            content=self.create_config_form(),  # 默认显示配置页面，后续可以改一个欢迎界面
            expand=True,
            padding=20
        )

        # 主布局
        main_layout = ft.Row([
            ft.Container(
                content=nav_rail,
                width=200,
                # bgcolor=ft.colors.GREY_50,
                border=ft.border.only(right=ft.BorderSide(1, ft.colors.GREY_300)),
                padding=ft.padding.only(top=10, bottom=10)
            ),
            content_area
        ], expand=True)

        page.add(main_layout)

        # 初始化日志
        self.log_message("RPA Integration 系统已启动", "success")


def main(page: ft.Page):
    app = RPAIntegrationUI()
    app.main(page)


if __name__ == "__main__":
    ft.app(target=main)