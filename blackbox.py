import customtkinter as ctk
from tkinter import messagebox
import os
import threading
import time
from datetime import datetime
import cv2
import numpy as np
from screeninfo import get_monitors
import mss
import sys

# OpenCV 및 FFMPEG 로그 억제
os.environ["OPENCV_LOG_LEVEL"] = "1"  # OpenCV 로그 (1: 경고 수준으로 최소화)
os.environ["OPENCV_FFMPEG_DEBUG"] = "0"  # FFMPEG 로그 수준 최소화
sys.stderr = open(os.devnull, "w")  # stderr로 전달되는 메시지 무시


class ScreenRecorderApp:
	def __init__(self, root):
		# 기본 설정
		self.codec = None
		self.root = root
		self.is_recording = False
		self.stop_recording = False
		self.fps = 10
		self.output_directory = "./recordings"
		self.monitor_index = None
		self.record_duration = None

		# 디렉토리가 없으면 생성
		if not os.path.exists(self.output_directory):
			os.makedirs(self.output_directory)

		# GUI 설정
		self.root.title("Black Box")
		self.root.geometry("400x650")
		ctk.set_appearance_mode("Dark")
		ctk.set_default_color_theme("blue")

		# 전체 창의 행(row) 가중치
		self.root.grid_rowconfigure(0, weight=1)  # 상태 레이블
		self.root.grid_rowconfigure(1, weight=0)  # 옵션 선택 (모니터/시간)
		self.root.grid_rowconfigure(2, weight=0)  # 버튼 섹션
		self.root.grid_rowconfigure(3, weight=1)  # 파일 탭 (생성/삭제)
		self.root.grid_rowconfigure(4, weight=0)  # 폴더 열기 버튼
		self.root.grid_columnconfigure(0, weight=1)

		# 상태 레이블 (row 0)
		self.status_label = ctk.CTkLabel(
			master=self.root,
			text="이슈 관찰용 화면녹화 프로그램입니다.",
			font=("Arial", 16, "bold"),
		)
		self.status_label.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="nwe")

		# 옵션 선택 프레임 (row 1, monitor & 녹화 시간)
		self.options_frame = ctk.CTkFrame(master=self.root)
		self.options_frame.grid(row=1, column=0, pady=(10, 10), padx=20, sticky="we")

		# 프레임 내부 구성 - 모니터 선택
		self.options_frame.grid_columnconfigure(0, weight=1)
		self.options_frame.grid_columnconfigure(1, weight=2)

		self.monitor_label = ctk.CTkLabel(master=self.options_frame, text="모니터 선택", font=("Arial", 14))
		self.monitor_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

		self.monitor_dropdown = ctk.CTkOptionMenu(
			master=self.options_frame, values=self.get_monitor_list(), width=150, dropdown_fg_color="#000000",
			dropdown_hover_color="#4169e1",
			fg_color="#000000",  # 드롭다운 버튼의 배경색 (메뉴 표시 전 기본 색상)
			button_color="#2E3A46",  # 드롭다운 버튼 자체의 색상
			button_hover_color="#4169E1"  # 드롭다운 버튼의 호버 상태 배경색
		)
		self.monitor_dropdown.grid(row=0, column=1, padx=10, pady=10, sticky="we")

		# 프레임 내부 구성 - 코덱 선택 (추가)
		self.codec_label = ctk.CTkLabel(master=self.options_frame, text="코덱 선택", font=("Arial", 14))
		self.codec_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")

		# 코덱 선택 드롭다운 메뉴
		self.codec_dropdown = ctk.CTkOptionMenu(
			master=self.options_frame,
			values=["MPEG-4 (mp4)", "XVID (avi)", "VP8 (webm)"],
			width=150,
			dropdown_fg_color="#000000",
			dropdown_hover_color="#4169e1",
			fg_color="#000000",  # 드롭다운 버튼의 배경색 (메뉴 표시 전 기본 색상)
			button_color="#2E3A46",  # 드롭다운 버튼 자체의 색상
			button_hover_color="#4169E1"  # 드롭다운 버튼의 호버 상태 배경색
		)
		self.codec_dropdown.grid(row=2, column=1, padx=10, pady=10, sticky="we")

		# 프레임 내부 구성 - 녹화 시간
		self.duration_label = ctk.CTkLabel(master=self.options_frame, text="녹화 시간 (초)", font=("Arial", 14))
		self.duration_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

		self.duration_entry = ctk.CTkEntry(master=self.options_frame, placeholder_text="예: 60")
		self.duration_entry.grid(row=1, column=1, padx=10, pady=10, sticky="we")

		# 버튼 섹션 (row 2)
		self.button_frame = ctk.CTkFrame(master=self.root)
		self.button_frame.grid(row=2, column=0, pady=10, padx=20, sticky="we")
		self.button_frame.grid_columnconfigure(0, weight=1)  # 첫 번째 버튼
		self.button_frame.grid_columnconfigure(1, weight=1)  # 두 번째 버튼

		# 녹화 시작 버튼
		self.start_button = ctk.CTkButton(
			master=self.button_frame, text="녹화 시작", command=self.start_recording, height=40, fg_color="red",
			text_color="white", font=("Arial", 14, "bold")
		)
		self.start_button.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nswe")

		# 녹화 종료 버튼
		self.stop_button = ctk.CTkButton(
			master=self.button_frame, text="녹화 종료", command=self.stop, state="disabled", font=("Arial", 14, "bold")
		)
		self.stop_button.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nswe")

		# 파일 탭 섹션 (row 3)
		self.file_tabs = ctk.CTkTabview(master=self.root, width=550, height=270)
		self.file_tabs.grid(row=3, column=0, pady=10, padx=20, sticky="nswe")

		# 탭 추가
		self.created_tab = self.file_tabs.add("생성된 파일")
		self.deleted_tab = self.file_tabs.add("삭제된 파일")

		# 생성된 파일 리스트
		self.created_file_list = ctk.CTkTextbox(master=self.created_tab, height=200, width=500)
		self.created_file_list.pack(pady=10, padx=10)

		# 삭제된 파일 리스트
		self.deleted_file_list = ctk.CTkTextbox(master=self.deleted_tab, height=200, width=500)
		self.deleted_file_list.pack(pady=10, padx=10)

		# 폴더 열기 버튼 (row 4)
		self.open_dir_button = ctk.CTkButton(
			master=self.root, text="저장된 폴더 열기", command=self.open_output_directory, height=40
		)
		self.open_dir_button.grid(row=4, column=0, pady=(10, 20), padx=20, sticky="we")

	def get_monitor_list(self):
		"""모니터 목록을 가져와 문자열 목록으로 반환"""
		monitors = get_monitors()
		monitor_list = []
		for idx, monitor in enumerate(monitors):
			monitor_list.append(f"모니터 {idx + 1}: {monitor.width}x{monitor.height} ({monitor.x}, {monitor.y})")
		return monitor_list

	def open_output_directory(self):
		"""녹화 저장 폴더를 파일 탐색기를 통해 열기"""
		if os.path.exists(self.output_directory):
			os.startfile(os.path.abspath(self.output_directory))  # 파일 탐색기로 열기
		else:
			messagebox.showerror("오류", "녹화된 파일 디렉토리가 존재하지 않습니다.")

	def start_recording(self):
		"""녹화를 시작하고 녹화 자동 반복"""
		try:
			# 초기 녹화 설정 가져오기
			monitor_selection = self.monitor_dropdown.get()
			self.monitor_index = int(monitor_selection.split(":")[0].split(" ")[1]) - 1  # "Monitor 1:"에서 인덱스 추출
			self.record_duration = int(self.duration_entry.get())

			# 녹화 시간 또는 선택된 모니터가 유효한지 확인
			if self.record_duration <= 0:
				self.status_label.configure(text="Error: 녹화 시간은 1초 이상이어야 합니다!", text_color='red')
				return

			# 사용자가 선택한 코덱 값 가져오기
			selected_codec = self.codec_dropdown.get()
			if selected_codec == "MPEG-4 (mp4)":
				self.codec = "mp4v"
			elif selected_codec == "XVID (avi)":
				self.codec = "XVID"
			elif selected_codec == "VP8 (webm)":
				self.codec = "VP80"
			else:
				raise ValueError("지원되지 않는 코덱")
			
			# 녹화 준비 완료
			self.is_recording = True
			self.stop_recording = False
			# 버튼 및 설정 UI 비활성화
			self.start_button.configure(state="disabled")
			self.monitor_dropdown.configure(state="disabled")  # 모니터 선택 비활성화
			self.duration_entry.configure(state="disabled")  # 녹화 시간 입력 비활성화
			self.codec_dropdown.configure(state="disabled")  # 코덱 선택 비활성화
			self.stop_button.configure(state="normal")
			self.status_label.configure(text="녹화중 입니다...", text_color="green")

			recording_thread = threading.Thread(target=self.record_screen_loop)
			recording_thread.start()
		except ValueError as e:
			self.status_label.configure(text=f"Error: {str(e)}", text_color='red')

	def stop(self):
		"""녹화를 종료"""
		if self.is_recording:
			self.stop_recording = True
			self.status_label.configure(text="녹화 종료...", text_color='white')
			# 버튼 및 설정 UI 다시 활성화
			self.start_button.configure(state="normal")  # 녹화 시작 버튼 활성화
			self.monitor_dropdown.configure(state="normal")  # 모니터 선택 활성화
			self.duration_entry.configure(state="normal")  # 녹화 시간 입력 활성화
			self.codec_dropdown.configure(state="normal")  # 코덱 선택 활성화
			self.stop_button.configure(state="disabled")  # 녹화 중지 버튼 비활성화


	def record_screen_loop(self):
		"""녹화를 반복 실행"""
		while not self.stop_recording:  # 종료 명령을 받을 때까지 무한 반복
			self.record_screen()

			# 오래된 파일 삭제 (주기적으로만 실행)
			if len(os.listdir(self.output_directory)) > 30:
				self.clean_old_files()

			# 상태 업데이트
			if not self.stop_recording:
				self.status_label.configure(text="녹화 완료. 새로운 녹화를 시작...")

	def record_screen(self):
		"""특정 모니터의 화면 녹화"""
		monitors = get_monitors()

		if self.monitor_index >= len(monitors):
			self.status_label.configure(text="Error: 모니터 선택이 맞지 않습니다!", text_color='red')
			return

		# 선택한 모니터의 크기 가져오기
		target_monitor = monitors[self.monitor_index]
		x, y, width, height = target_monitor.x, target_monitor.y, target_monitor.width, target_monitor.height

		# 선택된 코덱 및 파일 확장자 처리
		if self.codec == "mp4v":
			file_extension = ".mp4"
		elif self.codec == "XVID":
			file_extension = ".avi"
		elif self.codec == "VP80":
			file_extension = ".webm"
		else:
			self.status_label.configure(text="Error: 잘못된 코덱 선택", text_color='red')
			return

		# 저장 파일 이름 정의 (선택된 코덱에 따라 확장자 변경)
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		video_filename = os.path.join(self.output_directory, f"recording_{timestamp}{file_extension}")

		# OpenCV VideoWriter 설정 (선택된 코덱 사용)
		fourcc = cv2.VideoWriter_fourcc(*self.codec)
		out = cv2.VideoWriter(video_filename, fourcc, self.fps, (width, height))

		with mss.mss() as sct:
			monitor = {"top":y, "left":x, "width":width, "height":height}

			# 녹화 종료 시간 계산
			start_time = time.time()
			end_time = start_time + self.record_duration  # 종료 시간

			sct.compression_level = 1  # 최소화된 압축(속도 증가)

			while True:
				try:
					current_time = time.time()  # 현재 시간 측정
					if current_time >= end_time or self.stop_recording:  # 종료 조건
						break

					# 화면 캡처
					screenshot = np.array(sct.grab(monitor))
					frame = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
					out.write(frame)

					# 남은 시간 계산 및 상태 업데이트
					elapsed_time = current_time - start_time
					remaining_time = max(0, int(self.record_duration - elapsed_time))
					if int(elapsed_time) % 1 == 0:  # 매 초마다 실행
						self.status_label.configure(text=f"녹화중... 남은시간: {remaining_time}s")

					# 프레임 간격 대기 (FPS 조정)
					target_time = start_time + (elapsed_time + (1 / self.fps))  # 다음 프레임의 목표 시간 계산
					delay = target_time - time.time()  # 현재 시간과 목표 시간의 차이 계산
					if delay > 0:
						time.sleep(delay)
				except Exception as e:
					self.status_label.configure(text=f"Error: {e}")
					break

		# 녹화 종료
		out.release()

		# 생성된 파일을 텍스트 박스에 추가
		self.created_file_list.insert("end", f"{os.path.basename(video_filename)}\n")  # 목록에 추가
		self.created_file_list.see("end")  # 자동 스크롤

	def clean_old_files(self):
		"""만약 파일 수가 30개를 넘으면 가장 오래된 파일을 삭제"""
		file_list = [os.path.join(self.output_directory, f) for f in os.listdir(self.output_directory) if
		             os.path.isfile(os.path.join(self.output_directory, f))]

		# 파일을 수정 시간 기준으로 정렬
		file_list.sort(key=os.path.getmtime)

		# 파일 30개 초과 시 삭제
		while len(file_list) > 30:
			# 가장 오래된 파일 목록에서 삭제
			oldest_file = file_list.pop(0)  # 가장 오래된 파일
			os.remove(oldest_file)

			# 삭제된 파일을 텍스트 박스에 추가
			self.deleted_file_list.insert("end", f"{os.path.basename(oldest_file)}\n")  # 목록에 추가
			self.deleted_file_list.see("end")  # 자동 스크롤


def resource_path(relative_path):
	"""PyInstaller 패키징 호환 경로 설정"""
	if hasattr(sys, '_MEIPASS'):
		# 번들된 리소스가 위치한 임시 폴더 경로
		return os.path.join(sys._MEIPASS, relative_path)
	return os.path.join(os.path.abspath("."), relative_path)


if __name__ == "__main__":
	app = ctk.CTk()

	# 아이콘 설정 (PyInstaller 환경 대응)
	icon_path = resource_path("record.ico")  # ico 파일 경로

	if os.path.exists(icon_path):  # 파일 존재 여부 확인
		app.wm_iconbitmap(icon_path)
	else:
		print("아이콘 파일을 찾을 수 없습니다. 기본 아이콘이 사용됩니다.")

	recorder_app = ScreenRecorderApp(app)  # 앱 초기화
	app.mainloop()
