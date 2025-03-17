import customtkinter as ctk
import threading
import time
from datetime import datetime
import os
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
		self.root = root
		self.is_recording = False
		self.stop_recording = False
		self.fps = 15
		self.output_directory = "./recordings"
		self.monitor_index = None
		self.record_duration = None

		# 디렉토리가 없으면 생성
		if not os.path.exists(self.output_directory):
			os.makedirs(self.output_directory)

		# GUI 생성
		self.root.title("Black Box")
		self.root.geometry("500x700")
		ctk.set_appearance_mode("Dark")
		ctk.set_default_color_theme("blue")

		# 레이블 및 UI 요소
		self.status_label = ctk.CTkLabel(master=root, text="이슈 찾기 위한 화면녹화 프로그램입니다.", font=("Arial", 16))
		self.status_label.pack(pady=20)

		# 모니터 선택 (드롭다운)
		self.monitor_label = ctk.CTkLabel(master=root, text="모니터를 선택하세요.", font=("Arial", 14))
		self.monitor_label.pack(pady=10)

		self.monitor_dropdown = ctk.CTkOptionMenu(master=root, values=self.get_monitor_list())
		self.monitor_dropdown.pack(pady=10)

		# 녹화 시간 입력 필드
		self.duration_label = ctk.CTkLabel(master=root, text="녹화 시간을 입력해주세요(초 단위)", font=("Arial", 14))
		self.duration_label.pack(pady=10)

		self.duration_entry = ctk.CTkEntry(master=root, placeholder_text="60")
		self.duration_entry.pack(pady=10)

		# 버튼
		self.start_button = ctk.CTkButton(master=root, text="녹화 시작", command=self.start_recording)
		self.start_button.pack(pady=10)

		self.stop_button = ctk.CTkButton(master=root, text="녹화 종료", command=self.stop, state="disabled")
		self.stop_button.pack(pady=10)

		# 생성된 파일과 삭제된 파일 목록을 표시
		# 생성된 파일 라벨
		self.created_file_label = ctk.CTkLabel(master=root, text="생성된 파일 목록 ▼", font=("Arial", 14))
		self.created_file_label.pack(pady=5)
		self.created_file_list = ctk.CTkTextbox(master=root, height=100, width=350)
		self.created_file_list.pack(pady=10)

		# 삭제된 파일 라벨
		self.deleted_file_label = ctk.CTkLabel(master=root, text="삭제된 파일 목록 ▼", font=("Arial", 14))
		self.deleted_file_label.pack(pady=5)
		self.deleted_file_list = ctk.CTkTextbox(master=root, height=100, width=350)
		self.deleted_file_list.pack(pady=10)



	def get_monitor_list(self):
		"""모니터 목록을 가져와 문자열 목록으로 반환"""
		monitors = get_monitors()
		monitor_list = []
		for idx, monitor in enumerate(monitors):
			monitor_list.append(f"모니터 {idx + 1}: {monitor.width}x{monitor.height} ({monitor.x}, {monitor.y})")
		return monitor_list

	def start_recording(self):
		"""녹화를 시작하고 녹화 자동 반복"""
		try:
			# 초기 녹화 설정 가져오기
			monitor_selection = self.monitor_dropdown.get()
			self.monitor_index = int(monitor_selection.split(":")[0].split(" ")[1]) - 1  # "Monitor 1:"에서 인덱스 추출
			self.record_duration = int(self.duration_entry.get())

			# 녹화 시간 또는 선택된 모니터가 유효한지 확인
			if self.record_duration <= 0:
				self.status_label.configure(text="Error: 녹화 시간은 1초 이상이어야 합니다!")
				return

			self.is_recording = True
			self.stop_recording = False
			self.start_button.configure(state="disabled")
			self.stop_button.configure(state="normal")

			# 상태 업데이트 및 녹화 시작
			self.status_label.configure(text="녹화중 입니다...")
			recording_thread = threading.Thread(target=self.record_screen_loop)
			recording_thread.daemon = True
			recording_thread.start()
		except ValueError:
			self.status_label.configure(text="Error: 녹화 시간을 입력해 주세요.")

	def stop(self):
		"""녹화를 종료"""
		if self.is_recording:
			self.stop_recording = True
			self.status_label.configure(text="녹화 종료...")
			self.start_button.configure(state="normal")
			self.stop_button.configure(state="disabled")

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
			self.status_label.configure(text="Error: 모니터 idx값이 맞지 않습니다!")
			return

		# 선택한 모니터의 크기 가져오기
		target_monitor = monitors[self.monitor_index]
		x, y, width, height = target_monitor.x, target_monitor.y, target_monitor.width, target_monitor.height

		# 저장 파일 이름 정의
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		video_filename = os.path.join(self.output_directory, f"recording_{timestamp}.mp4")

		# OpenCV VideoWriter 설정
		fourcc = cv2.VideoWriter_fourcc(*"MP4V")
		out = cv2.VideoWriter(video_filename, fourcc, self.fps, (width, height))

		start_time = time.time()
		with mss.mss() as sct:
			monitor = {"top":y, "left":x, "width":width, "height":height}

			while not self.stop_recording:
				try:
					# 화면 캡처
					screenshot = np.array(sct.grab(monitor))
					frame = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
					out.write(frame)

					# 남은 시간 계산
					elapsed_time = time.time() - start_time
					remaining_time = max(0, int(self.record_duration - elapsed_time))
					self.status_label.configure(text=f"녹화중... 남은시간: {remaining_time}s")

					# 녹화 시간 초과 시 종료
					if remaining_time <= 0:
						break

					time.sleep(1 / self.fps)
				except Exception as e:
					self.status_label.configure(text=f"Error: {e}")
					break

		# 녹화 종료
		out.release()

		# 생성된 파일을 텍스트 박스에 추가
		self.created_file_list.insert("end", f"{os.path.basename(video_filename)}\n")  # 목록에 추가
		self.created_file_list.see("end")  # 자동 스크롤
		self.status_label.configure(text=f"녹화 저장: {video_filename}")

	def clean_old_files(self):
		"""만약 파일 수가 30개를 넘으면 가장 오래된 파일을 삭제"""
		file_list = [os.path.join(self.output_directory, f) for f in os.listdir(self.output_directory) if os.path.isfile(os.path.join(self.output_directory, f))]

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


if __name__ == "__main__":
	app = ctk.CTk()
	recorder_app = ScreenRecorderApp(app)
	app.mainloop()
