import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
 
from PIL import Image, ImageTk   # tk.PhotoImage는 크기 조절이 안 돼서 Pillow를 사용합니다.
 
 
# --------------------------------------------------
# 0. 설정값 (상수)
# --------------------------------------------------
 
CLASS_NAMES  = ["plastic", "can", "glass", "paper"]   # Class 목록 (순서 = class_id)
CLASS_COLORS = ["red", "blue", "green", "orange"]     # Class별 BBox 색
 
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")
 
CANVAS_W = 800
CANVAS_H = 500
 
MIN_BOX_SIZE = 5   # 이보다 작은 BBox는 실수 클릭으로 보고 무시합니다. (Canvas 픽셀 기준)
 
 
# --------------------------------------------------
# 1. YOLO 좌표 변환 함수 (GUI와 상관없는 순수 계산)
# --------------------------------------------------
 
def bbox_to_yolo(x1, y1, x2, y2, img_w, img_h):
    """
    픽셀 좌표 (x1, y1, x2, y2)  →  YOLO 좌표 (x_center, y_center, width, height)
 
    YOLO는 모든 값을 이미지 크기로 나눠서 0~1 사이로 저장합니다.
    그래서 이미지 크기가 바뀌어도 라벨을 그대로 쓸 수 있어요.
    """
    x_center = (x1 + x2) / 2 / img_w
    y_center = (y1 + y2) / 2 / img_h
    width    = (x2 - x1) / img_w
    height   = (y2 - y1) / img_h
    return x_center, y_center, width, height
 
 
def yolo_to_bbox(x_center, y_center, width, height, img_w, img_h):
    """
    YOLO 좌표  →  픽셀 좌표 (x1, y1, x2, y2)
    저장된 라벨을 다시 불러올 때 사용합니다. (bbox_to_yolo의 역방향)
    """
    x1 = (x_center - width / 2) * img_w
    y1 = (y_center - height / 2) * img_h
    x2 = (x_center + width / 2) * img_w
    y2 = (y_center + height / 2) * img_h
    return x1, y1, x2, y2
 
 
def get_class_name(class_id):
    """목록에 없는 class_id가 들어와도 프로그램이 죽지 않도록 처리합니다."""
    if 0 <= class_id < len(CLASS_NAMES):
        return CLASS_NAMES[class_id]
    return f"class{class_id}"
 
 
def get_class_color(class_id):
    if 0 <= class_id < len(CLASS_COLORS):
        return CLASS_COLORS[class_id]
    return "gray"
 
 
# --------------------------------------------------
# 2. 라벨링 툴 클래스
# --------------------------------------------------
 
class MiniLabelingTool:
    """
    예제 3에서는 global 변수를 썼지만,
    변수가 많아지면 관리가 어려워서 class 하나에 모았습니다.
 
    self.xxx  =  C++ 클래스의 멤버 변수 (this->xxx)
    """
 
    def __init__(self, root):
        self.root = root
        self.root.title("Mini Labeling Tool")
        self.root.geometry("860x680")
 
        # ---------- 이미지 관련 상태 ----------
        self.folder = None          # 선택한 이미지 폴더 경로
        self.image_paths = []       # 폴더 안 이미지 파일 경로 목록
        self.index = 0              # 지금 보고 있는 이미지 번호
 
        self.img_w = 0              # 원본 이미지 크기
        self.img_h = 0
        self.scale = 1.0            # 원본 → 화면 축소 비율
        self.offset_x = 0           # 이미지를 Canvas 가운데 놓기 위한 여백
        self.offset_y = 0
        self.disp_w = 0             # 화면에 표시된 이미지 크기
        self.disp_h = 0
 
        self.tk_image = None        # ⚠️ PhotoImage 참조를 꼭 붙잡아 둬야 이미지가 안 사라집니다.
 
        # ---------- BBox 관련 상태 ----------
        # 각 BBox는 dict 하나:
        # {"class_id": 0, "x1":.., "y1":.., "x2":.., "y2":.., "rect_id":.., "text_id":..}
        # 좌표는 "원본 이미지 픽셀" 기준으로 저장합니다. (화면 좌표 X)
        self.boxes = []
 
        self.start_x = 0            # 드래그 시작점 (Canvas 좌표)
        self.start_y = 0
        self.temp_rect = None       # 드래그 중 보여주는 임시 사각형
 
        self.dirty = False          # 저장 안 된 변경이 있는지 (True면 이동 시 자동 저장)
 
        self.build_ui()
        self.bind_events()
 
    # ==================================================
    # 2-1. 화면 구성 (pack + Frame)
    # ==================================================
 
    def build_ui(self):
        # ---------- 위쪽 줄: [폴더 열기] Image: xxx.jpg [이전] [다음] ----------
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=10)
 
        tk.Button(top_frame, text="📂 폴더 열기", command=self.open_folder).pack(side="left")
 
        self.file_label = tk.Label(top_frame, text="Image: (폴더를 열어주세요)", font=("Arial", 12))
        self.file_label.pack(side="left", padx=15)
 
        # side="right"는 오른쪽부터 쌓이므로 [다음]을 먼저 pack 해야 [이전][다음] 순서가 됩니다.
        tk.Button(top_frame, text="다음 ▶", width=8, command=self.next_image).pack(side="right")
        tk.Button(top_frame, text="◀ 이전", width=8, command=self.prev_image).pack(side="right", padx=5)
 
        # ---------- 가운데: 이미지 Canvas ----------
        self.canvas = tk.Canvas(self.root, width=CANVAS_W, height=CANVAS_H,
                                bg="#333333", cursor="crosshair")
        self.canvas.pack(padx=10)
 
        # ---------- 아래쪽 줄: Class: [plastic ▼] [BBox 삭제] [Label 저장] ----------
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill="x", padx=10, pady=10)
 
        tk.Label(bottom_frame, text="Class:", font=("Arial", 11)).pack(side="left")
 
        # ttk.Combobox = 드롭다운 목록. readonly라서 목록에 있는 값만 고를 수 있어요.
        self.class_combo = ttk.Combobox(bottom_frame, values=CLASS_NAMES,
                                        state="readonly", width=12)
        self.class_combo.current(0)     # 처음엔 0번(plastic) 선택
        self.class_combo.pack(side="left", padx=5)
 
        tk.Button(bottom_frame, text="BBox 삭제", width=10,
                  command=self.delete_last_box).pack(side="left", padx=10)
        tk.Button(bottom_frame, text="Label 저장", width=10,
                  command=self.save_labels).pack(side="left")
 
        # ---------- 맨 아래: 상태 메시지 ----------
        self.status_label = tk.Label(self.root, text="📂 폴더 열기 버튼으로 시작하세요.",
                                     anchor="w", fg="#555555")
        self.status_label.pack(fill="x", padx=10)
 
    def bind_events(self):
        # 마우스 (예제 3과 동일한 3단계)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
 
        # 키보드 단축키 (bind로 연결된 함수는 event를 받기 때문에 lambda로 감싸줍니다)
        self.root.bind("<a>", lambda e: self.prev_image())
        self.root.bind("<d>", lambda e: self.next_image())
        self.root.bind("<Control-s>", lambda e: self.save_labels())
        self.root.bind("<Control-z>", lambda e: self.delete_last_box())
 
        # 창 닫기(X) 버튼을 눌렀을 때 저장 안 된 작업이 있으면 물어봅니다.
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
 
    def set_status(self, text):
        self.status_label.config(text=text)
 
    # ==================================================
    # 2-2. 이미지 폴더 열기 & 이미지 표시
    # ==================================================
 
    def open_folder(self):
        folder = filedialog.askdirectory(title="이미지 폴더 선택")
        if not folder:                      # 취소를 누르면 빈 문자열이 돌아옵니다.
            return
 
        # 폴더 안 파일 중 이미지 확장자만 골라서 이름순 정렬
        files = sorted(
            f for f in os.listdir(folder)
            if f.lower().endswith(IMAGE_EXTENSIONS)
        )
 
        if not files:
            messagebox.showwarning("이미지 없음", "선택한 폴더에 이미지 파일이 없습니다.")
            return
 
        self.folder = folder
        self.image_paths = [os.path.join(folder, f) for f in files]
        self.index = 0
        self.load_image()
 
    def load_image(self):
        path = self.image_paths[self.index]
 
        # ---------- 1) 원본 이미지 열기 ----------
        img = Image.open(path).convert("RGB")
        self.img_w, self.img_h = img.size
 
        # ---------- 2) Canvas에 들어가도록 비율 유지하며 축소 ----------
        # 가로 비율, 세로 비율 중 더 작은 쪽에 맞추면 이미지가 잘리지 않습니다.
        self.scale = min(CANVAS_W / self.img_w, CANVAS_H / self.img_h)
        self.disp_w = int(self.img_w * self.scale)
        self.disp_h = int(self.img_h * self.scale)
 
        resized = img.resize((self.disp_w, self.disp_h))
        self.tk_image = ImageTk.PhotoImage(resized)   # self에 저장해야 화면에서 안 사라짐!
 
        # ---------- 3) 가운데 정렬용 여백 계산 ----------
        self.offset_x = (CANVAS_W - self.disp_w) // 2
        self.offset_y = (CANVAS_H - self.disp_h) // 2
 
        # ---------- 4) Canvas 초기화 후 이미지 그리기 ----------
        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y,
                                 anchor="nw", image=self.tk_image)
 
        # ---------- 5) 상태 초기화 & 저장된 라벨 불러오기 ----------
        self.boxes = []
        self.temp_rect = None
        self.load_labels()
        self.dirty = False
 
        name = os.path.basename(path)
        self.file_label.config(
            text=f"Image: {name}   ({self.index + 1}/{len(self.image_paths)})"
        )
        self.set_status(f"{name} 열기 완료  |  원본 {self.img_w}x{self.img_h}  |  "
                        f"BBox {len(self.boxes)}개")
 
    # ==================================================
    # 2-3. 좌표 변환: 화면(Canvas) ↔ 원본 이미지
    # ==================================================
    #
    #   Canvas 좌표 = 원본 좌표 × scale + offset
    #   원본 좌표   = (Canvas 좌표 − offset) ÷ scale
    #
    # 화면은 축소된 그림이라서, 저장할 땐 꼭 원본 좌표로 바꿔야 합니다.
 
    def canvas_to_image(self, cx, cy):
        return (cx - self.offset_x) / self.scale, (cy - self.offset_y) / self.scale
 
    def image_to_canvas(self, ix, iy):
        return ix * self.scale + self.offset_x, iy * self.scale + self.offset_y
 
    def clamp_to_image(self, cx, cy):
        """마우스가 이미지 밖으로 나가도 좌표를 이미지 테두리 안으로 붙잡아 둡니다."""
        cx = max(self.offset_x, min(cx, self.offset_x + self.disp_w))
        cy = max(self.offset_y, min(cy, self.offset_y + self.disp_h))
        return cx, cy
 
    # ==================================================
    # 2-4. 마우스로 BBox 그리기 (예제 3 확장판)
    # ==================================================
 
    def on_mouse_down(self, event):
        if not self.image_paths:            # 이미지가 없으면 아무것도 안 함
            return
 
        self.start_x, self.start_y = self.clamp_to_image(event.x, event.y)
 
        color = get_class_color(self.class_combo.current())
        self.temp_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline=color, width=2, dash=(4, 2)     # 그리는 중엔 점선
        )
 
    def on_mouse_drag(self, event):
        if self.temp_rect is None:
            return
        cx, cy = self.clamp_to_image(event.x, event.y)
        self.canvas.coords(self.temp_rect, self.start_x, self.start_y, cx, cy)
 
    def on_mouse_up(self, event):
        if self.temp_rect is None:
            return
 
        end_x, end_y = self.clamp_to_image(event.x, event.y)
 
        # 임시 점선 사각형은 지우고, 확정 BBox를 새로 그립니다.
        self.canvas.delete(self.temp_rect)
        self.temp_rect = None
 
        # 어느 방향으로 드래그해도 (왼쪽 위, 오른쪽 아래)로 정리
        x1, x2 = min(self.start_x, end_x), max(self.start_x, end_x)
        y1, y2 = min(self.start_y, end_y), max(self.start_y, end_y)
 
        if (x2 - x1) < MIN_BOX_SIZE or (y2 - y1) < MIN_BOX_SIZE:
            self.set_status("BBox가 너무 작아서 무시했습니다.")
            return
 
        # 화면 좌표 → 원본 이미지 좌표로 변환해서 저장
        ix1, iy1 = self.canvas_to_image(x1, y1)
        ix2, iy2 = self.canvas_to_image(x2, y2)
 
        class_id = self.class_combo.current()
        self.add_box(class_id, ix1, iy1, ix2, iy2)
        self.dirty = True
 
        self.set_status(
            f"[{get_class_name(class_id)}] 원본 좌표 ({ix1:.0f}, {iy1:.0f}) ~ "
            f"({ix2:.0f}, {iy2:.0f})  |  BBox {len(self.boxes)}개  |  * 저장 안 됨"
        )
 
    def add_box(self, class_id, x1, y1, x2, y2):
        """BBox 하나를 목록에 추가하고 Canvas에 그립니다. (그리기 / 불러오기 공용)"""
        color = get_class_color(class_id)
        cx1, cy1 = self.image_to_canvas(x1, y1)
        cx2, cy2 = self.image_to_canvas(x2, y2)
 
        rect_id = self.canvas.create_rectangle(cx1, cy1, cx2, cy2, outline=color, width=2)
        text_id = self.canvas.create_text(
            cx1 + 3, cy1 + 2, anchor="nw",
            text=get_class_name(class_id), fill=color, font=("Arial", 10, "bold")
        )
 
        self.boxes.append({
            "class_id": class_id,
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "rect_id": rect_id, "text_id": text_id,
        })
 
    def delete_last_box(self):
        if not self.boxes:
            self.set_status("삭제할 BBox가 없습니다.")
            return
 
        box = self.boxes.pop()                 # 마지막에 그린 BBox를 목록에서 꺼냄
        self.canvas.delete(box["rect_id"])     # 화면에서도 지움
        self.canvas.delete(box["text_id"])
        self.dirty = True
        self.set_status(f"마지막 BBox 삭제  |  남은 BBox {len(self.boxes)}개  |  * 저장 안 됨")
 
    # ==================================================
    # 2-5. YOLO TXT 저장 & 불러오기
    # ==================================================
 
    def get_label_path(self):
        """images/sample_001.jpg  →  images/labels/sample_001.txt"""
        image_name = os.path.basename(self.image_paths[self.index])
        stem = os.path.splitext(image_name)[0]          # 확장자 떼기
        return os.path.join(self.folder, "labels", stem + ".txt")
 
    def save_labels(self):
        if not self.image_paths:
            return
 
        label_path = self.get_label_path()
        os.makedirs(os.path.dirname(label_path), exist_ok=True)   # labels 폴더 없으면 생성
 
        with open(label_path, "w", encoding="utf-8") as f:
            for box in self.boxes:
                xc, yc, w, h = bbox_to_yolo(box["x1"], box["y1"], box["x2"], box["y2"],
                                            self.img_w, self.img_h)
                # YOLO 한 줄 형식:  class_id x_center y_center width height
                f.write(f"{box['class_id']} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")
 
        self.dirty = False
        self.set_status(f"💾 저장 완료: labels/{os.path.basename(label_path)}  "
                        f"(BBox {len(self.boxes)}개)")
 
    def load_labels(self):
        label_path = self.get_label_path()
        if not os.path.exists(label_path):     # 아직 라벨이 없는 이미지
            return
 
        with open(label_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                parts = line.split()
                if len(parts) != 5:            # 빈 줄이나 잘못된 줄은 건너뜀
                    continue
                try:
                    class_id = int(parts[0])
                    xc, yc, w, h = map(float, parts[1:])
                except ValueError:
                    print(f"[경고] {label_path} {line_no}번째 줄 형식 오류 → 건너뜀")
                    continue
 
                x1, y1, x2, y2 = yolo_to_bbox(xc, yc, w, h, self.img_w, self.img_h)
                self.add_box(class_id, x1, y1, x2, y2)
 
    # ==================================================
    # 2-6. 이전 · 다음 이미지
    # ==================================================
 
    def move_to(self, new_index):
        if not self.image_paths:
            return
        if not (0 <= new_index < len(self.image_paths)):
            self.set_status("첫 번째 이미지입니다." if new_index < 0 else "마지막 이미지입니다.")
            return
 
        if self.dirty:                         # 바꾼 내용이 있으면 자동 저장 후 이동
            self.save_labels()
 
        self.index = new_index
        self.load_image()
 
    def prev_image(self):
        self.move_to(self.index - 1)
 
    def next_image(self):
        self.move_to(self.index + 1)
 
    # ==================================================
    # 2-7. 종료
    # ==================================================
 
    def on_close(self):
        if self.dirty:
            answer = messagebox.askyesnocancel("저장", "저장하지 않은 BBox가 있습니다. 저장할까요?")
            if answer is None:                 # 취소 → 창 닫기 취소
                return
            if answer:                         # 예 → 저장 후 종료
                self.save_labels()
        self.root.destroy()


# --------------------------------------------------
# 3. 프로그램 실행
# --------------------------------------------------
 
if __name__ == "__main__":
    root = tk.Tk()
    app = MiniLabelingTool(root)
    root.mainloop()