#!/usr/bin/env python3
"""
اختبار معالج المستوى الثاني
"""
from src.level2_video_processor import Level2VideoProcessor
import time

print('Testing Level2VideoProcessor...')
processor = Level2VideoProcessor(enable_advanced_ai=False)  # بدون AI للاختبار السريع

try:
    results = processor.process_video(
        input_path='web_app/static/uploads/test_videos/test_sample.mp4',
        output_path='web_app/static/uploads/test_videos/test_output.mp4',
        frame_skip=2,
        max_duration=5
    )
    print('SUCCESS: Video processed!')
    print(f'Persons detected: {len(results["statistics"])}')
    print(f'Processing time: {results["processing_time"]:.2f}s')
    print(f'Total frames processed: {results["processed_frames"]}')
    
    # عرض تفاصيل الأشخاص
    for i, person in enumerate(results["statistics"]):
        print(f'Person {i+1}: {person["name"]}, Duration: {person["duration"]:.2f}s')
        
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
