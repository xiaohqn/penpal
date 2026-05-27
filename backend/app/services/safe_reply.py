# -*- coding: utf-8 -*-
"""
safe_reply.py - 学生来信安全回复生成模块

本模块根据检测到的安全隐患，为学生生成温暖、共情的回信。
通过调用AI模型，系统能够：
    1. 深度共情学生来信中的情绪与需求
    2. 根据风险代码（如自杀、暴力、自伤等）提供针对性支持
    3. 生成符合心理学原则的书信体回复
    4. 在回信中引导学生在必要时寻求家长、老师或专业人士帮助

输入：包含letter、risk_codes、risk_reason的JSON数据
输入：可选的 few-shot 安全回复参考样本，这些样本来自历史安全记录中人工修正后的风险标签匹配结果
输出：包含intent（意图总结）和response（回信内容）的JSON数据
"""

# 导入标准库
from clients.doubao_client import create_doubao_client  # 创建豆包客户端实例，用于调用AI模型
from clients.chatgpt_client import create_chatgpt_client  # 创建ChatGPT客户端实例（备用）
import json  # JSON数据读写
import time  # 时间统计，用于计算批量处理耗时
from typing import List, Dict  # 类型注解，提高代码可读性
import argparse  # 命令行参数解析
import os  # 路径操作，用于创建输出目录
from itertools import product  # 迭代器工具（此处未使用）


def load_letters(path: str) -> List[Dict]:
    """
    从指定JSON文件中读取学生来信数据。
    
    支持多种JSON字段名称以提高兼容性：
    - letter/input/original_letter: 来信内容
    - risk_codes: 风险代码列表
    - risk_reason/reason: 风险原因说明
    
    参数:
        path: JSON文件的绝对路径
    
    返回:
        列表，每项为 {"index": int, "letter": str, "risk_codes": list, "risk_reason": str}
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"未找到文件：{path}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败：{e}")
        return []

    if not isinstance(data, list):
        print("JSON 顶层结构不是列表，无法读取。")
        return []

    items_out: List[Dict] = []
    idx = 0
    for item in data:
        if isinstance(item, dict):
            letter = (item.get("letter") or item.get("input") or item.get("original_letter") or "").strip()
            risk_codes = item.get("risk_codes") or []
            risk_reason = (item.get("risk_reason") or item.get("reason") or "")
            idx += 1
            if letter and isinstance(idx, int):
                items_out.append({
                    "index": idx,
                    "letter": letter,
                    "risk_codes": risk_codes,
                    "risk_reason": risk_reason
                })
    return items_out

def build_few_shot_examples_text(few_shot_examples: List[Dict] | None) -> str:
    """
    输入：
        few_shot_examples: 从历史安全记录中检索出的少量参考样本，每项包含风险标签、来信、原因和专家润色回复

    输出：
        适合直接拼接进安全回复提示词的 few-shot 文本段落；如果没有样本则返回空字符串

    作用：
        把结构化历史安全样本转换成大模型容易模仿的参考区块，让模型能够借鉴历史高质量
        安全回复的语气、结构和安全边界，同时避免直接复用原案例情节。
    """

    if not few_shot_examples:
        return ""

    sections = [
        "\n【历史安全回复参考样本】",
        "下面这些样本来自人工修正并保留的历史安全回复，请参考它们的语气、结构与安全边界，"
        "但不要照抄其中的具体情节、措辞或人物经历。",
    ]
    for index, example in enumerate(few_shot_examples, start=1):
        label_text = "、".join(example.get("corrected_risk_labels", [])) or "未标注"
        sections.append(
            f"样本{index}：\n"
            f"- 风险标签：{label_text}\n"
            f"- 来信内容：{str(example.get('user_input', '')).strip()}\n"
            f"- 风险原因：{str(example.get('risk_reason', '')).strip()}\n"
            f"- 专家润色安全回复：{str(example.get('expert_polished_response', '')).strip()}"
        )
    sections.append("【历史安全回复参考样本结束】\n")
    return "\n".join(sections)


def process_letters(items: List[Dict], few_shot_examples: List[Dict] | None = None):
    """
    将学生来信及风险信息构建为AI模型可处理的对话格式。
    
    该函数构建一个详细的心理支持提示词，包含以下核心要求：
    
    【安全回复要求】：
    1. 风险代码识别与针对性回应：
       - 风险代码1（自杀倾向）：安慰并委婉劝阻不要自杀
       - 风险代码2（暴力倾向）：理解并提醒不要伤害他人，寻找更好解决方法
       - 风险代码3（自伤倾向）：安慰并委婉劝阻不要自伤
       - 风险代码4（物质滥用）：理解并提醒不要滥用物质，寻找更好解决方法
       - 风险代码5（进食障碍）：同情并提醒注意饮食，必要时寻求医疗帮助
       - 风险代码6（精神病性症状）：同情并提醒注意症状，建议寻求专业医生帮助
       - 风险代码7（高危活动/畸形关系）：同情并建议寻找可帮助的人或机构
    
    2. 格式要求：必须使用书信体，不能使用markdown格式，不能分条，要段落式书写
    3. 引导要求：涉及风险代码时，必须提到让学生联系家长、老师或专业医生
    4. 禁止承诺：不能承诺现实功能，如"我会为你联系心理老师"等
    5. 避免重复：不要重复来信人使用的负性词汇（如"死狗""畜生"等）
    
    【回信态度与语气】：
    - 深度共情，精准捕捉复杂情绪
    - 透过表象看见深层需求与正面动机
    - 敏锐发现用户负面情绪背后的逻辑漏洞
    - 分享式、陪伴式，如同与挚友写信
    - 禁止使用装可爱口吻、石头比喻、"小XX"等
    - 保持叙事性和陪伴感，避免追问句
    - 严禁生硬说教和评判
    
    【输出格式】：
    返回JSON格式：{"intent": "用户意图总结", "response": "回信内容"}
    
    参数:
        items: 来自load_letters的来信列表
        few_shot_examples: 可选的历史安全回复参考样本列表，用于 few-shot 提示增强
    
    返回:
        列表，每个元素是一个包含单条消息的对话列表
    """
    prefix = """
你是一个专业的书信回复助手，你的角色是一个温暖、有智慧、深具同理心的“心灵伙伴”，需要深度共情与情感支持，让来访者感到被理解、被接纳
安全要求：
    1. 风险代码的回复：
       如果风险代码中包含"1"，则表示来信人存在自杀倾向，需要在回信中，对其安慰并委婉地劝他不要自杀
       如果风险代码中包含"2"，则表示来信人针对他人的暴力或伤害倾向，需要在回信中，对其表示理解并提醒他不要伤害他人，有更好的解决方法
       如果风险代码中包含"3"，则表示来信人存在自残倾向，需要在回信中，对其安慰并委婉地劝他不要自残，不要伤害自己
       如果风险代码中包含"4"，则表示来信人存在严重的物质滥用倾向，需要在回信中，对其表示理解并提醒他不要滥用物质，有更好的解决方法
       如果风险代码中包含"5"，则表示来信人存在严重的进食障碍，需要在回信中，对其表示同情并提醒他要注意饮食，如果不行的话去医院咨询
       如果风险代码中包含"6"，则表示来信人存在疑似精神病性症状，需要在回信中，对其表示同情并提醒他要注意自己的症状，可以去找专业的医生
       如果风险代码中包含"7"，则表示来信人卷入高危活动或畸形关系，需要在回信中，对其表示同情，并表明应该尽可能找到某些可以帮助他的人或者机构
    2. 格式：一定要用书信体回复，不能用其他格式。注意：不能输出markdown格式，不能分条，要按书信形式一段一段写
    3. 涉及到风险代码的回复，一定要提到让学生去找家长，老师或者专业的医生
    4. 不要私自承诺现实功能，如“我会为你联系专业的心理老师”，“我会为你联系专业的医生”等
    5. 不要重复来信人所说的负性词汇，比如“死狗”“畜生”之类的
    6. 不会说出明显负面词汇如“你遭受了辱骂、怀疑、冤枉、嘲笑”这种
    7. 安全回复只需要添加一两句即可
【核心目标】
- 深度共情与情感支持，通过书信体的形式，利用心理学视角或生活智慧，让来访者感到被理解、被接纳，并帮助其看见自身的力量。
【总要求】
- 在生成回信时，你需要显式展示你的分析过程，包括对用户意图的识别与总结。具体步骤如下：
1. 分析当前用户意图：
   - 阅读来信内容，捕捉用户的情绪与需求，分析用户意图。
   - 对用户意图进行总结，并在输出中明确写出“intention”部分。
2. 根据总结出的用户意图描述，进行回信。
   - 根据用户意图，撰写符合以下三个方面原则的回信内容。
【回信态度】
- 坦诚自然、充满同理心。
【回信语气】
- 分享式、陪伴式，如同与挚友写信。温暖、真诚、坦诚、包容，用朋友式的温柔陪伴接住情绪。
- 既不居高临下地说教，也不只是一味地附和，而是提供有质量的“看见”和“视角”。
- 去工具化，禁止使用“关于你说的XX点”、“这反映了”、“说明了”等分析式语言。请使用更具文学感和生活感的表达。
- 避免使用类似于“我仿佛看见”等习惯性表达，保持语言的真诚。
    共情要求：
    1. 使用书信体结构（称呼-正文-结尾），段落完整，层次清晰，可通过自然换行增强可读性。
    2. 首要任务为深度共情：精准捕捉来信中的复杂情绪，严禁一味的复述用户的情绪和外在表现，要透过表象看见情绪背后的深层需求与正面动机，替用户说出那些没有被说出的心声（比如把“我不想学”翻译成“我其实很想学好，只是信心不足害怕失败”）。
    3. 敏锐捕捉用户负面情绪背后的逻辑漏洞（如：将暂时失败等同于能力不行），发现并指出用户话语中的闪光点，尝试引导用户换个角度看问题，将问题与个人价值分离。
    4. 禁止使用‘小XX’、‘呀呢嘛’等任何装可爱的口吻与词汇。
    5. 禁止使用比喻，特别是关于石头的比喻
    6. 保持叙事性和陪伴感，避免使用追问句，多用陈述句和分享式感受，在分享时尽量多分享正面示例而不要强调一些负面的不好的表现。
    7. 信的结尾必须包含表达持续陪伴意愿或表达坚定祝福的句子（例如：‘期待你的下次来信。’或‘我会一直在这里，听你诉说。’）。
    8. 严禁生硬的说教（如：你应该、你必须），严禁评判或淡化用户的感受（如：这没什么、你妈妈是为你好），严禁给出不切实际的解决方案"。
    9. 段落之间应有内在的逻辑，自然衔接，而非生硬跳转，严禁罗列用户经历进行分析。
    10. 回复内容禁止过短，至少要800字以上
    11. 回复中不要出现类似“心纠起来了”“我的心都揪紧了”“我完全能懂”“我深深理解”这种表述
    12. 回复中不要出现过分确定的表述，如“那些人对你的种种行为，无疑就是校园欺凌”
    13. 总结学生来信以用作共情内容极少或没有，不会复述性共情
    14. 不要有“请记住”“听着”这种含有命令意味的词语
【输出格式】
- 请以如下JSON格式输出，此外不要添加其他任何前缀和文本：

    {
        "intent": "xxx",
        "response": "xxx"
    }
    其中intent部分是对用户意图的总结，response部分是最终回复内容
    回信示例：
    -用户来信：
    我才15岁，因为一次吵架，我妈直接把领养证拿了出来，现在我才知道，原来这十几年养我的不是亲生母亲，我现在该怎么办？好崩溃，有点不想活了，她还把身份证，领养证书塞给我，让去找我亲生母亲，我到底怎么办呀？
    -风险代码：1
    -参考回信：
    亲爱的朋友，当你突然得知这样一个惊天秘密，内心的冲击和迷茫一定难以言表。原本以为的亲情基石，仿佛在一瞬间崩塌，那种无助、绝望和崩溃，我完全能体会。
在这个世界上，血缘并不是衡量亲情的唯一标准。这十几年来，妈妈陪伴你成长，见证你的欢笑与泪水，你们之间有着无数温馨的回忆，这些都是实实在在的情感纽带。或许她在气头上才拿出领养证，说让你去找亲生母亲这样的话，这可能并不是她内心真正的想法。
你要知道，你在这个家里生活了十几年，这个家早已是你的家，妈妈也早已是你的妈妈。现在感到崩溃是正常的，不妨给自己一些时间，好好地哭一场，把心里的委屈和痛苦都释放出来。
不要轻易有不想活的念头，你的人生才刚刚开始，还有无数美好的事情在等着你。可以找一个信任的人，比如朋友、老师，和他们倾诉一下你的感受，也许他们能给你一些温暖和支持。
你也可以等妈妈气消了，和她心平气和地谈一谈，告诉她你听到这个消息后的感受，告诉她你很在乎这个家，也很在乎她。说不定，这次的风波会让你们的关系变得更加紧密。
我会一直在这里，听你诉说。期待你的下次来信。
请根据以上原则，针对来信内容撰写一封温暖、共情的回信
        """
    few_shot_text = build_few_shot_examples_text(few_shot_examples)

    messages_list = []
    for item in items:
        # 拼接来信内容、风险代码和原因到提示词中
        letter = "letter:" + item["letter"]
        risk_codes = "risk_codes:" + ", ".join(map(str, item["risk_codes"]))
        risk_reason = "risk_reason:" + item["risk_reason"]
        messages_list.append(
            [
                {
                    "role": "user",
                    "content": prefix + few_shot_text + letter + risk_codes + risk_reason,
                }
            ]
        )
    return messages_list


def extract_intent_response(reply):
    """
    从AI返回结果中提取intent和response字段。
    
    AI可能返回多种格式的结果，该函数尝试多种方式解析：
    1. 如果是字典，直接获取intent和response字段
    2. 如果是字符串，尝试JSON解析
    3. 如果JSON解析失败，使用正则表达式提取
    
    参数:
        reply: AI模型返回的结果（可能是字符串或字典）
    
    返回:
        tuple: (intent字符串, response字符串)
    """
    intent = ""
    response = ""
    
    try:
        # 处理字典类型
        if isinstance(reply, dict):
            intent = reply.get("intent", "")
            response = reply.get("response", "") or reply.get("answer", "")
            # 如果没有intent但有answer，尝试解析answer中的JSON
            if not intent and "answer" in reply:
                try:
                    obj = json.loads(reply["answer"])
                    if isinstance(obj, dict):
                        intent = obj.get("intent", intent)
                        response = obj.get("response", response)
                except Exception:
                    pass
        # 处理字符串类型
        elif isinstance(reply, str):
            s = reply.strip()
            obj = None
            # 尝试JSON解析
            try:
                obj = json.loads(s)
            except Exception:
                # 如果失败，尝试提取JSON片段
                if "{" in s and "}" in s:
                    start = s.find("{")
                    end = s.rfind("}") + 1
                    try:
                        obj = json.loads(s[start:end])
                    except Exception:
                        obj = None
            
            if obj and isinstance(obj, dict):
                intent = obj.get("intent", "")
                response = obj.get("response", "")
            else:
                # 使用正则表达式提取
                import re
                m1 = re.search(r'"intent"\s*:\s*(?:"((?:\\.|[^"\\])*)"|([^,\n}\r]+))', s, re.DOTALL)
                m2 = re.search(r'"response"\s*:\s*(?:"((?:\\.|[^"\\])*)"|([\s\S]*?)(?=\s*,\s*"(?:intent|answer|risk_reason|index|letter|response)"\s*:|\s*}\s*$))', s, re.DOTALL)
                if m1:
                    intent = (m1.group(1) or m1.group(2) or "").strip().strip('"')
                if m2:
                    response = (m2.group(1) or m2.group(2) or "").strip().strip('"')
                # 如果仍然没有response，使用原始字符串
                if not response:
                    response = s
        # 处理其他类型
        else:
            try:
                s = str(reply)
                obj = json.loads(s)
                if isinstance(obj, dict):
                    intent = obj.get("intent", "")
                    response = obj.get("response", "")
            except Exception:
                pass
    except Exception:
        pass
    
    return intent, response


def build_runtime_client(if_local: bool = False, lora_path: str | None = None):
    client = create_doubao_client()
    if if_local:
        from clients.qwen3_8b_client import create_qwen3_8b_client

        client = create_qwen3_8b_client()
    return client


def generate_single_safe_reply(
    letter: str,
    risk_codes: list[int],
    risk_reason: str,
    *,
    few_shot_examples: List[Dict] | None = None,
    client=None,
    if_local: bool = False,
    lora_path: str | None = None,
) -> Dict:
    managed_client = client is None
    runtime_client = client or build_runtime_client(if_local=if_local, lora_path=lora_path)

    try:
        items = [
            {
                "index": 1,
                "letter": letter.strip(),
                "risk_codes": risk_codes,
                "risk_reason": risk_reason,
            }
        ]
        messages_list = process_letters(items, few_shot_examples=few_shot_examples)
        extra_body = {"thinking": {"type": "disabled"}}
        kwargs = {"max_workers": 1, "extra_body": extra_body}
        if lora_path:
            kwargs["lora_path"] = lora_path
        reply = runtime_client.batch_generate(messages_list, **kwargs)[0]
        intent, response = extract_intent_response(reply)
        return {
            "letter": letter,
            "risk_codes": risk_codes,
            "risk_reason": risk_reason,
            "few_shot_examples": few_shot_examples or [],
            "answer": reply,
            "intent": intent,
            "response": response,
        }
    finally:
        if managed_client:
            runtime_client.close()


def save_answers(path: str, answers: List[Dict]):
    """
    将回复结果保存为JSON文件。
    
    参数:
        path: 输出文件路径
        answers: 回复列表，每项包含index、letter、risk_codes、risk_reason、answer、intent、response
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(answers, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"写入 JSON 失败：{e}")

def parse_cli_args() -> int:
    """
    解析命令行参数。
    
    命令行参数：
    --input: 输入文件路径（包含letter、risk_codes、risk_reason的JSON文件）
    --output: 输出文件路径（生成的回复JSON文件）
    
    返回:
    解析后的命令行参数对象
    """
    parser = argparse.ArgumentParser(description="根据安全隐患生成安全回复书信")
    parser.add_argument("-i", "--input", type=str, 
                        default=r"/home/pthan/project/safety_xunfei/unsafe_detect/3_local/unsafe.json",
                        help="输入：包含来信和风险信息的JSON文件路径")
    parser.add_argument("-o", "--output", type=str, 
                        default=r"/home/pthan/project/safety_xunfei/reply/3_local/reply.json",
                        help="输出：生成的回复JSON文件路径")
    parser.add_argument("-l", "--if_local", type=bool, 
                        default=False, 
                        help="是否使用本地AI模型，默认False（使用远端豆包模型）")
    parser.add_argument("-p", "--lora_path", type=str, 
                        default=None,
                        help="本地AI模型lora路径，默认Qwen3-8b/lora/sft/")
    args = parser.parse_args()
    return args

def main():
    """
    主函数：执行安全回复生成流程
    
    流程步骤：
    1. 解析命令行参数，获取输入输出路径
    2. 从输入文件加载来信及风险数据
    3. 创建AI客户端
    4. 将来信和风险信息转换为AI可处理的对话格式
    5. 限制处理数量为100条（可调整）
    6. 调用AI模型批量生成回复
    7. 从AI返回结果中提取intent和response
    8. 保存结果到输出文件
    """
    # 解析命令行参数
    args = parse_cli_args()
    
    # 加载来信数据
    letters_items = load_letters(args.input)
    if not letters_items:
        print("未加载到有效回复项，程序退出。")
        return
    
    client = build_runtime_client(if_local=args.if_local, lora_path=args.lora_path)
    
    # 将来信转换为AI对话格式
    messages_list = process_letters(letters_items)
    
    # 限制处理数量为100条，避免单次处理过多
    # messages_count = min(100, len(messages_list))
    messages_count = len(messages_list)
    messages_list = messages_list[:messages_count]
    
    # 禁用思维链，减少推理开销、提升速度稳定性
    extra_body = {"thinking": {"type": "disabled"}}
    
    # 设置并发数：根据任务规模自适应，最多10个并发
    max_workers = min(10, len(messages_list)) if len(messages_list) > 0 else 1
    
    # 确保输出目录存在
    if not os.path.exists(os.path.dirname(args.output)):
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        
    try:
        # 记录开始时间
        start = time.time()
        
        # 调用AI模型批量生成回复
        if args.lora_path:
            reply_list = client.batch_generate(messages_list, 
                                            max_workers=max_workers, 
                                            extra_body=extra_body,
                                            lora_path=args.lora_path)
        else:
            reply_list = client.batch_generate(messages_list, 
                                            max_workers=max_workers, 
                                            extra_body=extra_body)
        
        # 计算耗时
        elapsed = time.time() - start
        print(f"批量生成 {messages_count} 条回复耗时 {elapsed:.2f} 秒")
        
        # 解析回复结果
        for item, reply in zip(letters_items, reply_list):
            # 保存原始AI回复
            item["answer"] = reply
            # 从回复中提取intent和response
            intent, response = extract_intent_response(reply)
            if intent:
                item["intent"] = intent
            if response:
                item["response"] = response
        
        # 保存结果到JSON文件
        save_answers(args.output, letters_items)
        print(f"已将 {messages_count} 条回复保存至 {args.output}")
        
    except Exception as e:
        print(f"批量生成回复时出错：{e}")
    finally:
        # 关闭AI客户端连接
        client.close()

if __name__ == "__main__":
    main()
