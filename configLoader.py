import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
class ConfigLoader:
    def __init__(self, config_path: str = "E:\\python_file\\2025\\rpa-integration\\config.json"):
        # 初始化
        self.config_path = Path(config_path)
        self._config = None
        self._load_config()

    def _load_config(self) -> None:
        # 加载配置文件
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件 {self.config_path} 不存在")

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
        except Exception as e:
            raise Exception(f"读取配置文件失败: {e}")

    def reload_config(self) -> None:
        # 重新加载
        self._load_config()

    def get(self, key: str, default: Any = None) -> Any:
        # 获取配置项
        if self._config is None:
            return default

        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy() if self._config else {}

    # === 服务器配置 ===
    def get_server_host(self) -> str:
        """获取服务器主机地址"""
        return self.get('server.host', '0.0.0.0')

    def get_server_port(self) -> int:
        """获取服务器端口"""
        return self.get('server.port', 55332)

    def get_max_connections(self) -> int:
        """获取最大连接数"""
        return self.get('server.max_connections', 5)

    def get_client_host(self) -> str:
        """获取客户端主机地址"""
        return self.get('server.client_host', '127.0.0.1')

    # === RPA映射 ===
    def get_rpa_filename_mapping(self) -> Dict[str, str]:
        """获取RPA文件名映射"""
        return self.get('rpa_filename_mapping', {})
    def get_rpa_processid_mapping(self) ->Dict[str, str]:
        """获取RPA进程id映射"""
        return self.get('rpa_processid_mapping',{})

    # === Superman项目配置 ===
    def get_superman_items(self) -> Dict[str, str]:
        """获取Superman项目配置"""
        return self.get('superman_items', {})

    # === camunda7配置 ===
    def get_camunda7_url(self) -> str:
        return self.get('camunda7.base_url', '')

    def get_camunda7_username(self) -> str:
        return self.get('camunda7.username', '')

    def get_camunda7_password(self) -> str:
        return self.get('camunda7.password', '')

    def get_bpm_platform(self) -> str:
        return self.get('camunda7.platform', 'camunda7')

    # === camunda8配置 ===

    def get_camunda8_base_url(self) -> str:
        return self.get('camunda8.base_url', '')

    def get_camunda8_username(self) -> str:
        return self.get('camunda8.username','')

    def get_camunda8_password(self) -> str:
        return self.get('camunda8.password', '')
    # === 时间配置 ===
    def get_sleep_interval(self) -> int:
        """获取睡眠间隔"""
        return self.get('timing.sleep_interval', 60)

    def get_short_sleep(self) -> int:
        """获取短睡眠时间"""
        return self.get('timing.short_sleep', 2)

    def get_rpa_check_interval(self) -> int:
        """获取RPA检查间隔"""
        return self.get('timing.rpa_check_interval', 2)

    # === uipath调用 ===
    def get_trigger_folder_path(self)->str:
        return self.get('uipath.folder_path','')
    def get_uipath_method(self) -> str:
        return self.get('uipath.method', 'file')
    def get_uipath_organization(self) -> str:
        return self.get('uipath.organization', 'your-organization')

    def get_uipath_tenant(self) -> str:
        return self.get('uipath.tenant', 'DefaultTenant')

    def get_uipath_pat(self) -> str:
        return self.get('uipath.pat', 'your-personal-access-token')

    def get_uipath_folder_id(self) -> int:
        return self.get('uipath.folder_id', 0)

    def get_uipath_robot_id(self) -> int:
        return self.get('uipath.robot_id', 0)

    def get_uipath_poll_interval(self) -> int:
        """获取轮询间隔（秒）"""
        return self.get('uipath.poll_interval', 5)

    def get_uipath_max_attempts(self) -> int:
        """获取最大轮询尝试次数"""
        return self.get('uipath.max_attempts', 60)

    # === 配置更新方法 ===
    def update_config(self, key: str, value: Any) -> None:
        if self._config is None:
            self._config = {}

        keys = key.split('.')
        current = self._config

        # 导航到目标位置
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # 设置值
        current[keys[-1]] = value

        # 保存到文件
        self.save_config()

    def save_config(self) -> None:
        """保存配置到文件"""
        if self._config is None:
            return

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"保存配置文件失败: {e}")


# 全局配置实例
config = ConfigLoader()


# 便捷函数
def get_config(key: str, default: Any = None) -> Any:
    """获取配置项"""
    return config.get(key, default)


def reload_config() -> None:
    """重新加载配置"""
    config.reload_config()


def update_config(key: str, value: Any) -> None:
    """更新配置"""
    config.update_config(key, value)