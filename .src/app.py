# app.py
import tkinter as tk
import tkinter.font as font
import threading
import queue
from model_agent import create_chat_agent, get_system_messages, stream_response, detect_injection, sanitize_input
from camel.messages import BaseMessage
from camel.types import OpenAIBackendRole
import time

class GUI:
    def __init__(self, agent):
        self.root = tk.Tk()
        self.root.title("AIGC Inspector & Reducer")
        self.root.geometry("1280x960+30+30")
        self.interface()
        self.agent = agent
        self.system_msgs = get_system_messages()
        self.response_queue = queue.Queue()  # 用于线程间通信
        self.current_response = ""  # 当前累积的响应内容
        self.is_streaming = False  # 流式响应状态标志
        self.root.after(100, self.process_queue)  # 启动队列处理循环
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)  # 处理窗口关闭事件
        self.current_aigc_rate = ""  # 当前AIGC率
        self.current_reduce = ""  # 当前降低后的内容
        self.send_mod = False  # 标志位，表示是否处于发送状态
        self.reduce_mod = False  # 标志位，表示是否处于降低状态
        self.user_input = ""  # 存储用户输入
        self.security_log = []  # 安全日志记录

    def interface(self):
        """创建和布局GUI界面元素"""
        self.font_of_btn = font.Font(weight="bold")
        
        # 发送按钮
        self.send_btn = tk.Button(
            self.root,
            text="SEND",
            font=self.font_of_btn,
            bg="LightSkyBlue",
            command=self.send
        )
        self.send_btn.place(relx=0.9, rely=0.9, relwidth=0.05, relheight=0.05)
        
        # 降低按钮
        self.reduce_btn = tk.Button(
            self.root,
            text="REDUCE",
            font=self.font_of_btn,
            bg="LightCoral",
            command=self.reduce
        )
        self.reduce_btn.place(relx=0.85, rely=0.9, relwidth=0.05, relheight=0.05)
        
        # 输入文本框
        self.send_text = tk.Text(self.root, height=3)
        self.send_text.place(relx=0.05, rely=0.9, relheight=0.05, relwidth=0.75)
        
        # 响应文本框（带滚动条）
        self.ans_text = tk.Text(
            self.root, 
            state=tk.DISABLED,  # 初始为禁用状态
            wrap=tk.WORD,
            font=("Arial", 12)
        )
        self.ans_text.config(state=tk.NORMAL)
        self.ans_text.insert(tk.END, "AIGC Inspector & Reducer\n\n")
        self.ans_text.insert(tk.END, "功能说明：\n")
        self.ans_text.insert(tk.END, "1. 输入文本后点击SEND进行AI生成内容检测\n")
        self.ans_text.insert(tk.END, "2. 检测结果显示AIGC率(0-100)\n")
        self.ans_text.insert(tk.END, "3. 如果AIGC率>25%，可点击REDUCE降低AI生成内容比重\n\n")
        self.ans_text.config(state=tk.DISABLED)
        self.ans_text.place(relx=0.05, rely=0.05, relheight=0.8, relwidth=0.9)
        
        # 滚动条
        scrollbar = tk.Scrollbar(self.root, command=self.ans_text.yview)
        scrollbar.place(relx=0.95, rely=0.05, relheight=0.8, relwidth=0.02)
        self.ans_text.config(yscrollcommand=scrollbar.set)
        
        # 安全日志按钮
        self.security_btn = tk.Button(
            self.root,
            text="SECURE",
            font=self.font_of_btn,
            bg="LightSalmon",
            command=self.show_security_log
        )
        self.security_btn.place(relx=0.8, rely=0.9, relwidth=0.05, relheight=0.05)

    def send(self):
        """处理发送按钮点击事件，启动AIGC检测"""
        if self.is_streaming:
            return  # 防止在前一个响应完成前发送新请求
            
        user_input = self.send_text.get('1.0', 'end-1c').strip()  # 获取文本并移除首尾空白
        if not user_input:
            return
        # 检测指令注入
        if detect_injection(user_input):
            self.security_log.append(f"\n检测到潜在指令注入: {user_input[:50]}...")
            self.update_response("\n\n安全警报: 检测到可疑输入。已启动防护机制。\n", clear=False)
            # 清理输入内容
            user_input = sanitize_input(user_input)
            self.update_response(f"\n清理后输入: {user_input}\n\n", clear=False)
        
        self.user_input = user_input
        self.current_aigc_rate = ""
        self.send_text.delete('1.0', tk.END)  # 清空输入框
        self.is_streaming = True
        
        # 在文本框中添加用户消息
        self.root.after(0, lambda: self.update_response(f"\n\nYou: {self.user_input}\n\nAIGC_checker: ", clear=False))
        
        self.send_mod = True
        # 启动新线程处理流式响应
        threading.Thread(
            target=self.stream_response,
            args=(0,),
            daemon=True
        ).start()

    def reduce(self):
        """处理降低按钮点击事件，启动AIGC内容降低"""
        # 检查是否有有效的AIGC率
        if not self.current_aigc_rate.isdigit():
            self.update_response("\n\nAIGC_reducer: 请先进行AIGC检测\n", clear=False)
            return
            
        # 检查AIGC率是否低于25%
        if int(self.current_aigc_rate) < 25:
            self.update_response(f"\n\nAIGC_reducer: 当前AIGC率({self.current_aigc_rate}%)低于25%，无需降低。\n", clear=False)
            return
            
        if self.is_streaming:
            return
            
        self.is_streaming = True
        self.current_reduce = ""
        self.update_response(f"\n\nAIGC_reducer: 正在降低AIGC内容比重...\n", clear=False)
        
        self.reduce_mod = True
        threading.Thread(
            target=self.stream_response,
            args=(1,),
            daemon=True
        ).start()
        self.security_log.append(f"降低请求 - 原始AIGC率: {self.current_aigc_rate}%")

    def stream_response(self, mod=0):
        """在后台线程中处理流式响应"""
        try:
            # 创建用户消息
            user_msg = BaseMessage.make_user_message(role_name="User", content=self.user_input)
            
            system_msgs = get_system_messages()
            
            # 根据模式选择系统消息
            if mod == 0:  # 检测模式
                _system_msg = system_msgs["detector"]
            elif mod == 1:  # 降低模式
                _system_msg = system_msgs["reducer"]
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": _system_msg.content},
                {"role": "user", "content": user_msg.content}
            ]
            
            # 调用流式响应函数
            stream = stream_response(messages)
            
            # 处理流式响应
            full_response = ""
            for chunk in stream:
                # 将每个chunk放入队列
                self.response_queue.put(chunk)
                
                # 累积完整响应
                full_response += chunk
                
                # 在流处理过程中累积内容
                if self.send_mod:
                    self.current_aigc_rate += chunk
                if self.reduce_mod:
                    self.current_reduce += chunk
            # 记录安全日志
            self.security_log.append(f"模式{mod}响应: {full_response[:100]}{'...' if len(full_response)>100 else ''}")
            
            # 将完整响应添加到代理的消息历史
            assistant_msg = BaseMessage.make_assistant_message(
                role_name="Assistant",
                content=full_response
            )
            self.agent.update_memory(user_msg, OpenAIBackendRole.USER)
            self.agent.update_memory(assistant_msg, OpenAIBackendRole.ASSISTANT)
            
            # 如果是降低模式，完成后自动重新检测
            if self.reduce_mod:
                self.root.after(0, self.handle_reduce_completion, full_response)
            
        except Exception as e:
            self.response_queue.put(f"\n\nError: {str(e)}")
            self.security_log.append(f"错误: {str(e)}")
        finally:
            self.response_queue.put(None)  # 流结束信号
            self.send_mod = False
            self.reduce_mod = False
            self.is_streaming = False

    def handle_reduce_completion(self, reduced_content):
        """处理降低模式完成后的逻辑"""
        # 更新用户输入为降低后的内容
        self.user_input = reduced_content
        
        # 显示检测前缀
        while not queue.Empty:
            time.sleep(0.1)  # 等待队列处理完成
        time.sleep(0.1)
        self.update_response(f"\n\nAIGC_checker: ", clear=False)
        
        # 启动新检测
        self.send_mod = True
        self.is_streaming = True
        threading.Thread(
            target=self.stream_response,
            args=(0,),
            daemon=True
        ).start()

    def process_queue(self):
        """主线程中处理队列内容（每100ms检查一次）"""
        try:
            while True:
                chunk = self.response_queue.get_nowait()
                if chunk is None:  # 流结束信号
                    break
                self.current_response += chunk
                self.update_response(chunk, clear=False)
        except queue.Empty:
            pass
        
        self.root.after(50, self.process_queue)  # 继续循环

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

    def show_security_log(self):
        """显示安全日志（新增方法）"""
        log_window = tk.Toplevel(self.root)
        log_window.title("安全日志")
        log_window.geometry("800x600")
        
        log_text = tk.Text(log_window, wrap=tk.WORD)
        log_text.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        log_text.insert(tk.END, "=== 安全日志 ===\n\n")
        for entry in self.security_log:
            log_text.insert(tk.END, f"- {entry}\n")
        
        log_text.config(state=tk.DISABLED)
    
if __name__ == "__main__":
    agent = create_chat_agent()
    gui = GUI(agent)
    
    gui.root.mainloop()