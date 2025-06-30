import re
from fileTools import *
from configLoader import config
from bpmApiClient import create_bpm_client

# 全局BMP客户端实例
bpm_client = None
RF_DICT = config.get_rpa_filename_mapping()
RP_DICT = config.get_rpa_processid_mapping()
TRIGGER_FOLDER_PATH = config.get_trigger_folder_path()


def init_bpm_client():
    """初始化BPM客户端"""
    global bpm_client
    try:
        platform = config.get_bpm_platform()
        bpm_client = create_bpm_client(platform)
        return bpm_client.authenticate()
    except Exception as e:
        sys.stderr.write(f"BPM客户端初始化失败: {str(e)}\n")
        return False



def get_bpm_client():
    global bpm_client
    if bpm_client is None:
        init_bpm_client()
    return bpm_client


def check_work_item():
    try:
        client = get_bpm_client()
        if not client:
            return False
        tasks = client.get_task_list()
        # tasks = [task for task in tasks if task.get("taskState") != "COMPLETED"] # 否则死循环
        return len(tasks) > 0
    except Exception as e:
        sys.stderr.write(f"检查工作项失败：{str(e)}\n")
        return False



def get_work_item_data():# 添加一个判断work item的名字是否出现在mapping中，出现了再return res
    """获取工作项数据，只有当任务名称在映射配置中存在时才返回数据"""
    try:
        client = get_bpm_client()
        if not client:
            return {}

        tasks = client.get_task_list()
        if not tasks:
            return {}

        # 获取RPA文件名映射配置
        rpa_mapping = config.get_rpa_filename_mapping()

        # 遍历所有任务，找到第一个在映射中的任务
        for task in tasks:
            task_name = task.get('name', '')
            # 检查任务名称是否在映射配置中
            if task_name in rpa_mapping:
                task_data = client.get_task_data(task.get('id', ''))
                res = {}
                res["taskName"] = task_data.get('name', '')
                res["taskId"] = task_data.get('id', '')
                return res

        # 如果没有找到匹配的任务，返回空字典
        return {}
    except Exception as e:
        sys.stderr.write(f"获取工作项数据失败：{str(e)}\n")
        return {}

## 触发RPA
def trigger_rpa(data):
    """
    根据配置项决定使用API触发还是文件触发
    """
    try:
        taskname = data["taskName"]
        filename = RF_DICT.get(taskname, '')
        taskID = RP_DICT.get(taskname, '')

        if not taskID:
            print(f"未找到任务 {taskname} 对应的配置")
            return

        # 获取触发方式配置
        uipath_method = config.get_uipath_method()

        if uipath_method == "api":
            print("使用API方式触发RPA")
            trigger_rpa_api(taskID)
        elif uipath_method == "file":
            print("使用文件方式触发RPA")
            trigger_rpa_file(filename)
        else:
            print(f"未知的触发方式: {uipath_method}，默认使用API方式")
            trigger_rpa_api(taskID)

    except Exception as e:
        sys.stderr.write(f"触发RPA任务失败：{str(e)}\n")


def trigger_rpa_api(taskID):
    """
    使用API方式触发RPA
    """
    try:
        trigger_rpa_job(taskID)
        wait_rpa_job_completion(taskID)
    except Exception as e:
        sys.stderr.write(f"API触发RPA任务失败：{str(e)}\n")


def trigger_rpa_file(filename):
    """
    使用文件方式触发RPA
    """
    try:
        create_file(filename)
        wait_delete_file(filename)
    except Exception as e:
        sys.stderr.write(f"文件触发RPA任务失败：{str(e)}\n")

def finish_work_item(task_data=None):
    client = get_bpm_client()
    if not client or not task_data:
        return False

    task_id = task_data.get("taskId", "")
    if task_id:
        return client.complete_task(task_id)
    sys.stderr.write("taskId不存在，工作项完成失败\n")
    return False


def match_taskname(taskname):
    pattern = re.compile(r'RPA_([a-zA-Z0-9]+)_([a-zA-Z0-9]+)')
    return re.fullmatch(pattern, taskname) != None


def start_IBP(pname):
    client = get_bpm_client()
    if not client:
        return False

    return client.start_process(pname)


def validate_work_item(dict, superman_items):
    client = get_bpm_client()
    if not client:
        return False

    res = False
    tasks = client.get_task_list()

    for task in tasks:
        taskname = task.get('name', '')
        task_id = task.get('id', '')

        if taskname in superman_items:
            start_IBP(superman_items[taskname])
            continue

        if match_taskname(taskname) and taskname not in dict:
            res = True
            dict[taskname] = (task_id, 0)
            print(f"检测到工作项 {taskname}")

    return res


def get_work_item_data_superman(taskname):
    res = {}
    name_list = taskname.split('_')
    res["userName"] = name_list[1]
    res["taskName"] = name_list[2]
    return res

def get_taskname():
    client = get_bpm_client()
    if not client:
        return ""

    tasks = client.get_task_list()
    if not tasks:
        return ""

    return tasks[0].get('name', '')


def send_work_item_by_id(task_id):
    client = get_bpm_client()
    if not client:
        return {}

    task_data = client.get_task_data(task_id)
    return task_data


def complete_task_by_id(task_id):
    client = get_bpm_client()
    if not client:
        return False
    return client.complete_task(task_id)