# ============================================================
# 기본 설정
# ============================================================

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import csv


root = tk.Tk()
root.title("GUI 라벨링 프로그램")
root.geometry("1200x800")


# ============================================================
# 데이터
# ============================================================

image_folder = ""
image_files = []
current_index = 0

original_image = None
photo_image = None

zoom = 1.0
image_x = 0
image_y = 0

pan_start_x = 0
pan_start_y = 0

boxes = []

selected_box = None
drawing_box = None

draw_start_x = 0
draw_start_y = 0

current_class = 0

modified = False

undo_stack = []

image_status = "REVIEW"

worker_name = ""
reviewer_name = ""

scene_type = "normal"


# ============================================================
# 클래스
# ============================================================

CLASS_NAMES = {
    0: "kimchi",
    1: "target",
    2: "object"
}

CLASS_COLORS = {
    0: "red",
    1: "blue",
    2: "green"
}


# ============================================================
# 이미지 표시
# ============================================================

def show_image():

    global photo_image

    if original_image is None:
        return

    width = int(original_image.width * zoom)
    height = int(original_image.height * zoom)

    if width <= 0 or height <= 0:
        return

    resized = original_image.resize(
        (width, height)
    )

    photo_image = ImageTk.PhotoImage(resized)

    canvas.delete("all")

    canvas.create_image(
        image_x,
        image_y,
        image=photo_image,
        anchor="nw",
        tags="image"
    )

    draw_boxes()


# ============================================================
# BBox 표시
# ============================================================

def draw_boxes():

    canvas.delete("bbox")

    for i, box in enumerate(boxes):

        x1 = image_x + box["x1"] * zoom
        y1 = image_y + box["y1"] * zoom

        x2 = image_x + box["x2"] * zoom
        y2 = image_y + box["y2"] * zoom

        color = CLASS_COLORS.get(
            box["class_id"],
            "yellow"
        )

        if i == selected_box:
            line_width = 4
        else:
            line_width = 2

        canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline=color,
            width=line_width,
            tags="bbox"
        )

        class_name = CLASS_NAMES.get(
            box["class_id"],
            str(box["class_id"])
        )

        canvas.create_text(
            x1 + 5,
            y1 + 5,
            text=class_name,
            fill=color,
            anchor="nw",
            tags="bbox"
        )


# ============================================================
# 이미지 열기
# ============================================================

def open_image():

    global original_image
    global image_folder
    global image_files
    global current_index
    global zoom
    global image_x
    global image_y
    global boxes
    global selected_box
    global modified
    global undo_stack

    file_path = filedialog.askopenfilename(
        title="이미지 선택",
        filetypes=[
            (
                "Image files",
                "*.jpg *.jpeg *.png"
            ),
            (
                "All files",
                "*.*"
            )
        ]
    )

    if not file_path:
        return

    if modified:

        answer = messagebox.askyesnocancel(
            "저장되지 않은 변경사항",
            "현재 이미지에 저장되지 않은 변경사항이 있습니다.\n"
            "저장할까요?"
        )

        if answer is None:
            return

        if answer:

            if not save_current():
                return

    image_folder = os.path.dirname(file_path)

    image_files = [
        os.path.basename(file_path)
    ]

    current_index = 0

    original_image = Image.open(
        file_path
    )

    zoom = 1.0

    image_x = 0
    image_y = 0

    boxes = []

    selected_box = None

    undo_stack = []

    modified = False

    load_yolo_file()

    update_info()

    show_image()

    load_csv_status()


# ============================================================
# 폴더 선택
# ============================================================

def select_folder():

    global image_folder
    global image_files
    global current_index

    folder_path = filedialog.askdirectory(
        title="이미지 폴더 선택"
    )

    if not folder_path:
        return

    image_folder = folder_path

    image_files = get_filtered_files()

    if not image_files:

        messagebox.showinfo(
            "알림",
            "조건에 맞는 이미지가 없습니다."
        )

        return

    current_index = 0

    load_current_image()


# ============================================================
# 현재 이미지 불러오기
# ============================================================

def load_current_image():

    global original_image
    global zoom
    global image_x
    global image_y
    global boxes
    global selected_box
    global modified
    global undo_stack
    global image_status

    if not image_files:
        return

    file_path = os.path.join(
        image_folder,
        image_files[current_index]
    )

    original_image = Image.open(
        file_path
    )

    zoom = 1.0

    image_x = 0
    image_y = 0

    boxes = []

    selected_box = None

    undo_stack = []

    modified = False

    image_status = "REVIEW"

    status_var.set(
        "REVIEW"
    )

    worker_var.set("")
    reviewer_var.set("")
    scene_type_var.set("normal")

    note_text.delete(
        "1.0",
        "end"
    )

    load_yolo_file()

    load_csv_status()

    update_info()

    show_image()


# ============================================================
# 정보 표시
# ============================================================

def update_info():

    if not image_files:

        filename_label.config(
            text="파일명: 없음"
        )

        count_label.config(
            text="0 / 0"
        )

        return

    filename_label.config(
        text="파일명: "
        + image_files[current_index]
    )

    count_label.config(
        text=f"{current_index + 1} / {len(image_files)}"
    )


# ============================================================
# 이전 이미지
# ============================================================

def previous_image():

    global current_index

    if not image_files:
        return

    if modified:

        answer = messagebox.askyesnocancel(
            "저장되지 않은 변경사항",
            "현재 변경사항을 저장할까요?"
        )

        if answer is None:
            return

        if answer:

            if not save_current():
                return

    if current_index > 0:

        current_index -= 1

        load_current_image()


# ============================================================
# 다음 이미지
# ============================================================

def next_image():

    global current_index

    if not image_files:
        return

    if modified:

        answer = messagebox.askyesnocancel(
            "저장되지 않은 변경사항",
            "현재 변경사항을 저장할까요?"
        )

        if answer is None:
            return

        if answer:

            if not save_current():
                return

    if current_index < len(image_files) - 1:

        current_index += 1

        load_current_image()


# ============================================================
# 확대
# ============================================================

def zoom_in():

    global zoom

    zoom *= 1.2

    show_image()


# ============================================================
# 축소
# ============================================================

def zoom_out():

    global zoom

    zoom /= 1.2

    if zoom < 0.1:
        zoom = 0.1

    show_image()


# ============================================================
# 화면 맞추기
# ============================================================

def fit_image():

    global zoom
    global image_x
    global image_y

    if original_image is None:
        return

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    if canvas_width <= 1 or canvas_height <= 1:
        return

    scale_x = (
        canvas_width
        / original_image.width
    )

    scale_y = (
        canvas_height
        / original_image.height
    )

    zoom = min(
        scale_x,
        scale_y
    )

    new_width = int(
        original_image.width * zoom
    )

    new_height = int(
        original_image.height * zoom
    )

    image_x = (
        canvas_width - new_width
    ) // 2

    image_y = (
        canvas_height - new_height
    ) // 2

    show_image()


# ============================================================
# Pan 시작
# ============================================================

def pan_start(event):

    global pan_start_x
    global pan_start_y

    pan_start_x = event.x
    pan_start_y = event.y


# ============================================================
# Pan 이동
# ============================================================

def pan_move(event):

    global image_x
    global image_y
    global pan_start_x
    global pan_start_y

    dx = event.x - pan_start_x
    dy = event.y - pan_start_y

    image_x += dx
    image_y += dy

    pan_start_x = event.x
    pan_start_y = event.y

    show_image()


# ============================================================
# 화면 좌표 → 이미지 좌표
# ============================================================

def canvas_to_image(x, y):

    image_x_pos = (
        x - image_x
    ) / zoom

    image_y_pos = (
        y - image_y
    ) / zoom

    return (
        image_x_pos,
        image_y_pos
    )


# ============================================================
# BBox 시작
# ============================================================

def bbox_start(event):

    global draw_start_x
    global draw_start_y
    global drawing_box

    if original_image is None:
        return

    x, y = canvas_to_image(
        event.x,
        event.y
    )

    draw_start_x = x
    draw_start_y = y

    drawing_box = canvas.create_rectangle(
        event.x,
        event.y,
        event.x,
        event.y,
        outline="yellow",
        width=2,
        tags="drawing"
    )


# ============================================================
# BBox 이동
# ============================================================

def bbox_move(event):

    if drawing_box is None:
        return

    canvas.coords(
        drawing_box,

        draw_start_x * zoom
        + image_x,

        draw_start_y * zoom
        + image_y,

        event.x,
        event.y
    )


# ============================================================
# BBox 완성
# ============================================================

def bbox_end(event):

    global drawing_box
    global modified

    if drawing_box is None:
        return

    if original_image is None:
        return

    x1, y1 = canvas_to_image(
        draw_start_x * zoom + image_x,
        draw_start_y * zoom + image_y
    )

    x2, y2 = canvas_to_image(
        event.x,
        event.y
    )

    x1 = max(
        0,
        min(x1, original_image.width)
    )

    x2 = max(
        0,
        min(x2, original_image.width)
    )

    y1 = max(
        0,
        min(y1, original_image.height)
    )

    y2 = max(
        0,
        min(y2, original_image.height)
    )

    if (
        abs(x2 - x1) > 5
        and
        abs(y2 - y1) > 5
    ):

        undo_stack.append(
            [box.copy() for box in boxes]
        )

        boxes.append({

            "class_id": current_class,

            "x1": min(x1, x2),
            "y1": min(y1, y2),

            "x2": max(x1, x2),
            "y2": max(y1, y2)
        })

        modified = True

    canvas.delete(
        "drawing"
    )

    drawing_box = None

    show_image()


# ============================================================
# BBox 선택
# ============================================================

def select_box(event):

    global selected_box
    global current_class

    if original_image is None:
        return

    x, y = canvas_to_image(
        event.x,
        event.y
    )

    selected_box = None

    for i in range(
        len(boxes) - 1,
        -1,
        -1
    ):

        box = boxes[i]

        if (
            box["x1"] <= x <= box["x2"]
            and
            box["y1"] <= y <= box["y2"]
        ):

            selected_box = i

            current_class = box["class_id"]

            current_class_var.set(
                str(box["class_id"])
            )

            break

    show_image()


# ============================================================
# BBox 삭제
# ============================================================

def delete_box():

    global selected_box
    global modified

    if selected_box is None:
        return

    undo_stack.append(
        [box.copy() for box in boxes]
    )

    del boxes[selected_box]

    selected_box = None

    modified = True

    show_image()


# ============================================================
# 클래스 변경
# ============================================================

def change_class():

    global modified
    global current_class

    if selected_box is None:
        return

    undo_stack.append(
        [box.copy() for box in boxes]
    )

    new_class = int(
        current_class_var.get()
    )

    boxes[selected_box][
        "class_id"
    ] = new_class

    current_class = new_class

    modified = True

    show_image()


# ============================================================
# 클래스 선택
# ============================================================

def class_changed(event=None):

    global current_class

    try:
        current_class = int(
            current_class_var.get()
        )

    except ValueError:
        current_class = 0


# ============================================================
# Undo
# ============================================================

def undo():

    global boxes
    global selected_box
    global modified

    if not undo_stack:
        return

    boxes = undo_stack.pop()

    selected_box = None

    modified = True

    show_image()


# ============================================================
# YOLO TXT 읽기
# ============================================================

def load_yolo_file():

    global boxes

    if original_image is None:
        return

    image_name = image_files[
        current_index
    ]

    base_name = os.path.splitext(
        image_name
    )[0]

    txt_path = os.path.join(
        image_folder,
        base_name + ".txt"
    )

    if not os.path.exists(
        txt_path
    ):
        return

    try:

        image_width = original_image.width
        image_height = original_image.height

        with open(
            txt_path,
            "r",
            encoding="utf-8"
        ) as file:

            for line in file:

                parts = line.strip().split()

                if len(parts) != 5:
                    continue

                class_id = int(
                    parts[0]
                )

                cx = float(
                    parts[1]
                )

                cy = float(
                    parts[2]
                )

                w = float(
                    parts[3]
                )

                h = float(
                    parts[4]
                )

                x1 = (
                    cx - w / 2
                ) * image_width

                y1 = (
                    cy - h / 2
                ) * image_height

                x2 = (
                    cx + w / 2
                ) * image_width

                y2 = (
                    cy + h / 2
                ) * image_height

                boxes.append({

                    "class_id": class_id,

                    "x1": x1,
                    "y1": y1,

                    "x2": x2,
                    "y2": y2
                })

    except Exception as e:

        messagebox.showerror(
            "TXT 오류",
            str(e)
        )


# ============================================================
# YOLO TXT 저장
# ============================================================

def save_yolo():

    if original_image is None:
        return False

    image_name = image_files[
        current_index
    ]

    base_name = os.path.splitext(
        image_name
    )[0]

    txt_path = os.path.join(
        image_folder,
        base_name + ".txt"
    )

    width = original_image.width
    height = original_image.height

    try:

        with open(
            txt_path,
            "w",
            encoding="utf-8"
        ) as file:

            for box in boxes:

                x1 = box["x1"]
                y1 = box["y1"]

                x2 = box["x2"]
                y2 = box["y2"]

                cx = (
                    (x1 + x2) / 2
                ) / width

                cy = (
                    (y1 + y2) / 2
                ) / height

                w = (
                    x2 - x1
                ) / width

                h = (
                    y2 - y1
                ) / height

                file.write(
                    f'{box["class_id"]} '
                    f'{cx:.6f} '
                    f'{cy:.6f} '
                    f'{w:.6f} '
                    f'{h:.6f}\n'
                )

        return True

    except Exception as e:

        messagebox.showerror(
            "저장 오류",
            str(e)
        )

        return False


# ============================================================
# CSV 경로
# ============================================================

def csv_path():

    return os.path.join(
        image_folder,
        "label_status.csv"
    )


# ============================================================
# CSV 저장
# ============================================================

def save_csv_status():

    if not image_folder:
        return

    path = csv_path()

    rows = {}

    if os.path.exists(path):

        try:

            with open(
                path,
                "r",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                reader = csv.DictReader(
                    file
                )

                for row in reader:

                    rows[
                        row["filename"]
                    ] = row

        except Exception:
            pass

    filename = image_files[
        current_index
    ]

    rows[filename] = {

        "filename": filename,

        "status":
            image_status,

        "worker":
            worker_var.get(),

        "reviewer":
            reviewer_var.get(),

        "scene_type":
            scene_type_var.get(),

        "note":
            note_text
            .get(
                "1.0",
                "end"
            )
            .strip()
    }

    with open(
        path,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        fieldnames = [

            "filename",

            "status",

            "worker",

            "reviewer",

            "scene_type",

            "note"
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for row in rows.values():

            writer.writerow(row)


# ============================================================
# CSV 상태 읽기
# ============================================================

def load_csv_status():

    global image_status

    if not image_folder:
        return

    path = csv_path()

    if not os.path.exists(path):
        return

    filename = image_files[
        current_index
    ]

    try:

        with open(
            path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(
                file
            )

            for row in reader:

                if row["filename"] == filename:

                    image_status = row[
                        "status"
                    ]

                    status_var.set(
                        image_status
                    )

                    worker_var.set(
                        row["worker"]
                    )

                    reviewer_var.set(
                        row["reviewer"]
                    )

                    scene_type_var.set(
                        row["scene_type"]
                    )

                    note_text.delete(
                        "1.0",
                        "end"
                    )

                    note_text.insert(
                        "1.0",
                        row["note"]
                    )

                    break

    except Exception:
        pass


# ============================================================
# 상태 변경
# ============================================================

def set_status(status):

    global image_status
    global modified

    image_status = status

    status_var.set(
        status
    )

    modified = True


# ============================================================
# 전체 저장
# ============================================================

def save_current():

    global modified

    if original_image is None:
        return False

    if not validate_labels():
        return False

    if not save_yolo():
        return False

    save_csv_status()

    modified = False

    return True


# ============================================================
# 저장 후 다음
# ============================================================

def save_and_next():

    if save_current():

        if (
            current_index
            <
            len(image_files) - 1
        ):

            next_image()


# ============================================================
# 라벨 검증
# ============================================================

def validate_labels():

    if original_image is None:
        return False

    width = original_image.width
    height = original_image.height

    for i, box in enumerate(boxes):

        class_id = box[
            "class_id"
        ]

        # 클래스 검사
        if class_id < 0:

            messagebox.showerror(
                "검증 오류",
                f"{i + 1}번 BBox의 "
                "클래스가 잘못되었습니다."
            )

            return False

        x1 = box["x1"]
        y1 = box["y1"]

        x2 = box["x2"]
        y2 = box["y2"]

        # 이미지 밖 검사
        if x1 < 0 or y1 < 0:

            messagebox.showerror(
                "검증 오류",
                f"{i + 1}번 BBox가 "
                "이미지 범위를 벗어났습니다."
            )

            return False

        if x2 > width or y2 > height:

            messagebox.showerror(
                "검증 오류",
                f"{i + 1}번 BBox가 "
                "이미지 범위를 벗어났습니다."
            )

            return False

        # 크기 검사
        if (
            x1 >= x2
            or
            y1 >= y2
        ):

            messagebox.showerror(
                "검증 오류",
                f"{i + 1}번 BBox 크기가 "
                "잘못되었습니다."
            )

            return False

    return True


# ============================================================
# 변경 감지
# ============================================================

def data_changed(*args):

    global modified

    modified = True


# ============================================================
# 필터용 이미지 목록
# ============================================================

def get_filtered_files():

    if not image_folder:
        return []

    all_files = [

        file

        for file in os.listdir(
            image_folder
        )

        if file.lower().endswith(
            (
                ".jpg",
                ".jpeg",
                ".png"
            )
        )
    ]

    all_files.sort()

    selected_filter = filter_var.get()

    if selected_filter == "전체":

        return all_files

    path = csv_path()

    if not os.path.exists(path):

        return []

    status_map = {}

    try:

        with open(
            path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(
                file
            )

            for row in reader:

                status_map[
                    row["filename"]
                ] = row["status"]

    except Exception:

        return []

    return [

        file

        for file in all_files

        if status_map.get(file)
        == selected_filter
    ]


# ============================================================
# 필터 적용
# ============================================================

def apply_filter():

    global image_files
    global current_index

    if not image_folder:
        return

    if modified:

        answer = messagebox.askyesnocancel(
            "저장되지 않은 변경사항",
            "현재 변경사항을 저장할까요?"
        )

        if answer is None:
            return

        if answer:

            if not save_current():
                return

    image_files = get_filtered_files()

    current_index = 0

    if not image_files:

        messagebox.showinfo(
            "알림",
            "조건에 맞는 이미지가 없습니다."
        )

        update_info()

        canvas.delete("all")

        return

    load_current_image()


# ============================================================
# 프로그램 종료
# ============================================================

def close_program():

    if modified:

        answer = messagebox.askyesnocancel(
            "종료",
            "저장되지 않은 변경사항이 있습니다.\n"
            "저장할까요?"
        )

        if answer is None:
            return

        if answer:

            if not save_current():
                return

    root.destroy()


# ============================================================
# 마우스 통합 이벤트
# ============================================================

def mouse_press(event):

    # Ctrl + 클릭 → BBox
    if event.state & 0x0004:

        bbox_start(event)

    # Shift + 클릭 → Pan
    elif event.state & 0x0001:

        pan_start(event)

    # 일반 클릭 → 선택
    else:

        select_box(event)

    canvas.focus_set()


def mouse_drag(event):

    # BBox 그리는 중
    if drawing_box is not None:

        bbox_move(event)

    # Shift → Pan
    elif event.state & 0x0001:

        pan_move(event)


def mouse_release(event):

    if drawing_box is not None:

        bbox_end(event)


# ============================================================
# UI
# ============================================================

top_frame = tk.Frame(root)
top_frame.pack(
    fill="x",
    padx=10,
    pady=8
)


open_button = tk.Button(
    top_frame,
    text="이미지 열기",
    command=open_image
)
open_button.pack(
    side="left",
    padx=3
)


folder_button = tk.Button(
    top_frame,
    text="폴더 선택",
    command=select_folder
)
folder_button.pack(
    side="left",
    padx=3
)


zoom_in_button = tk.Button(
    top_frame,
    text="확대",
    command=zoom_in
)
zoom_in_button.pack(
    side="left",
    padx=3
)


zoom_out_button = tk.Button(
    top_frame,
    text="축소",
    command=zoom_out
)
zoom_out_button.pack(
    side="left",
    padx=3
)


fit_button = tk.Button(
    top_frame,
    text="화면 맞추기",
    command=fit_image
)
fit_button.pack(
    side="left",
    padx=3
)


undo_button = tk.Button(
    top_frame,
    text="Undo",
    command=undo
)
undo_button.pack(
    side="left",
    padx=3
)


delete_button = tk.Button(
    top_frame,
    text="BBox 삭제",
    command=delete_box
)
delete_button.pack(
    side="left",
    padx=3
)


save_button = tk.Button(
    top_frame,
    text="저장",
    command=save_current
)
save_button.pack(
    side="left",
    padx=3
)


save_next_button = tk.Button(
    top_frame,
    text="저장 후 다음",
    command=save_and_next
)
save_next_button.pack(
    side="left",
    padx=3
)


# ============================================================
# 정보
# ============================================================

info_frame = tk.Frame(root)
info_frame.pack(
    fill="x",
    padx=10
)


filename_label = tk.Label(
    info_frame,
    text="파일명: 없음"
)
filename_label.pack(
    side="left",
    padx=10
)


count_label = tk.Label(
    info_frame,
    text="0 / 0"
)
count_label.pack(
    side="right",
    padx=10
)


# ============================================================
# 필터
# ============================================================

filter_frame = tk.Frame(root)
filter_frame.pack(
    fill="x",
    padx=10,
    pady=3
)


tk.Label(
    filter_frame,
    text="필터"
).pack(
    side="left"
)


filter_var = tk.StringVar(
    value="전체"
)


filter_combo = ttk.Combobox(
    filter_frame,
    textvariable=filter_var,
    values=[
        "전체",
        "REVIEW",
        "EDITED",
        "REVIEWED"
    ],
    state="readonly",
    width=12
)

filter_combo.pack(
    side="left",
    padx=5
)


# ============================================================
# 작업 영역
# ============================================================

main_frame = tk.Frame(root)

main_frame.pack(
    fill="both",
    expand=True,
    padx=10,
    pady=5
)


# ============================================================
# Canvas
# ============================================================

image_frame = tk.Frame(
    main_frame,
    bd=2,
    relief="sunken"
)

image_frame.pack(
    side="left",
    fill="both",
    expand=True
)


canvas = tk.Canvas(
    image_frame,
    bg="gray"
)

canvas.pack(
    fill="both",
    expand=True
)


# ============================================================
# 오른쪽 설정 영역
# ============================================================

control_frame = tk.Frame(
    main_frame,
    width=230
)

control_frame.pack(
    side="right",
    fill="y",
    padx=(10, 0)
)


# ============================================================
# 클래스
# ============================================================

tk.Label(
    control_frame,
    text="클래스"
).pack(
    pady=(5, 3)
)


current_class_var = tk.StringVar(
    value="0"
)


class_combo = ttk.Combobox(
    control_frame,
    textvariable=current_class_var,
    values=[
        "0",
        "1",
        "2"
    ],
    state="readonly",
    width=15
)

class_combo.pack(
    pady=3
)


class_change_button = tk.Button(
    control_frame,
    text="선택 BBox 클래스 변경",
    command=change_class
)

class_change_button.pack(
    pady=5
)


# ============================================================
# 상태
# ============================================================

tk.Label(
    control_frame,
    text="검수 상태"
).pack(
    pady=(15, 3)
)


status_var = tk.StringVar(
    value="REVIEW"
)


tk.Button(
    control_frame,
    text="PASS",
    width=15,
    command=lambda:
        set_status("PASS")
).pack(
    pady=2
)


tk.Button(
    control_frame,
    text="EDITED",
    width=15,
    command=lambda:
        set_status("EDITED")
).pack(
    pady=2
)


tk.Button(
    control_frame,
    text="REVIEW",
    width=15,
    command=lambda:
        set_status("REVIEW")
).pack(
    pady=2
)


tk.Button(
    control_frame,
    text="REVIEWED",
    width=15,
    command=lambda:
        set_status("REVIEWED")
).pack(
    pady=2
)


status_label = tk.Label(
    control_frame,
    textvariable=status_var
)

status_label.pack(
    pady=5
)


# ============================================================
# 작업자
# ============================================================

tk.Label(
    control_frame,
    text="작업자"
).pack(
    pady=(15, 3)
)


worker_var = tk.StringVar()


worker_combo = ttk.Combobox(
    control_frame,
    textvariable=worker_var,
    values=[
        "",
        "worker1",
        "worker2",
        "worker3"
    ],
    width=15
)

worker_combo.pack(
    pady=3
)


# ============================================================
# 검수자
# ============================================================

tk.Label(
    control_frame,
    text="검수자"
).pack(
    pady=(15, 3)
)


reviewer_var = tk.StringVar()


reviewer_combo = ttk.Combobox(
    control_frame,
    textvariable=reviewer_var,
    values=[
        "",
        "reviewer1",
        "reviewer2"
    ],
    width=15
)

reviewer_combo.pack(
    pady=3
)


# ============================================================
# Scene Type
# ============================================================

tk.Label(
    control_frame,
    text="Scene Type"
).pack(
    pady=(15, 3)
)


scene_type_var = tk.StringVar(
    value="normal"
)


scene_combo = ttk.Combobox(
    control_frame,
    textvariable=scene_type_var,
    values=[
        "normal",
        "kimchi+target",
        "object_only"
    ],
    state="readonly",
    width=15
)

scene_combo.pack(
    pady=3
)


# ============================================================
# 메모
# ============================================================

tk.Label(
    control_frame,
    text="Issue / Note"
).pack(
    pady=(15, 3)
)


note_text = tk.Text(
    control_frame,
    width=20,
    height=6
)

note_text.pack(
    pady=3
)


# ============================================================
# 하단
# ============================================================

bottom_frame = tk.Frame(root)

bottom_frame.pack(
    pady=8
)


previous_button = tk.Button(
    bottom_frame,
    text="◀ 이전",
    width=12,
    command=previous_image
)

previous_button.pack(
    side="left",
    padx=5
)


next_button = tk.Button(
    bottom_frame,
    text="다음 ▶",
    width=12,
    command=next_image
)

next_button.pack(
    side="left",
    padx=5
)


# ============================================================
# 마우스 이벤트
# ============================================================

canvas.bind(
    "<ButtonPress-1>",
    mouse_press
)

canvas.bind(
    "<B1-Motion>",
    mouse_drag
)

canvas.bind(
    "<ButtonRelease-1>",
    mouse_release
)


# ============================================================
# 클래스 변경 이벤트
# ============================================================

class_combo.bind(
    "<<ComboboxSelected>>",
    class_changed
)


# ============================================================
# 필터 변경 이벤트
# ============================================================

filter_combo.bind(
    "<<ComboboxSelected>>",
    lambda event:
        apply_filter()
)


# ============================================================
# 단축키
# ============================================================

root.bind_all(
    "<Control-s>",
    lambda event:
        save_current()
)


root.bind_all(
    "<Delete>",
    lambda event:
        delete_box()
)


root.bind_all(
    "<Control-z>",
    lambda event:
        undo()
)


root.bind_all(
    "<Left>",
    lambda event:
        previous_image()
)


root.bind_all(
    "<Right>",
    lambda event:
        next_image()
)


root.bind_all(
    "<KeyPress-plus>",
    lambda event:
        zoom_in()
)


root.bind_all(
    "<KeyPress-equal>",
    lambda event:
        zoom_in()
)


root.bind_all(
    "<KeyPress-minus>",
    lambda event:
        zoom_out()
)


root.bind_all(
    "<KeyPress-KP_Add>",
    lambda event:
        zoom_in()
)


root.bind_all(
    "<KeyPress-KP_Subtract>",
    lambda event:
        zoom_out()
)


# ============================================================
# 변경 감지
# ============================================================

worker_var.trace_add(
    "write",
    data_changed
)


reviewer_var.trace_add(
    "write",
    data_changed
)


scene_type_var.trace_add(
    "write",
    data_changed
)


status_var.trace_add(
    "write",
    data_changed
)


# ============================================================
# 종료
# ============================================================

root.protocol(
    "WM_DELETE_WINDOW",
    close_program
)


# ============================================================
# 프로그램 실행
# ============================================================

root.mainloop()