import customtkinter as ctk
import threading
import time
from datetime import datetime
import os
import cv2
import numpy as np
from screeninfo import get_monitors
import mss


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
		self.root.title("Screen Recorder")
		self.root.geometry("400x400")
		ctk.set_appearance_mode("Dark")
		ctk.set_default_color_theme("blue")

		# 레이블 및 UI 요소
		self.status_label = ctk.CTkLabel(master=root, text="Welcome to Screen Recorder", font=("Arial", 16))
		self.status_label.pack(pady=20)

		# 모니터 선택 (드롭다운)
		self.monitor_label = ctk.CTkLabel(master=root, text="Select Monitor:", font=("Arial", 14))
		self.monitor_label.pack(pady=10)

		self.monitor_dropdown = ctk.CTkOptionMenu(master=root, values=self.get_monitor_list())
		self.monitor_dropdown.pack(pady=10)

		# 녹화 시간 입력 필드
		self.duration_label = ctk.CTkLabel(master=root, text="Enter Recording Time (seconds):", font=("Arial", 14))
		self.duration_label.pack(pady=10)

		self.duration_entry = ctk.CTkEntry(master=root, placeholder_text="60")
		self.duration_entry.pack(pady=10)

		# 버튼
		self.start_button = ctk.CTkButton(master=root, text="Start Recording", command=self.start_recording)
		self.start_button.pack(pady=10)

		self.stop_button = ctk.CTkButton(master=root, text="Stop Recording", command=self.stop, state="disabled")
		self.stop_button.pack(pady=10)

	def get_monitor_list(self):
		"""모니터 목록을 가져와 문자열 목록으로 반환"""
		monitors = get_monitors()
		monitor_list = []
		for idx, monitor in enumerate(monitors):
			monitor_list.append(f"Monitor {idx + 1}: {monitor.width}x{monitor.height} ({monitor.x}, {monitor.y})")
		return monitor_list

	def start_recording(self):
		"""녹화를 시작하고 녹화 자동 반복"""
		try:
			# 초기 녹화 설정 가져오기
			monitor_selection = self.monitor_dropdown.get()
			self.monitor_index = int(monitor_selection.split(":")[0].split(" ")[1]) - 1  # "Monitor 1:"에서 인덱스 추출
			self.record_duration = int(self.duration_entry.get())

			# 입력 값 검증
			if self.monitor_index is None or self.record_duration is None:
				self.status_label.configure(text="Error: Invalid inputs!")
				return

			self.is_recording = True
			self.stop_recording = False
			self.start_button.configure(state="disabled")
			self.stop_button.configure(state="normal")

			# 상태 업데이트 및 녹화 시작
			self.status_label.configure(text="Recording in progress...")
			recording_thread = threading.Thread(target=self.record_screen_loop)
			recording_thread.daemon = True
			recording_thread.start()
		except ValueError:
			self.status_label.configure(text="Error: Invalid duration or monitor selection!")

	def stop(self):
		"""녹화를 종료"""
		if self.is_recording:
			self.stop_recording = True
			self.status_label.configure(text="Stopping recording...")
			self.start_button.configure(state="normal")
			self.stop_button.configure(state="disabled")

	def record_screen_loop(self):
		"""녹화를 반복 실행"""
		while not self.stop_recording:  # 종료 명령을 받을 때까지 무한 반복
			self.record_screen()

			# 오래된 파일 삭제
			self.clean_old_files()

			# 상태 업데이트
			if not self.stop_recording:
				self.status_label.configure(text="Recording finished. Restarting new recording...")

	def record_screen(self):
		"""특정 모니터의 화면 녹화"""
		monitors = get_monitors()

		if self.monitor_index >= len(monitors):
			self.status_label.configure(text="Error: Invalid monitor index!")
			return

		# 선택한 모니터의 크기 가져오기
		target_monitor = monitors[self.monitor_index]
		x, y, width, height = target_monitor.x, target_monitor.y, target_monitor.width, target_monitor.height

		# 저장 파일 이름 정의
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		video_filename = os.path.join(self.output_directory, f"recording_{timestamp}.avi")

		# OpenCV VideoWriter 설정
		fourcc = cv2.VideoWriter_fourcc(*"XVID")
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
					remaining_time = max(0, self.record_duration - elapsed_time)
					self.status_label.configure(text=f"Recording... Remaining: {remaining_time:.2f}s")

					# 녹화 시간 초과 시 종료
					if remaining_time <= 0:
						break

					time.sleep(1 / self.fps)
				except Exception as e:
					self.status_label.configure(text=f"Error: {e}")
					break

		# 녹화 종료
		out.release()
		self.status_label.configure(text=f"Recording saved: {video_filename}")

	def clean_old_files(self):
		"""만약 파일 수가 30개를 넘으면 가장 오래된 파일을 삭제"""
		file_list = [os.path.join(self.output_directory, f) for f in os.listdir(self.output_directory) if
		             os.path.isfile(os.path.join(self.output_directory, f))]

		# 파일을 수정 시간 기준으로 정렬
		file_list.sort(key=os.path.getmtime)

		# 파일 30개 초과 시 삭제
		while len(file_list) > 30:
			oldest_file = file_list.pop(0)  # 가장 오래된 파일
			os.remove(oldest_file)


if __name__ == "__main__":
	app = ctk.CTk()
	recorder_app = ScreenRecorderApp(app)
	app.mainloop()
