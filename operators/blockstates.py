import json
import math
import os
from .model import extract_vertices_from_elements
from .functions import get_file_path, get_all_data

def blockstates(pos, id, has_air, vertices, faces, direction, texture_list, uv_list, uv_rotation_list, vertices_dict):
    block_name = id.split('[')[0]
    filepath = get_file_path(block_name, 's')
    rotation = [0, 0, 0]
    # 获取方块属性的起始位置和结束位置
    start_index = id.find('[')
    end_index = id.find(']')
    # 如果找不到方块属性，则使用空字典
    properties_dict = {}
    if start_index != -1 and end_index != -1:
        # 使用字符串切片来提取方块属性部分
        properties_str = id[start_index + 1:end_index]
        # 将方块属性字符串转换为字典格式
        for prop in properties_str.split(','):
            key, value = prop.split('=')
            properties_dict[key.strip().replace('"', '')] = value.strip().replace('"', '')
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
            filepath = ""
            if "variants" in data:
                for key, value in data["variants"].items():
                    key_props = key.split(",")
                    flag = True
                    for key_prop in key_props:
                        key_prop = key_prop.split("=")
                        if key_prop[0] in properties_dict and key_prop[1] != properties_dict[key_prop[0]]:
                            flag = False
                            break
                    if flag:
                        if isinstance(value, list):
                            filepath = value[0]["model"]
                        else:
                            filepath = value["model"]
                        if "y" in value:
                            rotation[2] = 360-value["y"]
                        if "x" in value:
                            rotation[0] = value["x"]
                        break
            elif "multipart" in data:
                for part in data["multipart"]:
                    if "when" in part:
                        when = part["when"]
                        flag = True
                        for key, value in when.items():
                            if key in properties_dict:
                                if value != properties_dict[key]:
                                    flag = False
                                    break
                            else:
                                flag = False
                                break
                        if flag:
                            apply = part["apply"]
                            if "model" in apply:
                                filepath = apply["model"]
                            if "y" in value:
                                rotation[2] = 360-value["y"]
                            if "x" in value:
                                rotation[0] = value["x"]
                            break

            if filepath == "":
                print("No matching model found")
        filepath = get_file_path(filepath, 'm')
        dirname, filename = os.path.split(filepath)
        dirname = dirname + '\\'
        textures, elements = get_all_data(dirname, filename)
    except:
        textures = {}
        elements = []
        display = {}
        pass        
    has_air = [has_air[2], has_air[3], has_air[0], has_air[1], has_air[5], has_air[4]]
    #旋转后判断生成面
    if rotation[0] == 0 and rotation[2]==0:
        has_air = [has_air[0], has_air[1], has_air[2], has_air[3], has_air[4], has_air[5]]
    elif rotation[0] == 0 and rotation[2]==270:
        has_air = [has_air[2], has_air[3], has_air[1], has_air[0], has_air[4], has_air[5]]
    elif rotation[0] == 0 and rotation[2]==180:
        has_air = [has_air[1], has_air[0], has_air[3], has_air[2], has_air[4], has_air[5]]
    elif rotation[0] == 0 and rotation[2]==90:
        has_air = [has_air[3], has_air[2], has_air[0], has_air[1], has_air[4], has_air[5]]
    elif rotation[0] == 180 and rotation[2]==0:
        has_air = [has_air[0], has_air[1], has_air[3], has_air[2], has_air[5], has_air[4]]
    elif rotation[0] == 180 and rotation[2]==270:
        has_air = [has_air[0], has_air[1], has_air[2], has_air[3], has_air[5], has_air[4]]
    elif rotation[0] == 180 and rotation[2]==180:
        has_air = [has_air[1], has_air[0], has_air[2], has_air[3], has_air[5], has_air[4]]
    elif rotation[0] == 180 and rotation[2]==90:
        has_air = [has_air[3], has_air[2], has_air[1], has_air[0], has_air[5], has_air[4]]

    return extract_vertices_from_elements(textures, elements, has_air, pos, rotation, vertices, faces, direction, texture_list, uv_list, uv_rotation_list, vertices_dict)
