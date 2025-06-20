from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import DeepSeekConfig
from camel.messages import BaseMessage
from camel.agents import ChatAgent
from camel.types import OpenAIBackendRole
from dotenv import load_dotenv
import os
import tkinter as tk
import tkinter.font as font
import threading
import queue
import time

load_dotenv("D:\\gitRepo\\camel\\.env")

# 创建模型实例（启用流式响应）
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEEPSEEK,
    model_type=ModelType.DEEPSEEK_CHAT,
    model_config_dict={"temperature": 1.0, "stream": True},  # 确保启用流模式
)

system_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="Whatever others say, you just repeat what they say. Do not speak anything extra.",
)

class GUI:
    def __init__(self, agent):
        self.root = tk.Tk()
        self.root.title("Streaming Chat")
        self.root.geometry("1280x960+30+30")
        self.interface()
        self.agent = agent
        self.response_queue = queue.Queue()  # 用于线程间通信
        self.current_response = ""  # 当前累积的响应内容
        self.is_streaming = False  # 流式响应状态标志
        self.root.after(100, self.process_queue)  # 启动队列处理循环
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)  # 处理窗口关闭事件

    def interface(self):
        self.font_of_btn = font.Font(weight="bold")
        self.send_btn = tk.Button(
            self.root,
            text="SEND",
            font=self.font_of_btn,
            bg="LightSkyBlue",
            command=self.send
        )
        self.send_btn.place(relx=0.9, rely=0.9, relwidth=0.05, relheight=0.05)
        
        self.send_text = tk.Text(self.root)
        self.send_text.place(relx=0.05, rely=0.9, relheight=0.05, relwidth=0.85)
        
        # 使用Text控件替代Label，支持多行显示和滚动
        self.ans_text = tk.Text(
            self.root, 
            state=tk.DISABLED,  # 初始为禁用状态
            wrap=tk.WORD,
            font=("Arial", 12)
        )
        self.ans_text.place(relx=0.05, rely=0.05, relheight=0.8, relwidth=0.9)
        
        # 添加滚动条
        scrollbar = tk.Scrollbar(self.root, command=self.ans_text.yview)
        scrollbar.place(relx=0.95, rely=0.05, relheight=0.8, relwidth=0.02)
        self.ans_text.config(yscrollcommand=scrollbar.set)

    def send(self):
        if self.is_streaming:
            return  # 防止在前一个响应完成前发送新请求
            
        user_input = self.send_text.get('1.0', 'end-1c').strip()  # 获取文本并移除首尾空白
        if not user_input:
            return
            
        self.send_text.delete('1.0', tk.END)  # 清空输入框
        self.is_streaming = True
        
        # 在文本框中添加用户消息
        self.update_response(f"You: {user_input}\n\nAssistant: ", clear=False)
        
        # 启动新线程处理流式响应
        threading.Thread(
            target=self.stream_response,
            args=(user_input,),
            daemon=True
        ).start()

    def stream_response(self, user_input):
        """在后台线程中处理流式响应"""
        try:
            # 创建用户消息
            user_msg = BaseMessage.make_user_message(role_name="User", content=user_input)
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": system_msg.content},
                {"role": "user", "content": user_input}
            ]
            
            # 关键修改点：直接使用模型实例调用流式API
            stream = model._run(
                messages=messages
            )
            
            # 处理流式响应
            full_response = ""
            for chunk in stream:
                if not chunk.choices:
                    continue
                    
                # 获取内容块
                content_chunk = chunk.choices[0].delta.content or ""
                if content_chunk:
                    full_response += content_chunk
                    self.response_queue.put(content_chunk)
            
            # 将完整响应添加到代理的消息历史
            assistant_msg = BaseMessage.make_assistant_message(
                role_name="Assistant",
                content=full_response
            )
            self.agent.update_memory(user_msg, OpenAIBackendRole.USER)
            self.agent.update_memory(assistant_msg, OpenAIBackendRole.ASSISTANT)
                
        except Exception as e:
            self.response_queue.put(f"\n\nError: {str(e)}")
        finally:
            self.response_queue.put(None)  # 流结束信号
            self.is_streaming = False

    def process_queue(self):
        """主线程中处理队列内容（每100ms检查一次）"""
        try:
            while True:
                chunk = self.response_queue.get_nowait()
                if chunk is None:  # 流结束信号
                    self.update_response("\n\n", clear=False)
                    break
                    
                self.current_response += chunk
                self.update_response(chunk, clear=False)
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_queue)  # 继续循环

    def update_response(self, text, clear=False):
        """更新响应文本框内容"""
        self.ans_text.config(state=tk.NORMAL)  # 临时启用编辑
        
        if clear:
            self.ans_text.delete('1.0', tk.END)
            self.current_response = ""
        
        self.ans_text.insert(tk.END, text)
        self.ans_text.see(tk.END)  # 自动滚动到底部
        self.ans_text.config(state=tk.DISABLED)  # 恢复禁用状态
        
    def on_close(self):
        """处理窗口关闭事件"""
        if self.is_streaming:
            # 可以添加取消请求的逻辑
            pass
        self.root.destroy()

if __name__ == "__main__":
    agent = ChatAgent(system_msg, model=model)
    gui = GUI(agent)
    gui.root.mainloop()