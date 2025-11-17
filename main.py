# main.py - Disaster News Extraction Pipeline (Updated)
import subprocess
import argparse
import sys
import json
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='Disaster news extraction pipeline for climate impact monitoring')
    
    # Original parameters (backward compatibility)
    parser.add_argument('--date', type=str, 
                      help='Target date in YYYY-MM-DD format (default: current date)')
    parser.add_argument('--days-back', type=int, default=0, 
                      help='Number of days to look back from target date (default: 0)')
    parser.add_argument('--state', type=str, 
                      help='Process only this single state/UT (e.g., kerala, maharashtra, delhi)')
    parser.add_argument('--skip-folders', action='store_true', 
                      help='Skip folder creation step')
    parser.add_argument('--skip-extraction', action='store_true', 
                      help='Skip article content extraction step')
    
    # NEW PARAMETERS for flexible disaster extraction
    parser.add_argument('--hazard-name', type=str,
                      help='Name of the hazard/disaster (e.g., "Cyclone Example", "Flood", "Heatwave")')
    parser.add_argument('--locations-json', type=str,
                      help='JSON string with nested locations: {"State": {"districts": {"District": ["City1", "City2"]}}}')
    parser.add_argument('--keywords-json', type=str,
                      help='JSON string with language-specific keywords: {"en": ["word1", "word2"], "hi": ["शब्द1"]}')
    
    args = parser.parse_args()
    
    # Determine if we're using new flexible mode or old monsoon mode
    using_flexible_mode = all([args.hazard_name, args.locations_json, args.keywords_json])
    
    if using_flexible_mode:
        print(f"🎯 Starting Flexible Disaster Extraction Pipeline")
        print(f"📋 Hazard: {args.hazard_name}")
        
        # Validate and parse JSON inputs
        try:
            locations = json.loads(args.locations_json)
            keywords = json.loads(args.keywords_json)
            
            print(f"📍 States: {list(locations.keys())}")
            print(f"🗣️  Languages: {list(keywords.keys())}")
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON format: {e}")
            print("\nExample locations format:")
            print('{"Telangana": {"districts": {"Warangal": ["Kazipet"], "Hyderabad": ["Hyderabad"]}}}')
            print("\nExample keywords format:")
            print('{"en": ["cyclone", "flood"], "hi": ["चक्रवात", "बाढ़"]}')
            sys.exit(1)
            
    else:
        print("🌧️ Starting Monsoon News Extraction Pipeline (Legacy Mode)")
        print(f"📅 Target date: {args.date if args.date else 'Current date'}")
        print(f"📅 Days back: {args.days_back}")
        if args.state:
            print(f"🎯 Single state mode: {args.state}")
    
    # Validate date format if provided
    if args.date:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print("❌ Invalid date format. Please use YYYY-MM-DD")
            sys.exit(1)
    
    try:
        # Step 1: Create required folders (unless skipped)
        if not args.skip_folders:
            print("\n📁 Step 1: Creating folder structure...")
            subprocess.run(["python", "utils.py"], check=True)
            print("✅ Folder structure created")
        else:
            print("\n📁 Step 1: Skipping folder creation")
        
        # Step 2: Run news collection
        if using_flexible_mode:
            print(f"\n🎯 Step 2: Running flexible disaster news collection...")
        else:
            print(f"\n🌧️ Step 2: Running monsoon news collection...")
            
        cmd = ["python", "monsoon.py"]
        
        # Add original parameters
        if args.date:
            cmd.extend(["--date", args.date])
        if args.days_back > 0:
            cmd.extend(["--days-back", str(args.days_back)])
        if args.state:
            cmd.extend(["--state", args.state])
        
        # Add new flexible parameters
        if using_flexible_mode:
            cmd.extend(["--hazard-name", args.hazard_name])
            cmd.extend(["--locations-json", args.locations_json])
            cmd.extend(["--keywords-json", args.keywords_json])
        
        subprocess.run(cmd, check=True)
        print("✅ News collection completed")
        
        # Step 3: Extract full articles (unless skipped)
        if not args.skip_extraction:
            print(f"\n📰 Step 3: Extracting full article content...")
            subprocess.run(["python", "extract_articles.py"], check=True)
            print("✅ Article content extraction completed")
        else:
            print("\n📰 Step 3: Skipping article content extraction")
        
        print(f"\n🎉 Pipeline completed successfully!")
        
        # Show output locations
        if not args.skip_extraction:
            today = datetime.now().strftime('%Y-%m-%d')
            print(f"\n📁 Output locations:")
            print(f"   📂 Daily articles: JSON Output/{today}/articles_combined.json")
            print(f"   📂 Detailed data: JSON Output Spare/{today}/")
            if using_flexible_mode:
                print(f"   📂 CSV data: data/[states|union-territories]/[region]/{args.hazard_name}/")
            else:
                print(f"   📂 CSV data: data/[states|union-territories]/[region]/Monsoon/")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running subprocess: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n⚠️ Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
