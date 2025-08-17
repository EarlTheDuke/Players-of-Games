"""Simple script to view exported debug logs."""
import json
import os
from datetime import datetime

def view_latest_export():
    """View the most recent exported log file."""
    log_dir = "error_logs"
    
    if not os.path.exists(log_dir):
        print("❌ No error_logs directory found")
        return
    
    # Find the most recent export file
    export_files = [f for f in os.listdir(log_dir) if f.startswith("error_export_")]
    
    if not export_files:
        print("❌ No export files found")
        return
    
    # Get the most recent file
    export_files.sort(reverse=True)  # Most recent first
    latest_file = export_files[0]
    filepath = os.path.join(log_dir, latest_file)
    
    print(f"📁 Reading: {filepath}")
    print("="*80)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📊 Export Info:")
        print(f"   Session ID: {data.get('session_id')}")
        print(f"   Export Time: {data.get('export_timestamp')}")
        print(f"   Total Logs: {len(data.get('logs', []))}")
        print()
        
        # Show validation errors with debug output
        validation_errors = [log for log in data.get('logs', []) 
                           if log.get('category') == 'VALIDATION' 
                           and log.get('level') == 'ERROR']
        
        if validation_errors:
            print(f"🔍 VALIDATION ERRORS WITH DEBUG OUTPUT:")
            print("="*80)
            
            for i, log in enumerate(validation_errors):
                timestamp = log.get('timestamp', '')[11:19]  # Just time
                player = log.get('context', {}).get('current_player', 'Unknown')
                
                print(f"\n🚨 ERROR {i+1} - [{timestamp}] {player}")
                print(f"Message: {log.get('message')}")
                
                # Show debug output if available
                debug_output = log.get('context', {}).get('full_debug_output')
                if debug_output:
                    print("\n🔍 DEBUG OUTPUT:")
                    print("-" * 40)
                    print(debug_output)
                    print("-" * 40)
                else:
                    print("   (No debug output available)")
        else:
            print("✅ No validation errors found")
            
        # Show recent logs
        print(f"\n📋 RECENT LOGS:")
        print("="*40)
        for log in data.get('logs', [])[-5:]:  # Last 5 logs
            timestamp = log.get('timestamp', '')[11:19]
            level = log.get('level', 'INFO')
            message = log.get('message', '')[:60]
            print(f"[{timestamp}] {level}: {message}")
            
    except Exception as e:
        print(f"❌ Error reading file: {e}")

if __name__ == "__main__":
    view_latest_export()
