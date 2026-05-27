# -*- coding: utf-8 -*-
"""
find_unsafe.py - 学生来信安全隐患检测模块

本模块用于分析学生来信的文字内容，判断其是否存在严重心理安全风险。
通过调用AI模型，系统能够识别7类不同的安全风险：
    1. 自杀倾向
    2. 针对他人的暴力或伤害倾向
    3. 非自杀性自伤行为
    4. 严重的物质滥用
    5. 严重的进食障碍
    6. 疑似精神病性症状
    7. 卷入高危活动或畸形关系

输入：JSON格式的学生来信数据
输出：包含风险代码和原因的分析结果
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
import re  # 正则表达式，用于解析AI返回结果


def load_letters(path: str) -> List[Dict]:
    """
    从指定 JSON 文件中读取每项的 index、letter，并额外读取 subject、grade、emotion、keyword（若存在）。
    - 若仅有 'reply'，则回退为 'letter'。

    参数：
        path: JSON 文件的绝对路径。
    返回：
        列表：每项为 {"index": int, "subject": str, "grade": str, "emotion": str, "keyword": str, "letter": str}
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
            idx += 1
            if letter and isinstance(idx, int):
                items_out.append({
                    "index": idx,
                    "letter": letter
                })
    return items_out

def process_letters(items: List[Dict]):
    prefix = """
    以下是一个用于判断学生来信是否有不安全倾向（如自杀倾向）的Prompt模板，它结合了心理学知识、危险信号识别和应急处理步骤，可以帮助你系统性地进行评估和决策：
# 任务指令​
你是一名心理健康支持人员，需要分析学生来信的文字内容，判断其是否存在严重心理安全风险。请按以下框架逐步分析：
1. 自杀倾向
关键词与隐喻：识别信中是否出现以下语言信号：
直接或间接表达绝望（如“活着没意义”“坚持不下去了”）
自我否定（如“我是累赘”“没有我会更好”）
提及死亡或自杀方式（如“想消失”“希望一直睡着”）
情绪描述：注意是否频繁描述极端孤独、无助、失控感，或长期失眠、食欲丧失等生理问题。
近期变化：信中是否提及突然的行为转变（如分发财物、与人道别、放弃珍视事物）。
2. 针对他人的暴力或伤害倾向
关键词与隐喻：识别信中是否出现以下语言信号：
直接威胁：如“真想杀了某人”、“让他们付出代价”。
敌意与偏执：坚信自己被特定个人或团体迫害、针对，言语中充满恨意。
计划与工具：提及获取或准备武器（如刀、化学品），或有具体的伤害计划。
情绪与认知：注意是否表现出极度愤怒、认为暴力是唯一解决方案，或感到被逼入绝境、必须反抗。
相关行为：信中是否透露出跟踪、监视、或实际准备伤害他人的行为迹象。
3. 非自杀性自伤行为
关键词与隐喻：识别信中是否出现以下语言信号：
行为描述：直接或隐喻性地描述自伤行为，如“用疼痛让自己清醒”、“在皮肤上刻下印记”、“用灼烧感对抗麻木”。
功能表达：将自伤与情绪调节联系起来，如“这样我能感觉到自己还活着”、“只有流血时心里才平静”。
情绪与认知：注意是否频繁描述解离感（如灵魂出窍、与世界隔层膜）、无法表达的情绪，或通过自伤来惩罚自己。
相关行为：信中是否提及隐藏伤痕（如“夏天也穿长袖”）、收集特定工具，或自伤频率、严重程度在增加。
4. 严重的物质滥用
关键词与隐喻：识别信中是否出现以下语言信号：
使用描述：直接提及或使用黑话描述酗酒、滥用处方药（如镇静剂）、吸食毒品的行为。
依赖表达：如“离了它我撑不下去”、“只有用它才能逃离现实”。
情绪与认知：注意是否将物质作为应对痛苦、失眠、空虚的唯一手段，或对失控状态感到羞耻但无力改变。
相关行为：信中是否提及因滥用导致学业崩溃、经济困难、健康恶化（如呕吐、昏迷）或法律风险。
5. 严重的进食障碍
关键词与隐喻：识别信中是否出现以下语言信号：
行为描述：描述极端的进食控制行为，如“已经三天只喝水”、“暴食后必须吐干净”、“每天计算每一卡路里”。
身体意象扭曲：如“我觉得自己像个肿胀的怪物”、“再瘦十斤也许才值得被爱”。
情绪与认知：注意是否将体重、食物与自我价值、罪恶感、控制感紧密绑定，并对身体形象有极度扭曲的认知。
相关行为：信中是否提及因节食/暴食导致的生理症状，如晕厥、停经、严重脱发、胃痛，或对体重数字的强迫性关注。
6. 疑似精神病性症状
关键词与隐喻：识别信中是否出现以下语言信号：
幻觉体验：描述听到、看到、感觉到不存在的事物，如“有个声音在命令我”、“墙里有东西在蠕动”。
妄想信念：表达坚信但脱离现实的念头，如“我被组织监控了”、“我能通过特殊电波与人交流”。
情绪与认知：注意是否表现出因这些体验而产生恐惧、困惑，或思维变得支离破碎、逻辑难以理解。
相关行为：信中是否透露出因这些症状而出现社交退缩、无法完成日常任务，或做出令人费解的行为。
7. 卷入高危活动或畸形关系
关键词与隐喻：识别信中是否出现以下语言信号：
关系描述：描述处于虐待性、控制性或剥削性的关系中，如“他打我但我离不开”、“我必须听从他们的一切要求”。
活动描述：提及参与危险行为，如无保护的多性伴行为、危险驾驶、赌博欠债、或从事违法交易。
情绪与认知：注意是否感到被困住、无力摆脱、羞于求助，或通过冒险行为来寻求刺激、麻木痛苦、证明自己。
相关行为：信中是否提及因此遭遇身体伤害、性威胁、财产损失、法律追究，或陷入持续的恐惧与不安中。
    """
    subfix = """
    请判断该信是否存在严重心理安全风险。如果存在，请输出对应安全问题（1-7）；如果不存在，请输出0。
    输出格式：
    安全问题编号：0-7
    原因：<详细描述输出该编号的具体原因>
    """
    messages_list = []
    for item in items:
        letter = "letters:" + item["letter"]
        messages_list.append([{"role": "user", "content": prefix + letter + subfix}])
    return messages_list

def save_answers(path: str, answers: List[Dict]):
    """
    将答案列表保存为 JSON 文件。
    
    参数：
        path: 输出文件路径。
        answers: 每条包含 index、original_reply、answer 的字典。
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(answers, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"写入 JSON 失败：{e}")


def parse_answer_fields(answer: str):
    if not isinstance(answer, str):
        return [], ""
    m_code = re.search(r"安全问题编号[:：]\s*(.+)", answer, re.S)
    codes: List[int] = []
    if m_code:
        raw = m_code.group(1)
        raw_line = raw.splitlines()[0]
        for ch in re.findall(r"[0-7]", raw_line):
            codes.append(int(ch))
        if not codes:
            m_num = re.search(r"\b(\d+)\b", raw_line)
            if m_num:
                num = int(m_num.group(1))
                if 0 <= num <= 7:
                    codes = [num]
    m_reason = re.search(r"原因[:：]\s*(.+)", answer, re.S)
    reason = m_reason.group(1).strip() if m_reason else ""
    return codes , reason


def build_runtime_client(if_local: bool = False, lora_path: str | None = None):
    client = create_doubao_client()
    if if_local:
        from clients.qwen3_8b_client import create_qwen3_8b_client

        client = create_qwen3_8b_client()
    return client


def detect_single_letter(
    letter: str,
    *,
    client=None,
    if_local: bool = False,
    lora_path: str | None = None,
) -> Dict:
    managed_client = client is None
    runtime_client = client or build_runtime_client(if_local=if_local, lora_path=lora_path)

    try:
        items = [{"index": 1, "letter": letter.strip()}]
        messages_list = process_letters(items)
        extra_body = {"thinking": {"type": "disabled"}}
        kwargs = {"max_workers": 1, "extra_body": extra_body}
        if lora_path:
            kwargs["lora_path"] = lora_path
        reply = runtime_client.batch_generate(messages_list, **kwargs)[0]
        codes, reason = parse_answer_fields(reply)
        return {
            "letter": letter,
            "answer": reply,
            "risk_codes": codes,
            "reason": reason,
        }
    finally:
        if managed_client:
            runtime_client.close()

def parse_cli_args() -> int:
    parser = argparse.ArgumentParser(description="选择各字段列表中的索引项，-1 表示枚举所有组合")
    parser.add_argument("-i", "--input", type=str, 
                        default=r"/home/pthan/project/safety_xunfei/evaluation/2/filter_evaluation.scored.not_meet.json")
    parser.add_argument("-o", "--output", type=str, 
                        default=r"/home/pthan/project/safety_xunfei/unsafe_detect/3_local/unsafe.json")
    parser.add_argument("-l", "--if_local", type=bool, 
                        default=False, 
                        help="是否使用本地AI模型，默认False（使用远端豆包模型）")
    parser.add_argument("-p", "--lora_path", type=str, 
                        default=None,
                        help="本地AI模型lora路径，默认Qwen3-8b/lora/sft/")



    args = parser.parse_args()
    return args

def main():
    args = parse_cli_args()
    letters_items = load_letters(args.input)
    if not letters_items:
        print("未加载到有效回复项，程序退出。")
        return
    client = build_runtime_client(if_local=args.if_local, lora_path=args.lora_path)
    
    messages_list = process_letters(letters_items)
    #小幅度测试
    #messages_count = 3
    messages_count = len(messages_list)
    messages_list = messages_list[:messages_count]
    # 4) 可选参数：禁用思维链，减少推理开销、提升速度稳定性
    extra_body = {"thinking": {"type": "disabled"}}

    # 5) 执行批量生成（并发）。并发度可按需求调整，这里取 5 或任务数较小值
    # 并发度按任务规模自适应（最多 5），避免任务过少时线程浪费
    max_workers = min(10, len(messages_list)) if len(messages_list) > 0 else 1
    if not os.path.exists(os.path.dirname(args.output)):
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        
    try:
        start = time.time()
        if args.lora_path:
            reply_list = client.batch_generate(messages_list, 
                                               max_workers=max_workers, 
                                               extra_body=extra_body, 
                                               lora_path=args.lora_path)
        else:
            reply_list = client.batch_generate(messages_list, 
                                               max_workers=max_workers, 
                                               extra_body=extra_body)
        elapsed = time.time() - start
        print(f"批量生成 {messages_count} 条回复耗时 {elapsed:.2f} 秒")
        for item, reply in zip(letters_items, reply_list):
            item["answer"] = reply
            codes, reason = parse_answer_fields(reply)
            item["risk_codes"] = codes
            item["reason"] = reason
        save_answers(args.output, letters_items)
        print(f"已将 {messages_count} 条回复保存至 {args.output}")
    except Exception as e:
        print(f"批量生成回复时出错：{e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
