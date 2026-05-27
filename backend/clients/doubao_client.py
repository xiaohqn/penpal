#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输入：
- 调用方向客户端传入的消息列表、模型名、采样参数，以及运行环境中的豆包 API 配置。
- 优先读取 `backend/.env` 对应的 Settings 中的豆包配置；如果没有，再回退到进程环境变量
  `DOUBAO_API_KEY` / `ARK_API_KEY` 与可选的 `DOUBAO_BASE_URL` / `ARK_BASE_URL`。
输出：
- 返回豆包模型生成的文本结果、流式片段或批量生成结果；失败时抛出带上下文的异常。
作用：
- 这个文件封装了安全链路和独立脚本会复用的豆包客户端能力，并负责把运行环境中的配置
  统一组装成 OpenAI 兼容接口调用参数，避免把 API Key 写死在仓库里，提升迁移与部署稳定性。
"""

import os
import threading
import queue
import concurrent.futures
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import time
try:
    from tqdm import tqdm
except Exception:
    tqdm = None

try:
    import openai
    from openai import OpenAI
except ImportError:
    print("请先安装openai库: pip install openai")
    raise


from clients.base_client import ModelConfig
from clients.base_client import BaseClient


def _load_backend_settings():
    """
    输入：
    - 无显式参数；内部尝试导入后端的 `get_settings()`。
    输出：
    - 成功时返回 Settings 实例；如果当前运行环境拿不到后端配置模块，则返回 `None`。
    作用：
    - 让兼容脚本使用的 client 也能优先读取 `backend/.env`，避免安全链路必须额外依赖
      `export DOUBAO_API_KEY=...` 这类进程级环境变量。
    """

    try:
        from app.core.config import get_settings
    except Exception:
        return None

    try:
        return get_settings()
    except Exception:
        return None

@dataclass
class DoubaoConfig(ModelConfig):
    """豆包配置类"""
    api_key: str
    model: str 
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: int = 30
    base_url: str = "https://ark.cn-beijing.volces.com/api/v3"  # 豆包API端点


class DoubaoClient(BaseClient):
    """
    豆包API客户端类
    
    这个类使用官方的openai库来与豆包API进行交互，
    因为豆包API兼容OpenAI格式。
    """
    
    def __init__(self, config: DoubaoConfig, threads=10):
        """
        初始化豆包客户端
        
        Args:
            config: 豆包配置对象，包含API密钥、模型等参数
            threads: 线程池大小，默认为10
        """
        self.config = config
        self.threads = threads
        self._lock = threading.Lock()  # 线程锁，确保线程安全
        self._thread_pool = None  # 线程池，延迟初始化
        
        # 初始化OpenAI客户端（兼容豆包API）
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout
        )
    
    def _get_thread_pool(self):
        """获取线程池，延迟初始化（无锁，线程安全由 CPython 字节码保证）"""
        if self._thread_pool is None:
            # 简单赋值即可，CPython 中线程不会同时进入同一分支
            self._thread_pool = ThreadPoolExecutor(max_workers=self.threads)
        return self._thread_pool
    
    def generate(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        发送请求到豆包API
        
        Args:
            messages: 消息列表，格式为 [{"role": "user/system/assistant", "content": "消息内容"}]
            model: 模型名称（可选，如果不指定则使用配置中的默认值）
            max_tokens: 最大token数（可选）
            temperature: 温度参数（可选）
            **kwargs: 其他传递给API的参数
            
        Returns:
            豆包的回复内容
            
        Raises:
            Exception: 当请求失败时
        """
        try:
            # 构建请求参数
            request_params = {
                "model": model or self.config.model,
                "messages": messages,
                "max_tokens": max_tokens or self.config.max_tokens,
                "temperature": temperature or self.config.temperature,
            }
            
            # 添加额外的参数
            request_params.update(kwargs)
            
            # 无锁并行请求
            response = self.client.chat.completions.create(**request_params)
            
            # 提取回复内容
            if response.choices and response.choices[0].message:
                return response.choices[0].message.content
            else:
                raise Exception("响应格式错误: 无法提取回复内容")
                
        except openai.OpenAIError as e:
            # 处理豆包API错误
            raise Exception(f"豆包API错误: {str(e)}")
        except Exception as e:
            # 处理其他错误
            raise Exception(f"豆包请求出错: {str(e)}")
    
    def stream_generate(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ):
        """
        流式聊天接口
        
        Args:
            messages: 消息列表
            model: 模型名称（可选，如果不指定则使用配置中的默认值）
            max_tokens: 最大token数（可选）
            temperature: 温度参数（可选）
            **kwargs: 其他参数
            
        Yields:
            逐个字节的回复内容
        """
        try:
            # 构建请求参数
            request_params = {
                "model": model or self.config.model,
                "messages": messages,
                "max_tokens": max_tokens or self.config.max_tokens,
                "temperature": temperature or self.config.temperature,
                "stream": True,
            }
            request_params.update(kwargs)
            
            # 无锁并行流式请求
            stream = self.client.chat.completions.create(**request_params)
            
            # 逐个字节yield回复内容
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
                        
        except openai.OpenAIError as e:
            raise Exception(f"豆包API错误: {str(e)}")
        except Exception as e:
            raise Exception(f"豆包流式请求出错: {str(e)}")
    
    def get_available_models(self) -> List[str]:
        """
        获取可用的模型列表
        
        Returns:
            模型名称列表
        """
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            print(f"获取豆包模型列表失败: {e}")
            return []
    
    def batch_generate(
        self,
        messages_list: List[List[Dict[str, str]]],
        models: Optional[List[str]] = None,
        max_workers: Optional[int] = None,
        **kwargs
    ) -> List[str]:
        """
        批量生成文本（多线程优化）
        
        返回顺序与输入的 messages_list 顺序严格一致，避免错位。
        """
        if max_workers is None:
            max_workers = self.threads

        # 预分配结果列表，确保结果位置与输入索引一致
        results: List[Optional[str]] = [None] * len(messages_list)
        total = len(messages_list)
        pb = tqdm(total=total, desc="批量生成", unit="req") if tqdm else None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {}
            for i, messages in enumerate(messages_list):
                model = models[i] if models and i < len(models) else None
                # 提交任务，并记录该 future 对应的原始索引
                future = executor.submit(self._generate_single, messages, model, **kwargs)
                future_to_index[future] = i

            # 收集结果：按 future 完成事件更新到对应索引位置，保证输出顺序与输入一致
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    result = future.result()
                except Exception as e:
                    # 如果某个请求失败，将错误信息写入对应位置
                    raise Exception(f"错误: {str(e)}")
                results[idx] = result
                if pb:
                    pb.update(1)

        # 所有位置都已写入，返回与输入顺序一致的结果列表
        if pb:
            pb.close()
        return results
    
    def _generate_single(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        生成单个请求的辅助方法
        
        Args:
            messages: 消息列表
            model: 模型名称
            **kwargs: 其他参数
            
        Returns:
            生成的文本内容
        """
        max_retries = int(kwargs.pop("max_retries", 5))
        retry_interval = float(kwargs.pop("retry_interval", 1.0))
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                model_to_use = model or self.config.model
                request_params = {
                    "model": model_to_use,
                    "messages": messages,
                    "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
                    "temperature": kwargs.get('temperature', self.config.temperature),
                }
                request_params.update(kwargs)
                response = self.client.chat.completions.create(**request_params)
                result = response.choices[0].message.content
                return result
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    time.sleep(retry_interval * attempt)
                else:
                    raise Exception(f"豆包API调用失败，已重试{max_retries}次: {str(last_error)}")
    
    def batch_stream_generate(
        self,
        messages_list: List[List[Dict[str, str]]],
        models: Optional[List[str]] = None,
        max_workers: Optional[int] = None,
        **kwargs
    ):
        """
        批量流式生成文本（多线程优化）
        
        Args:
            messages_list: 消息列表的列表
            models: 每个请求使用的模型列表
            max_workers: 最大工作线程数
            **kwargs: 其他参数
            
        Yields:
            tuple: (索引, 文本片段) 对，用于标识哪个请求的哪个片段
        """
        if max_workers is None:
            max_workers = self.threads

        # 使用队列管理并发流
        result_queue = queue.Queue()
        
        def _stream_worker(index, messages, model):
            """流式工作线程"""
            last_error = None
            max_retries = int(kwargs.pop("max_retries", 5))
            retry_interval = float(kwargs.pop("retry_interval", 1.0))
            for attempt in range(1, max_retries + 1):
                try:
                    model_to_use = model or self.config.model

                    # 构建请求参数
                    request_params = {
                        "model": model_to_use,
                        "messages": messages,
                        "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
                        "temperature": kwargs.get('temperature', self.config.temperature),
                        "stream": True,
                    }
                    request_params.update(kwargs)

                    # 无锁并行流式请求：去除全局锁，避免串行化阻塞
                    stream = self.client.chat.completions.create(**request_params)

                    # 逐块yield内容
                    for chunk in stream:
                        if chunk.choices[0].delta.content is not None:
                            result_queue.put((index, chunk.choices[0].delta.content))
                    break
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        time.sleep(retry_interval * attempt)
                    else:
                        result_queue.put((index, f"错误: {str(last_error)}（已重试{max_retries}次）"))
            result_queue.put((index, None))
        
        # 启动所有工作线程
        threads = []
        for i, messages in enumerate(messages_list):
            model = models[i] if models and i < len(models) else None
            thread = threading.Thread(target=_stream_worker, args=(i, messages, model))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # 收集结果（采用与 batch_generate 一致的命名风格）
        total = len(messages_list)
        pb = tqdm(total=total, desc="并行流式", unit="req") if tqdm else None
        results: List[List[str]] = [[] for _ in range(total)]
        completed: List[bool] = [False] * total
        completed_count = 0
        next_idx = 0

        while completed_count < total:
            try:
                idx, result = result_queue.get(timeout=1.0)
                if result is None:
                    if not completed[idx]:
                        completed[idx] = True
                        completed_count += 1
                    while next_idx < total and completed[next_idx]:
                        for piece in results[next_idx]:
                            yield (next_idx, piece)
                        results[next_idx].clear()
                        if pb:
                            pb.update(1)
                        next_idx += 1
                else:
                    results[idx].append(result)
            except queue.Empty:
                continue
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        if pb:
            pb.close()
    
    def close(self):
        """
        关闭客户端，清理资源
        
        关闭线程池，释放资源
        """
        if self._thread_pool is not None:
            with self._lock:
                if self._thread_pool is not None:
                    self._thread_pool.shutdown(wait=True)
                    self._thread_pool = None
    
    def __del__(self):
        """析构函数，确保资源被清理"""
        self.close()


def create_doubao_client(model: str = "doubao-1-5-pro-32k-250115", **kwargs) -> DoubaoClient:
    """
    输入：
    - model：调用豆包时使用的模型名称。
    - kwargs：其他客户端配置项；如果显式传入 `api_key` 或 `base_url`，会优先覆盖环境变量。
    输出：
    - 返回配置完成的 `DoubaoClient` 实例。
    作用：
    - 为安全检测、安全回复和高亮提取提供统一的豆包客户端工厂，并优先从 `backend/.env`
      读取配置；只有在拿不到后端配置时，才回退到进程环境变量，保证 Web 服务和独立脚本
      的配置来源尽量一致。
    """
    settings = _load_backend_settings()

    # 优先级顺序设计为：显式传参 > backend/.env 对应的 Settings > 进程环境变量。
    # 这样既保留脚本手动覆写能力，也能让常规服务启动统一使用 `.env` 中的配置。
    api_key = (
        kwargs.pop("api_key", None)
        or getattr(settings, "doubao_api_key", None)
        or os.getenv("DOUBAO_API_KEY")
        or os.getenv("ARK_API_KEY")
    )
    if not api_key:
        raise ValueError("未找到豆包 API Key，请在 backend/.env 中设置 DOUBAO_API_KEY，或提供 ARK_API_KEY")

    base_url = (
        kwargs.pop("base_url", None)
        or getattr(settings, "doubao_base_url", None)
        or os.getenv("DOUBAO_BASE_URL")
        or os.getenv("ARK_BASE_URL")
        or "https://ark.cn-beijing.volces.com/api/v3"
    )
    
    config = DoubaoConfig(
        api_key=api_key,
        model=model,
        base_url=base_url,
        **kwargs
    )
    
    return DoubaoClient(config)


# 使用示例和测试代码
if __name__ == "__main__":
    print("豆包API客户端示例 - 多线程版本")
    print("=" * 60)
    
    # 示例1: 基本多线程批量生成
    print("示例1: 基本多线程批量生成")
    print("-" * 30)
    
    try:
        client = create_doubao_client()
        
        # 准备多个问题
        questions = [
            "请介绍一下人工智能的基本概念",
            "什么是机器学习？",
            "深度学习的原理是什么？"
        ]
        
        # 构建消息列表
        messages_list = []
        for question in questions:
            messages_list.append([{"role": "user", "content": question}])
        
        import time
        start_time = time.time()
        
        # 使用批量生成方法
        results = client.batch_generate(messages_list, max_workers=3)
        
        end_time = time.time()
        print(f"批量生成完成，耗时: {end_time - start_time:.2f}秒")
        
        for i, (question, answer) in enumerate(zip(questions, results)):
            print(f"\n问题 {i+1}: {question}")
            print(f"回答: {answer[:100]}...")  # 显示前100个字符
            
    except Exception as e:
        print(f"批量生成失败: {e}")
    
    print("\n" + "=" * 60)
    
    # 示例2: 多轮对话（支持多线程）
    print("示例2: 多轮对话")
    print("-" * 30)
    
    try:
        client = create_doubao_client()
        
        # 构建多轮对话
        messages = [
            {"role": "system", "content": "你是一个专业的技术专家。"},
            {"role": "user", "content": "什么是机器学习？"},
            {"role": "assistant", "content": "机器学习是人工智能的一个分支..."},
            {"role": "user", "content": "能举个具体的例子吗？"}
        ]
        extra_body={"thinking": {"type": "disabled",}}
        
        response = client.generate(messages,extra_body=extra_body)
        print(f"豆包: {response}")
        
    except Exception as e:
        print(f"错误: {e}")
    
    print("\n" + "=" * 60)
    
    # 示例3: 流式输出（支持线程安全）
    print("示例3: 流式输出")
    print("-" * 30)
    
    try:
        client = create_doubao_client()
        
        extra_body={"thinking": {"type": "disabled",}}
        messages = [
            {"role": "user", "content": "请用100字左右介绍Python语言的特点"}
        ]
        
        print("豆包: ", end="", flush=True)
        for chunk in client.stream_generate(messages,extra_body=extra_body):
            print(chunk, end="", flush=True)
        print()  # 换行
        
    except Exception as e:
        print(f"错误: {e}")
    
    print("\n" + "=" * 60)
    
    # 示例4: 并行流式输出
    print("示例4: 并行流式输出")
    print("-" * 30)
    
    try:
        client = create_doubao_client()
        
        extra_body={"thinking": {"type": "disabled",}}
        messages_list = [
            [{"role": "user", "content": "请用100字左右介绍Python语言的特点"}],
            [{"role": "user", "content": "请用100字左右介绍Java语言的特点"}]
        ]
        
        print("豆包并行流式输出: ")
        results = {i: "" for i in range(len(messages_list))}
        
        for index, chunk in client.batch_stream_generate(messages_list, extra_body=extra_body, max_workers=2):
            results[index] += chunk
            print(f"[{index}] {chunk}", end="", flush=True)
        
        print("\n\n最终结果汇总:")
        for i, result in results.items():
            print(f"任务{i}: {result[:80]}...")
        
    except Exception as e:
        print(f"错误: {e}")
    
    print("\n" + "=" * 60)
    
    # 示例5: 性能对比测试
    print("示例5: 性能对比测试")
    print("-" * 30)
    
    try:
        client = create_doubao_client()
        
        # 准备测试问题
        questions = [
            "解释量子计算的基本原理",
            "什么是区块链技术？",
            "请说明5G网络的特点"
        ]
        
        messages_list = []
        for question in questions:
            messages_list.append([{"role": "user", "content": question}])
        
        # 顺序执行
        print("顺序执行...")
        start_time = time.time()
        
        sequential_results = []
        try:
            for messages in messages_list:
                # 传入完整的消息列表，而不是字符串
                result = client.generate(messages, extra_body={"thinking": {"type": "disabled"}})
                sequential_results.append(result)
        except Exception as e:
            sequential_results.append(f"错误: {e}")
        
        sequential_time = time.time() - start_time
        print(f"顺序执行耗时: {sequential_time:.2f}秒")
        
        # 并发执行
        print("\n并发执行...")
        start_time = time.time()
        
        concurrent_results = client.batch_generate(messages_list, max_workers=3, extra_body={"thinking": {"type": "disabled"}})
        concurrent_time = time.time() - start_time
        print(f"并发执行耗时: {concurrent_time:.2f}秒")
        print(f"并发加速比: {sequential_time/concurrent_time:.2f}x")
        
    except Exception as e:
        print(f"性能测试失败: {e}")
    
    print("\n" + "=" * 60)
    print("所有示例完成！记得调用 client.close() 释放资源")
    
    # 清理资源
    try:
        client.close()
        print("资源已清理")
    except:
        pass
