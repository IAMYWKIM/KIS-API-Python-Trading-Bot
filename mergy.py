import os

# MODIFIED: [출력 파일명 락온] 사용자 지시에 따라 code.txt 유지
output_filename = 'code.txt'

# 합칠 파일들이 들어있는 폴더 경로 (기본값: 현재 폴더)
folder_path = '.' 

# NEW: [자기 잠식 방어막] 실행 중인 스크립트 파일명을 동적으로 추출하여 병합 대상에서 제외
current_script = os.path.basename(__file__)

with open(output_filename, 'w', encoding='utf-8') as outfile:
    # MODIFIED: [동적 파일 스캔 복원] os.listdir을 사용하여 디렉토리 내 전체 파일 스캔
    for filename in os.listdir(folder_path):
        # NEW: [확장자 락온 및 바이패스] .py 확장자만 필터링하고, 자기 자신은 건너뜀
        if filename.endswith('.py') and filename != current_script:
            file_path = os.path.join(folder_path, filename)
            
            outfile.write(f"\n{'='*50}\n")
            outfile.write(f"FILE: {filename}\n")
            outfile.write(f"{'='*50}\n\n")
            
            with open(file_path, 'r', encoding='utf-8') as infile:
                outfile.write(infile.read())
                outfile.write("\n")

print(f"🚀 성공! 디렉토리 내 모든 파이썬 코드가 '{output_filename}' 파일에 무결점으로 병합 완료되었습니다.")
