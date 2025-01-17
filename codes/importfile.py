import bpy
import os
import time
import pickle
import subprocess


from .block import block
from .functions.get_data import get_all_data
from .classification_files.block_type import exclude
from .schem import schem_chunk,schem_liquid,schem,remove_brackets
from .functions.mesh_to_mc import create_mesh_from_dictionary,create_or_clear_collection
from .register import register_blocks
import json
import amulet
import amulet_nbt
import threading


class ImportBlock(bpy.types.Operator):
    """导入方块"""
    bl_label = "导入方块"
    bl_idname = 'baigave.import_block'

    # 定义一个属性来存储文件路径
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    # 定义一个属性来过滤文件类型，只显示.json文件
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})
    def execute(self, context):
        namespace=os.path.basename(os.path.dirname(os.path.dirname(self.filepath)))+":"
        # 读取JSON文件
        with open(self.filepath, 'r') as file:
            data = json.load(file)
        
        # 提取所需内容
        variants = data.get("variants", {})
        # 提取所需内容
        multipart = data.get("multipart", [])
        
        id_list = []
        if variants != {}:
            for key, value in variants.items():
                if key !="":
                    id_list.append(namespace+os.path.basename(self.filepath).replace(".json","") + "[" + key + "]")
                else:
                    id_list.append(namespace+os.path.basename(self.filepath).replace(".json",""))
        if multipart !=[]:
            # 获取所有when可能的属性
            all_when_keys = set()
            for entry in multipart:
                when_data = entry.get("when", {})
                all_when_keys.update(when_data.keys())

            # 遍历multipart数组
            for i, entry in enumerate(multipart):
                when_data = entry.get("when", {})

                # 补充默认为False的属性
                for key in all_when_keys:
                    if key not in when_data:
                        when_data[key] = "false"

                # 将when数据按字母顺序排序
                sorted_when_data = dict(sorted(when_data.items()))

                # 生成[]内的字符串
                when_string = ','.join([f'{key}={value}' for key, value in sorted_when_data.items()])

                # 构建文件名
                filename = os.path.basename(self.filepath).replace(".json","") + "[" + when_string + "]"

                # 添加到结果列表
                id_list.append(namespace+filename)
        register_blocks(id_list)


            
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ImportNBT(bpy.types.Operator):
    bl_idname = "baigave.import_nbt"
    bl_label = "导入.nbt文件"
    
    # 定义一个属性来存储文件路径
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    # 定义一个属性来过滤文件类型，只显示.nbt文件
    filter_glob: bpy.props.StringProperty(default="*.nbt", options={'HIDDEN'})

    # 定义操作的执行函数
    def execute(self, context):
        # 获取文件路径
        filepath = self.filepath
        filename = os.path.basename(filepath)
        start_time = time.time()
        data = amulet_nbt.load(filepath)
        
        blocks =data["blocks"]
        entities = data["entities"]
        if "palette" in data:
            palette = data["palette"]
        elif "palettes" in data:
            palette = data["palettes"][0]
           

        size = data["size"]
        d = {}  

        for block in blocks:
            pos_tags = block['pos']  
            pos = tuple(tag.value for tag in pos_tags)  
            state = block['state'].value 
            block_name = palette[state]['Name'].value if 'Name' in palette[state] else palette[state]['nbt']['name'].value
            if 'Properties' in palette[state]:
                block_state = palette[state]['Properties'].value
                block_state = ', '.join([f'{k}={v}' for k, v in block_state.items()])
            elif 'nbt' in palette[state] and 'name' in palette[state]['nbt']:
                block_state = palette[state]['nbt']['name'].value
                block_state = ', '.join([f'{k}={v}' for k, v in block_state.items()])
            else:
                block_state = None
            if block_name !="minecraft:air":
                if block_state is not None:
                    d[(pos[0],pos[2],pos[1])] = str(block_name)+"["+block_state+"]"
                else:
                    d[(pos[0],pos[2],pos[1])] = block_name
        end_time = time.time()
        print("代码块执行时间：", end_time - start_time, "秒")

        #普通方法，有面剔除，速度较慢。
        # start_time = time.time()
        # nbt(d,filename)
        # end_time = time.time()
        #print("代码块执行时间：", end_time - start_time, "秒")

        #py+几何节点做法，无面剔除，但速度快。
        start_time = time.time()
        create_mesh_from_dictionary(d,filename.replace(".nbt",""))
        end_time = time.time()
        print("代码块执行时间：", end_time - start_time, "秒")
        return {'FINISHED'}
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# 定义一个导入.schem文件的操作类
class ImportSchem(bpy.types.Operator):
    bl_idname = "baigave.import_schem"
    bl_label = "导入.schem文件"
    
    # 定义一个属性来存储文件路径
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    # 定义一个属性来过滤文件类型，只显示.schem文件
    filter_glob: bpy.props.StringProperty(default="*.schem", options={'HIDDEN'})

    # 定义操作的执行函数
    def execute(self, context):
        name=os.path.basename(self.filepath)
        #清空缓存文件夹
        start_time = time.time()
        folder_path = bpy.utils.script_path_user() + "/addons/BaiGave_Plugin/schemcache"
        file_names = os.listdir(folder_path)
        for file_name in file_names:
            file_path = os.path.join(folder_path, file_name)
            os.remove(file_path)
        level = amulet.load_level(self.filepath)
        all_chunks=sorted(level.all_chunk_coords("main"))
        chunks = [list(point) for point in level.bounds("main").bounds]
        nbt_data = amulet_nbt._load_nbt.load(self.filepath)
        
        #data=nbt_data["BlockEntities"][0]["data"]["data"]
        # 解析数据为坐标点
        # coordinates = []
        # for i in range(0, len(data), 3):
        #     x = data[i]
        #     y = data[i + 1]
        #     z = data[i + 2]
        #     coordinates.append((x, y, z))

        # # 构建字典
        # coordinates_dict = {f"Point {index + 1}": point for index, point in enumerate(coordinates)}

        # 打印字典
        #print(data)
        #print(len(data))
        size = {
            "x":int(nbt_data["Width"]),
            "y":int(nbt_data["Height"]),
            "z":int(nbt_data["Length"])
        }
        
        # 设置图片的大小和颜色
        image_width = int(size["z"])
        image_height = int(size["x"])
        default_color = (0.47, 0.75, 0.35, 1.0)  # RGBA颜色，对应#79c05a

        # 创建一个新的图片
        filename = os.path.basename(self.filepath)
        image = bpy.data.images.new("colormap", width=image_width, height=image_height)
        image.use_fake_user = True

        def set_default_color(image, image_width, image_height, default_color):
            # 设置默认颜色
            for y in range(image_height):
                for x in range(image_width):
                    pixel_index = (y * image_width + x) * 4  # RGBA每个通道都是4个值
                    image.pixels[pixel_index : pixel_index + 4] = default_color
        # 创建一个新的线程来执行 set_default_color 函数
        thread = threading.Thread(target=set_default_color, args=(image, image_width, image_height, default_color))
        # 启动新的线程
        thread.start()

        #小模型，直接导入
        if (chunks[1][0]-chunks[0][0])*(chunks[1][1]-chunks[0][1])*(chunks[1][2]-chunks[0][2]) < bpy.context.preferences.addons['BaiGave_Plugin'].preferences.sna_minsize:
            #几何节点+py方法
            schem(level,chunks,False,name)
            schem_liquid(level,chunks)
            materials = bpy.data.materials
            for material in materials:
                try:
                    node_tree = material.node_tree
                    nodes = node_tree.nodes
                    for node in nodes:
                        if node.type == 'TEX_IMAGE':
                            if node.name == '色图':
                                node.image = bpy.data.images.get("colormap")
                except Exception as e:
                    print("材质出错了:", e)

        #大模型，分块导入
        else:
            processnum = bpy.context.preferences.addons['BaiGave_Plugin'].preferences.sna_processnumber
            x_cut = (chunks[1][0]-chunks[0][0]+1)//processnum
            x_list = [[chunks[0][0]+i*x_cut+1, chunks[0][0]+(i+1)*x_cut+1] for i in range(processnum)]
            x_list[0][0] = chunks[0][0]
            x_list[-1][1] = chunks[1][0]
            VarCachePath = bpy.utils.script_path_user() + "/addons/BaiGave_Plugin/schemcache/var.pkl"
            with open(VarCachePath, 'wb') as file:
                pickle.dump((self.filepath,chunks,name,x_list,processnum),file)

            blender_path = bpy.app.binary_path
            ImportPath = bpy.utils.script_path_user()
            MultiprocessPath = ImportPath + "/addons/BaiGave_Plugin/multiprocess/schem_mp.py"
            MPliquidPath = ImportPath + "/addons/BaiGave_Plugin/multiprocess/schem_liquid_mp.py"
            #多进程实现方法：后台启动headless blender(-b)，只运行python代码(-P)，不显示界面
            for num in range(processnum):
                ChunkIndex = f"import bpy;bpy.context.scene.frame_current = {num}"
                subprocess.Popen([blender_path,"-b","--python-expr",ChunkIndex,"-P",MultiprocessPath])
        end_time = time.time()
        print("预处理时间：", end_time - start_time, "秒")
        try:
            schem_liquid(level,chunks)
        except Exception as e:
            print("流体出错了:", e)

        CacheFolder = bpy.utils.script_path_user() + "/addons/BaiGave_Plugin/schemcache/"
        # 检查所有的文件是否都存在
        while not all(os.path.exists(os.path.join(CacheFolder, f'chunk{i}.pkl')) for i in range(processnum)):
            time.sleep(0.5)
        merged_dict = {}
        merged_vertices = []
        merged_ids = []
        counter = 0
        # 获取所有的缓存文件
        for i in range(processnum):
            # 加载每个文件中的字典
            with open(os.path.join(CacheFolder, f'chunk{i}.pkl'), 'rb') as f:
                vertices,ids,id_map = pickle.load(f)
            # 将字典合并到大字典中
            for key, value in id_map.items():
                if key not in merged_dict:
                    merged_dict[key] = counter
                    counter += 1
            # 将列表合并到大列表中
            merged_vertices.extend(vertices)
            merged_ids.extend(ids)

        IDCachePath = bpy.utils.script_path_user() + "/addons/BaiGave_Plugin/schemcache/id_map.pkl"
        with open(IDCachePath, 'wb') as f:
            pickle.dump((merged_vertices,merged_ids,merged_dict), f)

        bpy.ops.baigave.multiprocess_import()

        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

#多进程结束后导入模型
class MultiprocessImport(bpy.types.Operator):
    bl_idname = "baigave.multiprocess_import"
    bl_label = "导入.schem文件"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.schem", options={'HIDDEN'})

    def execute(self, context):
        VarCachePath = bpy.utils.script_path_user() + "/addons/BaiGave_Plugin/schemcache/var.pkl"
        with open(VarCachePath, 'rb') as file:
            schempath,chunks,name,x_list,processnum = pickle.load(file)
        level = amulet.load_level(schempath)
        schem(level,chunks,True,name)

        materials = bpy.data.materials
        for material in materials:
            try:
                node_tree = material.node_tree
                nodes = node_tree.nodes
                for node in nodes:
                    if node.type == 'TEX_IMAGE':
                        if node.name == '色图':
                            node.image = bpy.data.images.get("colormap")
            except Exception as e:
                print("材质出错了:", e)

        return {'FINISHED'}
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

#每个进程分别处理一个区块
class MultiprocessSchem(bpy.types.Operator):
    bl_idname = "baigave.import_schem_mp"
    bl_label = "导入.schem文件"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.schem", options={'HIDDEN'})

    def execute(self, context):
        VarCachePath = bpy.utils.script_path_user() + "/addons/BaiGave_Plugin/schemcache/var.pkl"
        with open(VarCachePath, 'rb') as file:
            schempath,chunks,name,x_list,processnum = pickle.load(file)
        level = amulet.load_level(schempath)
        schem_chunk(level,chunks,x_list,name)

        return {'FINISHED'}
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    

class ImportSchemLiquid(bpy.types.Operator):
    bl_idname = "baigave.import_schem_liquid"
    bl_label = "导入.schem文件"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.schem", options={'HIDDEN'})

    def execute(self, context):
        VarCachePath = bpy.utils.script_path_user() + "/addons/BaiGave_Plugin/schemcache/var.pkl"
        with open(VarCachePath, 'rb') as file:
            chunks,mp_chunks,schempath,interval,processnum = pickle.load(file)
        level = amulet.load_level(schempath)
        schem_liquid(level,chunks)
        ModelCachePath = bpy.utils.script_path_user() + "/addons/BaiGave_Plugin/schemcache/liquid.blend"
        bpy.ops.wm.save_as_mainfile(filepath=ModelCachePath)
        return {'FINISHED'}
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class Importjson(bpy.types.Operator):
    """导入选定的json文件"""
    bl_idname = "baigave.import_json"
    bl_label = "导入json文件"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        # 检查文件路径是否有效
        if os.path.isfile(self.filepath) and self.filepath.endswith(".json"):
            # 获取文件名
            filename = os.path.basename(self.filepath)
            textures, elements,parent = get_all_data(os.path.dirname(self.filepath)+"\\", filename)
            position = [0, 0, 0]
            has_air = [True, True, True, True, True, True]
            block(textures, elements, position,[0,0,0], filename, has_air)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "请选择有效的.json文件")
            return {'CANCELLED'}

    def invoke(self, context, event):
        # 打开文件选择对话框
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class SNA_AddonPreferences_F35F8(bpy.types.AddonPreferences):
    bl_idname = 'BaiGave_Plugin'
    sna_processnumber: bpy.props.IntProperty(name='ProcessNumber', description='最大进程数，同时处理这么多个区块', default=6, subtype='NONE', min=1, max=64)
    sna_intervaltime: bpy.props.FloatProperty(name='IntervalTime', description='处理完每个区块，间隔一段时间再导入进来。较小值减少总时间；较大值能避免blender卡住，边导边用', default=1.0, subtype='NONE', unit='NONE', min=0.0, max=10.0, step=3, precision=1)
    sna_minsize: bpy.props.IntProperty(name='MinSize', description='超过这个数就会启用多进程分区块导入', default=1000000, subtype='NONE', min=1000, max=99999999)

    def draw(self, context):
        if not (False):
            layout = self.layout 


class SNA_OT_My_Generic_Operator_A38B8(bpy.types.Operator):
    bl_idname = "sna.my_generic_operator_a38b8"
    bl_label = "刷新"
    bl_description = "自动设置以下参数"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        Variable = None
        Variable=int(os.cpu_count()/2)
        bpy.context.preferences.addons['BaiGave_Plugin'].preferences.sna_processnumber = Variable
        bpy.context.preferences.addons['BaiGave_Plugin'].preferences.sna_intervaltime = 1
        bpy.context.preferences.addons['BaiGave_Plugin'].preferences.sna_minsize = 1000000
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


    
# class SelectArea(bpy.types.Operator):
#     """选择区域（性能有问题）"""
#     bl_label = "选择区域"
#     bl_idname = 'baigave.select'
    
#     def execute(self, context):
#         # 获取当前场景的名称
#         current_scene = bpy.context.scene.name
#         # 如果场景名称不为"地图"，则返回
#         if current_scene != "地图":
#             button_callback(self, context,"地图仍未创建！")
#             return {'CANCELLED'}
#         # 检查当前场景是否已经有名为"Map"的集合
#         existing_collections = bpy.data.collections.values()
#         for coll in existing_collections:
#             if coll.name == "Map":
#                 button_callback(self, context,"已经存在选择框！(如果你删除了一些东西请连同集合一起删除）")
#                 return {'CANCELLED'}
#         # 获取当前文件的路径
#         current_path = os.path.dirname(os.path.abspath(__file__))
#         # 拼接路径和文件名
#         filepath = os.path.join(current_path, "blend_files","Map.blend")
#         # 从文件中加载名为"Map"的集合
#         with bpy.data.libraries.load(filepath) as (data_from, data_to):
#             data_to.collections = ["Map"]
#         # 将集合链接到当前场景
#         for coll in data_to.collections:
#             if coll is not None:
#                 bpy.context.scene.collection.children.link(coll)
#         return {'FINISHED'}

class ImportWorld(bpy.types.Operator):
    """导入世界(性能有问题)"""
    bl_label = "导入世界"
    bl_idname = 'baigave.import_world'

    current_chunk_index = 0  # 当前处理的区块索引

    # 定义一个属性来存储文件路径
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")


    def execute(self, context):
        filename="world"
        level = amulet.load_level(self.filepath)
        min_coords=context.scene.min_coordinates
        max_coords=context.scene.max_coordinates
        # 创建一个新的网格对象
        mesh = bpy.data.meshes.new(name=filename)
        mesh.attributes.new(name='blockid', type="INT", domain="POINT")
        mesh.attributes.new(name='biome', type="FLOAT_COLOR", domain="POINT")
        obj = bpy.data.objects.new(filename, mesh)

        # 将对象添加到场景中
        scene = bpy.context.scene
        scene.collection.objects.link(obj)
        # 创建一个新的集合
        collection_name="Blocks"
        create_or_clear_collection(collection_name)
        collection =bpy.data.collections.get(collection_name)
        nodetree_target = "SchemToBlocks"

        #导入几何节点
        try:
            nodes_modifier.node_group = bpy.data.node_groups[collection_name]
        except:
            file_path =bpy.context.scene.geometrynodes_blend_path
            inner_path = 'NodeTree'
            object_name = nodetree_target
            bpy.ops.wm.append(
                filepath=os.path.join(file_path, inner_path, object_name),
                directory=os.path.join(file_path, inner_path),
                filename=object_name
            )
        # 创建顶点和顶点索引
        vertices = []
        ids = []  # 存储顶点id

        # 遍历范围内所有的坐标
        for x in range(min_coords[0], max_coords[0] + 1):
            for y in range(min_coords[1], max_coords[1] + 1):
                for z in range(min_coords[2], max_coords[2] + 1):
                    # 获取坐标处的方块       
                    blc =level.get_version_block(x, y, z, "minecraft:overworld",("java", (1, 20, 4)))
                    id =blc[0]
                    if isinstance(id,amulet.api.block.Block):
                        id = str(id).replace('"', '')
                        result = remove_brackets(id) 
                        if result not in exclude:  
                            # 将字符串id映射到数字，如果id已经有对应的数字id，则使用现有的数字id
                            vertices.append((x-min_coords[0],-(z-min_coords[2]),y-min_coords[1]))
                            # 将字符串id转换为相应的数字id
                            ids.append(id)

        id_map=register_blocks(list(set(ids)))
        # 将顶点和顶点索引添加到网格中
        mesh.from_pydata(vertices, [], [])
        for i, item in enumerate(obj.data.attributes['blockid'].data):
            item.value=id_map[ids[i]]
        #群系上色
        for i, item in enumerate(obj.data.attributes['biome'].data):
            item.color[:]=(0.149,0.660,0.10,0.00)
        # 设置顶点索引
        mesh.update()
        
        # 检查是否有节点修改器，如果没有则添加一个
        has_nodes_modifier = False
        for modifier in obj.modifiers:
            if modifier.type == 'NODES':
                has_nodes_modifier = True
                break
        if not has_nodes_modifier:
            obj.modifiers.new(name="SchemToBlocks",type="NODES")
        nodes_modifier=obj.modifiers[0]
        
        # 复制 SchemToBlocks 节点组并重命名为 CollectionName
        try:
            original_node_group = bpy.data.node_groups['SchemToBlocks']
            new_node_group = original_node_group.copy()
            new_node_group.name = collection_name
        except KeyError:
            print("error")
        #设置几何节点        
        nodes_modifier.node_group = bpy.data.node_groups[collection_name]
        bpy.data.node_groups[collection_name].nodes["集合信息"].inputs[0].default_value = collection
        nodes_modifier.show_viewport = True    
        level.close()
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


classes=[ImportBlock,ImportSchem,MultiprocessSchem,Importjson,ImportWorld,#SelectArea,
         ImportNBT,SNA_AddonPreferences_F35F8,SNA_OT_My_Generic_Operator_A38B8,ImportSchemLiquid,MultiprocessImport]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
        
    