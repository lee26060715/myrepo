import tkinter as tk

def change_message():
    """
    버튼을 눌렀을 때 실행되는 함수입니다.
    message_label의 글자를 새로운 문장으로 바꿉니다.
    """
    message_label.config(text="버튼을 눌렀습니다!")

root = tk.Tk()

root.title("예제 1 - Tkinter 기본 화면")

root.geometry("500x300")

title_label = tk.Label(
    root,
    text="교과 7 Tkinter 첫 번째 실습",
    font=("Arial", 18)
)
title_label.pack(pady=30)

message_label = tk.Label(
    root,
    text="아래 버튼을 눌러보세요.",
    font=("Arial", 12)
)
message_label.pack(pady=10)









root.mainloop()