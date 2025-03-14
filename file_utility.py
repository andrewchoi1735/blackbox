import os


def clean_old_files(directory, max_files=10):
	"""지정된 디렉토리에서 파일 수를 관리"""
	files = sorted(os.listdir(directory))  # 파일 정렬
	if len(files) > max_files:
		files_to_remove = files[:len(files) - max_files]
		for file in files_to_remove:
			os.remove(os.path.join(directory, file))
			print(f"{file} 삭제 완료!")
