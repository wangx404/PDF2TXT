#-*- coding: UTF-8 -*-
import time, os
import apiutil
import json
from PIL import Image
from pdf2image import convert_from_path

app_id = 'xxx' # api调用id
app_key = 'xxx' # api秘钥
image_dir = 'images' # 图像缓存文件夹
json_dir = 'jsons' # json缓存文件夹
txt_dir = 'txts' # txt缓存文件夹
pdf_file = 'xxx.pdf' # 当前文件夹中待处理的PDF文件名
'''
由于某些扫描版本的pdf中存在额外添加的水印， 为消除此水印以及页眉页脚带来的噪音干扰，请设定剪裁区域。
剪裁区域的坐标分别为(左上角x轴数值，左上角y轴数值，右下角x轴数值，右下角y轴数值。)
'''
crop_area = (100, 200, 1200, 1900) # 剪裁区域坐标
method = 'space' # 选择文本重组的方法，使用空格'space'或者行间距'interval'进行
platform = 'linux' # 选择操作系统的类别，请填入'linux'或者'windows'


def makeDirs(image_dir, json_dir, txt_dir):
    '''
    创建用于缓存图片、json和txt文本的文件夹。
    :param image_dir: 图像缓存文件夹
    :param json_dir: json文件缓存文件夹
    :param txt_dir: txt文件缓存文件夹
    :return None:
    '''
    current_dir = os.getcwd()
    if not os.path.exists(os.path.join(current_dir, image_dir)):
        os.makedirs(os.path.join(current_dir, image_dir))
    if not os.path.exists(os.path.join(current_dir, json_dir)):
        os.makedirs(os.path.join(current_dir, json_dir))
    if not os.path.exists(os.path.join(current_dir, txt_dir)):
        os.makedirs(os.path.join(current_dir, txt_dir))


def pdf2images(pdf_file, image_dir):
    '''
    将pdf拆分成image，以便后续进行ocr。
    :param pdf_file: 待处理的pdf文件位置，str格式
    :param image_dir: 图像输出文件夹
    :return None:
    '''
    print('There will take pretty long time to finish. Please wait patiently.')
    _images = convert_from_path(pdf_file, dpi=200, output_folder=image_dir)
    del _images
    print('Finally, pdf has been converted to images.')    


def renameImages(image_dir):
    '''
    将image dir中的图像重命名为更简短的名称。
    :param image_dir: 缓存图像文件夹
    :return None:
    '''
    image_list = os.listdir(image_dir)
    image_list.sort()
    index = 0
    for image in image_list:
        os.rename(os.path.join(image_dir, image), 
                  os.path.join(image_dir, '%04d.jpg' % index))
        index += 1
    print('Images have been renamed.')


def cropImages(image_dir, crop_area):
    '''
    使用设定的剪裁区域坐标剪裁图像。
    :param image_dir: 待处理图像文件夹
    :param crop_area: 需要剪裁的区域，(xmin, ymin, xmax, ymax)形式元组或者列表
    :return None:
    '''
    image_list = os.listdir(image_dir)
    image_list.sort()
    for image in image_list:
        image_file = os.path.join(image_dir, image)
        img = Image.open(image_file)
        img = img.crop(crop_area)
        img.save(image_file) # 此操作会覆盖掉原有的图像
    print('Images have been croped.')


def image2json(image_file, json_dir):
    '''
    通过调用Tencent Common OCR API将图片转为json文件。
    :image_file: 待处理图像
    :json_dir: 用于保存json文件的文件夹
    :return None:
    '''
    # 获取对应的json文件名，并跳过已转换的图片
    json_file = os.path.split(image_file)[0]
    json_file = json_file.split('.')[0] + '.json'
    json_file = os.path.join(json_dir, json_file)
    if os.path.exists(json_file):
        return
    ai_obj = apiutil.AiPlat(app_id, app_key)
    rsp = ai_obj.getOcrGeneralocr(image_file)
    with open(json_file, 'w') as f:
        json.dump(rsp, f)
    print('Image %s has been converted to json.' % image_file)

def images2jsons(image_dir, json_dir):
    '''
    将图像文件夹的图像批量转化为json文本。
    :param image_dir: 待处理图像文件夹
    :param json_dir: 用于保存json文件的文件夹
    :return None:
    '''
    image_list = os.listdir(image_dir)
    image_list.sort()
    for image in image_list:
        image_file = os.path.join(image_dir, image) # input image file 
        try:
            image2json(image_file, json_dir)
        except Exception as e:
            print('When converting image %s, some error happened.' % image_file)
            print('And the error is %s' % e)
        time.sleep(1) # 强制sleep，防止调用速度超过限制


def transformFormat(content):
    '''
    将json中的数据转换成更容易解析的嵌套list形式，以便后续文本处理。
    其中x和y为起始坐标，width和height为字符串宽度和高度。
    :param content: 解析后的json字符串
    :return new_content: 嵌套列表，自列表形式为[item_string, x, y, width, height]
                         item_string为字符串，x和y为字符串起始点坐标，widht和height为宽高
    '''
    item_list = content['data']['item_list']
    new_content = []
    for item in item_list:
        item_string = item['itemstring']
        item_x = item["itemcoord"][0]['x']
        item_y = item["itemcoord"][0]['y']
        item_width = item["itemcoord"][0]['width']
        item_height = item["itemcoord"][0]['height']
        new_content.append([item_string, item_x, item_y, item_width, item_height])
    return new_content


def calcAverageCharWidth(new_content):
    '''
    计算字符的平均宽度。
    :param new_content: 格式转换后的嵌套列表
    :return: 字符平均高度
    '''
    total_width = sum([item[3] for item in new_content])
    total_number = sum([len(item[0]) for item in new_content])
    return total_width / total_number


def calcAverageCharHeight(new_content):
    '''
    计算字符的平均高度（加权平均）。
    :param new_content: 格式转换后的嵌套列表
    :return: 字符平均高速
    '''
    total_heights = sum([len(item[0])*item[4] for item in new_content])
    total_number = sum([len(item[0]) for item in new_content])
    return total_heights / total_number


def calcAverageIntervalHeight(new_content):
    '''
    计算行间隔的平均值（使用较小的50%）。
    :param new_content: 格式转换后的嵌套列表
    :return average_interval: 平均行间隔大小
    '''
    intervals = []
    for up_line, down_line in zip(new_content[:-1], new_content[1:]):
        intervals.append(abs(down_line[2] - up_line[2]))
    intervals.sort()
    half_length = len(intervals) // 2
    average_interval = sum(intervals[:half_length]) / half_length
    return average_interval


# 为一种拼接解决方法（通过行长度判断是否为同一行）定义的待用函数
def calcLineLength(new_content):
    '''
    通过一行文字所含有的字符数估算每行的最大字符容量。
    :param new_content: 格式转换后的嵌套列表
    :return line_length: 行字符容量
    '''
    total_length = [len(item[0]) for item in new_content]
    total_length.sort(reverse=True)
    half_length = len(total_length) // 2
    line_length = sum(total_length[:half_length]) // half_length
    return line_length


def calcSpaceNumber(new_content, char_width):
    '''
    计算每行前需要补足的空格的数目。
    :param new_content: 格式转换后的嵌套列表
    :param char_width: 字符的平均像素宽度
    :return space_numbers: 每行需要补齐的空白字符数目
    '''
    start_points = [item[1] for item in new_content] # 起始坐标，即距离图片边缘的距离
    # 使用前50%的空白字符的数目估算页边距的宽度
    start_points_copy = start_points[:] # 非浅层复制
    start_points_copy.sort() # 从小到大
    half_length = len(start_points_copy) // 2 # 使用前50%
    average_space_width = sum(start_points_copy[:half_length]) / half_length # 页边距宽度
    average_char_number = average_space_width / char_width # 页边距折算为字符数目
    # 每行的距离减去页边距的距离得到行前空白的大小，进一步可折算为空白字符的数目
    space_numbers = [item/char_width for item in start_points] # 字符折算
    space_numbers = [item-average_char_number for item in space_numbers] # 减去页边距
    space_numbers = [int(item) if item > 0 else 0 for item in space_numbers] # 取整
    return space_numbers


def addSpace(new_content, space_numbers):
    '''
    为每一行字符串添加n个全角空格字符作为缩进。
    :param new_content: 格式转换后的嵌套列表
    :param space_numbers: 每行需要添加的空格字符数目
    :return new_content: 添加空格后的嵌套列表
    '''
    for index in range(len(space_numbers)):
        new_content[index][0] = '　' * space_numbers[index] + new_content[index][0]
    return new_content


def spliceStringBySpace(content):
    '''
    根据下一个字符串开头是否存在空格，将同一段落内的字符串拼接为一个长字符串。
    对于某些排版格式不符合国标的书籍(段落顶格书写），此方法将失效！！！
    :param content: 添加空格后的嵌套列表
    :return new_content: 拼接后的字符串列表（丢弃附加信息）
    '''
    length = len(content)
    if length == 1: return [content[0][0]]
    
    new_content = []
    temp_line = content[0][0]
    for index in range(1, length):
        if content[index][0].startswith('　'): # 空格开头，需要换行
            new_content.append(temp_line) # 添加，更新
            temp_line = content[index][0]
        else:
            temp_line += content[index][0] # 拼接不更新
    new_content.append(temp_line)
    return new_content


def spliceStringByInterval(content, interval_threshold):
    '''
    根据字符串间距判断是否属于同一段落，将同一段落内的字符串拼接为一个长字符串。
    如果两行之间的间距过大，则视为不同的段落，否则视为同一段落
    :param content:添加空格后的嵌套列表
    :param height_threshold: 段落间距阈值
    :return new_content: 拼接后的字符串列表
    '''
    length = len(content)
    if length == 1: return [content[0][0]]
    new_content = []
    for index in range(length-1):
        if abs(content[index+1][2] - content[index][2]) >= interval_threshold: # 大于阈值
            new_content.append(content[index][0]+'\n') # 添加换行标识符
        else:
            new_content.append(content[index][0])
    new_content.append(content[length-1][0]) # 添加最后一行
    new_content = ''.join(new_content) # 全部拼接
    new_content = new_content.split('\n') # 使用换行标识符分割
    return new_content


def replaceCharsInString(string):
    '''
    将识别结果中的英文标点（部分可能出错的常见标点）全部转换为中文标点。
    :param string: 需要标点替换的字符串
    :return string: 替换标点后的字符串
    '''
    eng_punctuation = [':', '?', '!', '(', ')', ';']
    chn_punctuation = ['：', '？', '！', '（', '）', '；']
    for eng, chn in zip(eng_punctuation, chn_punctuation):
        string = string.relace(eng, chn)
    return string


def replaceCharsInContent(content):
    '''
    调用replaceChars将对字符串列表中的所有字符串进行标点替换。
    :param content: 需要标点替换字符串列表
    :return content:替换标点后的字符串列表
    '''
    for index in range(len(content)):
        content[index] = replaceCharsInString(content[index])
    return content


def json2txt(json_file, txt_dir, method, platform):
    '''
    调用文本处理的相关函数，将json转化为txt。
    :param json_file: 待处理的json文件
    :param txt_dir: txt文本的存储位置
    :param method: 调用的文本处理方法，即选择通过空格或者行间距进行字符串拼接处理
    :param platform: 脚本调用的操作系统（windows/linux/mac），决定写文本时行尾添加\r\n/\n/\r
    :return None:
    '''
    with open(json_file, 'r') as f:
        content = json.load(f)
    content = transformFormat(content) # 加载并转换json文件的格式
    # 计算相关属性参数
    char_width = calcAverageCharWidth(content)
    #char_height = calcAverageCharHeight(content)
    line_interval = calcAverageIntervalHeight(content)
    # 空格补全
    space_numbers = calcSpaceNumber(content, char_width)
    content = addSpace(content, space_numbers)
    # 根据选定的方法进行拼接
    if method == 'space':
        content = spliceStringBySpace(content)
    elif method == 'interval':
        interval_threshold = line_interval * 1.5 # 一点五倍行间距
        content = spliceStringByInterval(content, interval_threshold)
    else:
        print("You should choose the method in ('space, 'interval').")
        return
    # 字符替换
    content = replaceCharsInContent(content)
    # 添加尾部换行符
    if platform == 'windows':
        content = [line+'\r\n' for line in content]
    elif platform == 'linux':
        content = [line+'\n' for line in content]
    elif platform == 'mac':
        content = [line+'\r' for line in content]
    else:
        print("You should choose the platform in ('windows', 'linux', 'mac').")
    # 写入文件
    json_file_prefix = os.path.split(json_file)[1]
    json_file_prefix = json_file_prefix.split('.')[0]
    txt_file = os.path.join(txt_dir, '%s.txt' % json_file_prefix)
    with open(txt_file, 'w') as f:
        f.writelines(content)
    print('Json file %s has been converted to txt file.' % json_file)


def jsons2txts(json_dir, txt_dir, method, platform):
    '''
    调用json2txt函数，将json_dir中的json文件全部转化为txt。
    :param json_dir: json文件夹
    :param txt_dir: txt文本的存储文件夹
    :param method: 调用的文本处理方法，即选择通过空格或者行间距进行字符串拼接处理
    :param platform: 脚本调用的操作系统（windows/linux/mac），决定写文本时行尾添加\r\n/\n/\r
    :return None:
    '''
    json_list = os.listdir(json_dir)
    json_list.sort()
    for json_file in json_list:
        json_file = os.path.join(json_dir, json)
        try:
            json2txt(json_file, txt_dir, method, platform)
        except Exception as e:
            print('When converting json file %s, some error happened.' % json_file)
            print('The error is ', e)
    
    
def readTXT(txt):
    '''
    读取文本文件，返回字符串列表。
    :param txt:
    :return lines: 字符串列表
    '''
    with open(txt, 'r') as f:
        lines = f.readlines()
    lines = [line.strip() for line in lines]
    return lines

       
def concatTXT(txt_dir):
    '''
    将每页已经单独处理过的文本拼合成一个完整的字符串列表。
    :params txt_dir: 文本文件所在的文件夹
    :return contents: 字符串列表
    '''
    contents = []
    txt_list = os.listdir(txt_dir)
    txt_list.sort()
    for txt in txt_list:
        content = readTXT(os.path.join(txt_dir, txt))
        contents.extend(content)
    return contents
    

def concatContentBySpace(txt_dir):
    '''
    通过每一行是否为空格开头将每页已经单独处理过的文本进一步拼合。
    :params txt_dir: 文本文件所在的文件夹
    :return new_contents: 拼接后的完整字符串列表
    '''
    contents = concatTXT(txt_dir)
    length = len(contents)
    if length == 1: return contents
    
    new_contents = []
    temp_line = contents[0]
    for index in range(1, length):
        if contents[index].startswith('　'): # 空格开头，需要换行
            new_contents.append(temp_line) # 添加，更新
            temp_line = contents[index]
        else:
            temp_line += contents[index] # 拼接不更新
    new_contents.append(temp_line)
    return new_contents
        

def concatTwoContent(content1, content2):
    '''
    通过判断第一个文件的尾行的最后一个字符是否为终止字符决定是否和下一个文件的首行合并。
    如果是终止字符，不合并；如果不是终止字符，则合并。
    此函数所使用的终止字符包括句号、问号和感叹号(。？！)。
    :param content1: 前一页的字符串列表
    :param content2: 后一页的字符串列表
    :return content: 拼接后的字符串列表
    '''
    end_chars = ['。', '？', '！']
    # 第一个文档拆分为prior content和最后一行
    if len(content1) == 1:
        prior_content = []
    else:
        prior_content = content1[:-1]
    last_line = content1[-1]
    # 第二个文档拆分为latter_content和首行
    if len(content2) == 1:
        latter_content = []
    else:
        latter_content = content2[1:]
    first_line = content2[0]
    # 比较最后一行的最后一个字符
    if last_line[-1] in end_chars:
        middle_content = [last_line, first_line]
    else:
        middle_content = [last_line + first_line]
    # 组合
    content = [*prior_content, *middle_content, *latter_content]
    return content


def concatContentByPunc(txt_dir):
    '''
    调用concatTwoContent,将文本文件两两拼接得到最终的字符串列表。
    :params txt_dir: 文本文件所在的文件夹
    :return content: 拼接后的完整字符串列表
    '''
    txt_list = os.listdir(txt_dir)
    txt_list.sort()
    txt_list = [os.path.join(txt_dir, txt) for txt in txt_list]
    content = readTXT(txt_list[0])
    for txt in txt_list[1:]:
        temp_content = readTXT(txt)
        content = concatTwoContent(content, temp_content)
    return content
    
    
def saveContent(txt_dir, pdf_file, method, platform):
    '''
    :param txt_dir: 文本文件所在文件夹
    :param pdf_file: PDF文件名，用于计算最终保存的TXT文件名
    :param method: 拼接的方法,即通过空格或者标点符号选择进行拼接判断
    :param platform: 脚本调用的操作系统（windows/linux/mac），决定写文本时行尾添加\r\n/\n/\r
    :return None:
    '''
    if method == 'space':
        contents = concatContentBySpace(txt_dir)
    elif method == 'interval': # 选择通过行间距进行业内拼接后跨页拼接只能选择标点符号
        contents = concatContentByPunc(txt_dir)
    else:
        print("You should chooose the method in ('space', 'interval').")
        return
    # 添加尾部换行符
    if platform == 'windows':
        contents = [line+'\r\n' for line in contents]
    elif platform == 'linux':
        contents = [line+'\n' for line in contents]
    elif platform == 'mac':
        contents = [line+'\r' for line in contents]
    else:
        print("You should choose the platform in ('windows', 'linux', 'mac').")
    # 保存文本
    txt = pdf_file.split('.')[0] + '.txt'
    with open(txt, 'r') as f:
        f.writelines(contents)
    print('Congratulation, the PDF is converted to TXT!')


if __name__ == '__main__':
    # 创建缓存文件夹
    makeDirs(image_dir, json_dir, txt_dir)
    # 将PDF解析成图片形式
    pdf2images(pdf_file, image_dir)
    # 对图片文件重命名
    renameImages(image_dir)
    # 对图片进行剪裁处理
    cropImages(image_dir, crop_area)
    # 调用api对图片进行OCR识别
    images2jsons(image_dir, json_dir)
    # 将json文件转化为txt文件
    jsons2txts(json_dir, txt_dir, method, platform)
    # 将txt拼接为一个txt文件
    saveContent(txt_dir, pdf_file, method, platform)

