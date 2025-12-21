"""
اختبار بسيط للفيديو - Simple Video Test
أداة لاختبار إعدادات مختلفة بدون مشاكل الترميز
"""

import json
import time
import logging
from pathlib import Path

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def test_video_settings(video_path: str):
    """اختبار فيديو مع إعدادات مختلفة"""
    
    print("=" * 60)
    print("Person Detection Settings Test")
    print("=" * 60)
    print(f"Video: {video_path}")
    
    # الإعدادات المختلفة
    configs = [
        {"name": "Current", "confidence": 0.35, "desc": "Current settings"},
        {"name": "Strict", "confidence": 0.6, "desc": "Reduce false positives"},
        {"name": "Balanced", "confidence": 0.45, "desc": "Balanced approach"},
        {"name": "Sensitive", "confidence": 0.25, "desc": "More detections"}
    ]
    
    results = []
    
    for config in configs:
        print(f"\nTesting: {config['name']}")
        print(f"  Description: {config['desc']}")
        print(f"  Confidence: {config['confidence']}")
        
        try:
            # Apply consistency
            from ensure_consistency import ensure_consistency
            ensure_consistency()
            
            # Create processor
            from src.level2_video_processor import Level2VideoProcessor
            
            processor = Level2VideoProcessor(
                device="cpu",
                imgsz=416,
                conf_threshold=config["confidence"],
                enable_face_recognition=False,
                enable_activity_recognition=False,
                enable_advanced_ai=False,
                random_seed=42
            )
            
            # Process video
            start_time = time.time()
            video_results = processor.process_video(
                input_path=video_path,
                output_path=None
            )
            processing_time = time.time() - start_time
            
            # Analyze results
            detected_persons = len(video_results.get('statistics', []))
            
            result = {
                "config_name": config["name"],
                "confidence": config["confidence"],
                "detected_persons": detected_persons,
                "processing_time": processing_time,
                "description": config["desc"]
            }
            
            results.append(result)
            
            print(f"  Result: {detected_persons} persons detected")
            print(f"  Time: {processing_time:.2f} seconds")
            
        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                "config_name": config["name"],
                "confidence": config["confidence"],
                "error": str(e)
            })
    
    # Show summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    valid_results = [r for r in results if 'error' not in r]
    
    if valid_results:
        print("Setting      | Persons | Time    | Description")
        print("-" * 50)
        
        for result in valid_results:
            name = result["config_name"][:12].ljust(12)
            persons = str(result["detected_persons"]).center(7)
            time_str = f"{result['processing_time']:.2f}s".center(7)
            desc = result["description"][:20]
            print(f"{name} | {persons} | {time_str} | {desc}")
        
        # Analysis
        person_counts = [r["detected_persons"] for r in valid_results]
        
        print(f"\nAnalysis:")
        print(f"  Min persons detected: {min(person_counts)}")
        print(f"  Max persons detected: {max(person_counts)}")
        print(f"  Different results: {len(set(person_counts))}")
        
        # Recommendations
        print(f"\nRecommendations:")
        
        if len(set(person_counts)) == 1:
            print("  All settings give same result - system is stable")
        elif max(person_counts) > min(person_counts) * 2:
            print("  Large difference in results detected:")
            print("  - Try increasing confidence to 0.5 or higher")
            print("  - Check video quality and lighting")
            print("  - May need to adjust tracking settings")
        else:
            print("  Normal variation - choose setting based on needs")
        
        # Best setting suggestion
        if max(person_counts) > 0:
            detecting_results = [r for r in valid_results if r["detected_persons"] > 0]
            if detecting_results:
                best_result = max(detecting_results, key=lambda x: x["confidence"])
                print(f"\nSuggested setting: {best_result['config_name']}")
                print(f"  Confidence: {best_result['confidence']}")
                print(f"  Detected: {best_result['detected_persons']} persons")
        
    else:
        print("No successful results")
    
    # Save results
    results_file = Path("video_test_results.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "video_path": video_path,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {results_file}")
    
    return results

def apply_settings(confidence: float):
    """تطبيق الإعدادات على النظام"""
    config_file = Path("config/unified_config.json")
    
    try:
        # Read current config
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Backup
        backup_file = Path("config/unified_config_backup.json")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # Apply new settings
        config["yolo"]["confidence"] = confidence
        config["level2_processor"]["conf_threshold"] = confidence
        
        # Improved tracking settings
        config["tracking"]["track_high_thresh"] = min(0.7, confidence + 0.1)
        config["tracking"]["new_track_thresh"] = min(0.8, confidence + 0.2)
        config["tracking"]["match_thresh"] = 0.85
        
        # Save new config
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"Settings applied successfully:")
        print(f"  Confidence: {confidence}")
        print(f"  Track High Thresh: {config['tracking']['track_high_thresh']}")
        print(f"  New Track Thresh: {config['tracking']['new_track_thresh']}")
        print(f"  Backup saved to: {backup_file}")
        
        return True
        
    except Exception as e:
        print(f"Error applying settings: {e}")
        return False

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) < 2:
        video_path = "web_app/static/uploads/test_videos/test_sample.mp4"
        print("Using test video...")
    else:
        video_path = sys.argv[1]
    
    # Check if video exists
    if not Path(video_path).exists():
        print(f"Video not found: {video_path}")
        return
    
    # Test settings
    results = test_video_settings(video_path)
    
    # Ask user about applying settings
    valid_results = [r for r in results if 'error' not in r and r['detected_persons'] > 0]
    
    if valid_results:
        print(f"\nDo you want to apply optimized settings to the system?")
        
        # Suggest best confidence
        best_confidence = max(valid_results, key=lambda x: x["confidence"])["confidence"]
        print(f"  Suggested confidence: {best_confidence}")
        
        choice = input("  Type 'y' to apply or anything else to cancel: ").lower().strip()
        
        if choice in ['y', 'yes']:
            if apply_settings(best_confidence):
                print("\nSettings applied successfully!")
                print("Restart the system to activate new settings")
            else:
                print("\nFailed to apply settings")
        else:
            print("\nSettings not applied")
    
    print(f"\nTest completed!")

if __name__ == "__main__":
    main()
