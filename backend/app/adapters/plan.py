import os
import re
import json
import time
from typing import Dict, Any, Optional, List
from openai import OpenAI

from app.adapters.persona_config import (
    PERSONAS,
    STYLE_AXES_DEF,
    get_all_persona_names,
    get_persona_style_config,
    normalize_persona_name,
)

# ==========================================
# 3. Agent 1: Planner 的 Prompt
# ==========================================
PLANNER_PROMPT = """
你现在是一个顶级的“心理干预策略规划师”（Planner Agent）。
你的任务是【阅读用户来信】，并根据指定的【人格风格设定】，为下游的“回信撰写者”（Writer Agent）制定一份详细的【执行计划】。

【下游撰写者的人格风格设定】
- 叙事强度：{narrative} ({desc_narrative})
- 建议结构：{advice} ({desc_advice})
- 共情表达：{empathy} ({desc_empathy})
- 认知干预：{cognitive} ({desc_cognitive})

【你的任务】
请输出一个 JSON，包含以下字段：
1. "intent_analysis": 深度剖析用户当前的核心情绪、未说出口的需求，以及是否存在自伤等安全风险。
2. "generation_plan": 针对上述【指定风格】，给下游 Writer Agent 写一份严密的指导计划。说明该分几段写、每一段的核心任务是什么、如何具体体现这四种风格。

【输出格式要求】只输出 JSON：
{{
    "intent_analysis": "...",
    "generation_plan": "第一段：...，第二段：..."
}}
"""

# ==========================================
# 4. Agent 2: Generator 的 Prompt
# ==========================================
GENERATOR_PROMPT = """
你是一个专业的书信回复助手（Writer Agent）。
你需要严格按照“策略规划师”（Planner）提供的大纲和意图剖析，为用户撰写一封回信。

【规划师给你的意图剖析】
{intent_analysis}

【规划师给你的强制执行大纲 (Plan)】
{generation_plan}

【撰写铁律】
1. 严格使用书信体结构（称呼-正文-落款）。
2. 绝对服从规划师规定的人格风格和段落布局。
3. 严禁使用“小XX”、“呀呢嘛”等装可爱的词汇。
4. 严禁使用“笔尖颤抖”、“乌云银边”等虚假、悬浮的 AI 常见比喻（防豆包风）。
5. 必须要有真实人类的温度和分寸感。

【输出格式要求】只输出 JSON：
{{
    "response": "你撰写的最终书信内容"
}}
"""

def _safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    if not text: return None
    try:
        return json.loads(text)
    except:
        m = re.search(r"\{[\s\S]*\}", text, re.DOTALL)
        if m:
            try: return json.loads(m.group(0))
            except: pass
    return None

# ==========================================
# 5. 核心多智能体流水线
# ==========================================
def run_multi_agent_pipeline(
    client, 
    planner_model: str, 
    generator_model: str, 
    user_letter: str, 
    persona_name: str
) -> Dict[str, Any]:
    persona_name = normalize_persona_name(persona_name)
    style_config = get_persona_style_config(persona_name)
    
    # --- Step 1: 触发 Planner Agent ---
    print(f"\n[Agent 1: Planner] 正在使用【{persona_name}】人格进行分析与规划...")
    planner_sys_prompt = PLANNER_PROMPT.format(
        narrative=style_config["narrative"],
        desc_narrative=STYLE_AXES_DEF["narrative"][style_config["narrative"]],
        advice=style_config["advice"],
        desc_advice=STYLE_AXES_DEF["advice"][style_config["advice"]],
        empathy=style_config["empathy"],
        desc_empathy=STYLE_AXES_DEF["empathy"][style_config["empathy"]],
        cognitive=style_config["cognitive"],
        desc_cognitive=STYLE_AXES_DEF["cognitive"][style_config["cognitive"]]
    )
    
    planner_resp = client.chat.completions.create(
        model=planner_model,
        messages=[
            {"role": "system", "content": planner_sys_prompt},
            {"role": "user", "content": f"【用户来信】\n{user_letter}"}
        ],
        temperature=0.3 # 规划者需要理性严谨
    )
    
    plan_data = _safe_json_parse(planner_resp.choices[0].message.content)
    if not plan_data:
        raise ValueError("Planner 未能输出合规的 JSON")
        
    intent = plan_data.get("intent_analysis", "")
    plan = plan_data.get("generation_plan", "")
    print("[Agent 1: Planner] 规划完成。")

    # --- Step 2: 触发 Generator Agent ---
    print(f"[Agent 2: Generator] 正在根据 Planner 大纲执笔写信...")
    generator_sys_prompt = GENERATOR_PROMPT.format(
        intent_analysis=intent,
        generation_plan=plan
    )
    
    generator_resp = client.chat.completions.create(
        model=generator_model,
        messages=[
            {"role": "system", "content": generator_sys_prompt},
            {"role": "user", "content": f"请为以下来信撰写回复：\n\n【用户来信】\n{user_letter}"}
        ],
        temperature=0.7 # 写手需要一定的文字创造力
    )
    
    letter_data = _safe_json_parse(generator_resp.choices[0].message.content)
    if not letter_data:
        # 如果 JSON 解析失败，直接取 text
        final_letter = generator_resp.choices[0].message.content
    else:
        final_letter = letter_data.get("response", generator_resp.choices[0].message.content)

    print("[Agent 2: Generator] 撰写完成。")
    
    # 返回完整的链路追踪数据
    return {
        "persona": persona_name,
        "style_config": style_config,
        "raw_persona_config": PERSONAS[persona_name],
        "user_letter": user_letter.strip(),
        "planner_intent": intent,
        "planner_plan": plan,
        "final_response": final_letter.strip()
    }

# ==========================================
# 6. 测试运行
# ==========================================
def main():
    # 初始化客户端（由于架构解耦，你可以 Planner 用 GPT-4o，Generator 用 Doubao 等）
    client = OpenAI(
        api_key=os.getenv("GPT_API_KEY", ""),
        base_url="https://api.chatanywhere.tech/v1" 
    )
    
    PLANNER_MODEL = "gpt-4o-mini"
    GENERATOR_MODEL = "gpt-4o-mini" # 实际跑可以用 "doubao-1-5-pro-32k"

    sample_letter = """
    老师你好，我是一名高二理科生。最近一次月考我物理不及格，这是从来没有过的事。看着成绩单我脑子一片空白。爸妈虽然没骂我，但我看到他们欲言又止的样子更难受。我觉得自己这大半年的努力像个笑话。我现在一看到物理题就恶心，晚自习一翻开书就想哭。我感觉自己可能根本不是学理科的料，是不是我现在放弃比较好？但我又不敢说。我很绝望。
    """

    print("💌 用户来信：", sample_letter.strip())

    # 遍历全部人格，观察每种人格下的生成差异
    test_personas = get_all_persona_names()
    print(f"本次将生成 {len(test_personas)} 种人格回复：{', '.join(test_personas)}")
    
    results = []
    for persona in test_personas:
        result = run_multi_agent_pipeline(
            client=client,
            planner_model=PLANNER_MODEL,
            generator_model=GENERATOR_MODEL,
            user_letter=sample_letter,
            persona_name=persona
        )
        results.append(result)
        
        print("-" * 50)
        print(f"🌟 【最终交付 - {persona}】")
        print(result["final_response"])
        print("-" * 50)

    # 保存流水线数据，用于后续作为大模型的 SFT 数据
    with open("multi_agent_output.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
