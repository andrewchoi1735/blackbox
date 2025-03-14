import os
import cv2
import numpy as np
from screeninfo import get_monitors  # 모니터 정보 가져오기
import time
from datetime import datetime
from file_utility import clean_old_files  # 파일 정리 유틸 가져오기
import pyautogui

# 녹화 프레임 분당 설정 (60초 기준)
fps = 15
frame_interval = 1 / fps

# 저장될 파일 경로 설정
output_directory = "./recordings"

# 디렉터리 없으면 생성
if not os.path.exists(output_directory):
	os.makedirs(output_directory)


def get_monitor_info():
	"""모니터 정보 가져오기"""
	monitors = get_monitors()
	print("모니터 정보:")
	for idx, monitor in enumerate(monitors):
		print(f"모니터 {idx + 1}: {monitor}")
	return monitors


def record_screen(monitor_index=0):
	"""특정 모니터 영역을 녹화"""
	monitors = get_monitor_info()
	if monitor_index >= len(monitors):
		print(f"잘못된 모니터 인덱스입니다. 총 {len(monitors)}개의 모니터만 존재합니다.")
		return

	# 대상 모니터 선택
	target_monitor = monitors[monitor_index]
	x, y, width, height = target_monitor.x, target_monitor.y, target_monitor.width, target_monitor.height

	# 좌표 검증 (음수 좌표 방지)
	if x < 0 or y < 0:
		print("좌표 값이 정상적이지 않습니다. 기본 모니터를 사용합니다.")
		x, y, width, height = 0, 0, 1920, 1080  # 기본 모니터 해상도로 대체

	print(f"선택된 모니터 좌표: x={x}, y={y}, width={width}, height={height}")

	# 녹화 파일 이름 설정
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	video_filename = os.path.join(output_directory, f"recording_{timestamp}.avi")

	# OpenCV VideoWriter 설정
	fourcc = cv2.VideoWriter_fourcc(*"XVID")
	out = cv2.VideoWriter(video_filename, fourcc, fps, (int(width), int(height)))

	start_time = time.time()

	while True:
		try:
			# 화면 캡처
			screenshot = pyautogui.screenshot(region=(x, y, width, height))
			frame = np.array(screenshot)  # PIL 이미지를 NumPy 배열로 변환
			frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # OpenCV용 색상 체계로 변환
			out.write(frame)
			time.sleep(frame_interval)

			# 1분이 지나면 녹화 종료
			if time.time() - start_time > 60:
				break

		except Exception as e:
			print(f"녹화 중 오류 발생: {e}")
			break

	out.release()
	print(f"{video_filename} 저장 완료!")


def main():
	"""메인 함수 - 모니터 선택 후 녹화  """
	monitor_index = 1  # 캡처하려는 모니터 인덱스 (0 = 첫 번째 모니터)
	while True:
		print(f"모니터 {monitor_index + 1} 녹화 시작...")
		record_screen(monitor_index)
		print("1분 녹화 저장 완료, 다음 녹화로 이어집니다...")

		# 오래된 파일 정리 실행
		clean_old_files(output_directory, max_files=3)


if __name__ == "__main__":
	main()
