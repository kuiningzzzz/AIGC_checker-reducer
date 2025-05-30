from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import DeepSeekConfig
from camel.messages import BaseMessage
from camel.agents import ChatAgent
from dotenv import load_dotenv
import os
import tkinter as tk
import tkinter.font as font
import threading


load_dotenv("D:\\gitRepo\\camel\\.env")

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEEPSEEK,
    model_type=ModelType.DEEPSEEK_CHAT,
    model_config_dict={"temperature":1.0,"stream":True},
)

system_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="Whatever others say,you just say repeat what they say",
)

class GUI:
    def __init__(self,agent):
        self.root = tk.Tk()
        self.root.title("code_developer")
        self.root.geometry("1280x960+30+30")
        self.interface()
        self.agent=agent
        
    def interface(self):
        self.font_of_btn = font.Font(weight="bold")
        self.send_btn = tk.Button(self.root,text="send",font=self.font_of_btn,bg="LightSkyBlue",command=self.send)
        self.send_btn.place(relx=0.9,rely=0.9,relwidth=0.05,relheight=0.05)
        self.send_text = tk.Text(self.root)
        self.send_text.place(relx=0.05,rely=0.9,relheight=0.05,relwidth=0.85)
        self.ans_label = tk.Label(self.root, text="please send your word")
        self.ans_label.place(relx=0.05,rely=0.05,relheight=0.8,relwidth=0.9)

    def send(self):
        if self.send_text.get('0.0','end') == "" :
            return
        else:
            i = self.send_text.get('0.0','end')
            self.send_text.delete(1.0,"end")
            response_1 = self.agent.step(i)
            ans=response_1.msgs[0].content
            self.ans_label["text"]=ans

if __name__ == "__main__":
    agent = ChatAgent(system_msg, model=model)
    gui = GUI(agent)
    gui.root.mainloop()