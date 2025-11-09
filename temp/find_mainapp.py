with open('e:/CODE/VisionDeploy-Studio/app/gui_ctk.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    count = 0
    for i, line in enumerate(lines):
        if 'class MainApp' in line:
            print(f'Line {i+1}: {line.strip()}')
            count += 1
    print(f'Total found: {count}')