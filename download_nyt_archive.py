import requests
import json
import os
from datetime import datetime

# NYT API Key
API_KEY = "MsCFSc7Yeb0oeBYmyNif0zgjTNX7Y2Gwq8MAlzRSt2URHvd6"
BASE_URL = "https://api.nytimes.com/svc/archive/v1"

def download_nyt_archive(year, month, output_dir="nyt_archives"):
    """
    Download NYT archive data for a specific year and month.
    
    Args:
        year (int): Year (e.g., 2024)
        month (int): Month (1-12)
        output_dir (str): Directory to save JSON files
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    # Validate month
    if month < 1 or month > 12:
        print(f"Error: Month must be between 1 and 12, got {month}")
        return False
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    
    # Construct URL
    url = f"{BASE_URL}/{year}/{month}.json?api-key={API_KEY}"
    
    # Construct filename
    filename = f"{output_dir}/{year}_{month:02d}.json"
    
    try:
        print(f"Downloading NYT archive for {year}-{month:02d}...")
        response = requests.get(url, timeout=30)
        
        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
            
            # Save to file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Print summary
            if 'response' in data and 'docs' in data['response']:
                article_count = len(data['response']['docs'])
                print(f"✓ Successfully downloaded {article_count} articles")
                print(f"✓ Saved to: {filename}")
            else:
                print(f"✓ Downloaded data saved to: {filename}")
            
            return True
        else:
            print(f"Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return False
    except IOError as e:
        print(f"Error saving file: {e}")
        return False


def download_range(start_year, start_month, end_year, end_month, output_dir="nyt_archives"):
    """
    Download NYT archive data for a range of months.
    
    Args:
        start_year (int): Starting year
        start_month (int): Starting month (1-12)
        end_year (int): Ending year
        end_month (int): Ending month (1-12)
        output_dir (str): Directory to save JSON files
    """
    
    current_year = start_year
    current_month = start_month
    success_count = 0
    fail_count = 0
    
    while True:
        if download_nyt_archive(current_year, current_month, output_dir):
            success_count += 1
        else:
            fail_count += 1
        
        # Check if we've reached the end
        if current_year == end_year and current_month == end_month:
            break
        
        # Move to next month
        if current_month == 12:
            current_year += 1
            current_month = 1
        else:
            current_month += 1
    
    print(f"\n--- Download Summary ---")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")


if __name__ == "__main__":
    # import sys
    #
    # if len(sys.argv) < 3:
    #     print("Usage:")
    #     print("  Single month: python download_nyt_archive.py <year> <month>")
    #     print("  Date range:   python download_nyt_archive.py <start_year> <start_month> <end_year> <end_month>")
    #     print("\nExample:")
    #     print("  python download_nyt_archive.py 2024 1          # Download January 2024")
    #     print("  python download_nyt_archive.py 2024 1 2024 3   # Download Jan-Mar 2024")
    #     sys.exit(1)
    
    try:
        # if len(sys.argv) == 3:
        #     # Single month
        #     year = int(sys.argv[1])
        #     month = int(sys.argv[2])
        #     download_nyt_archive(year, month)
        #
        # elif len(sys.argv) == 5:
        #     # Date range
        #     start_year = int(sys.argv[1])
        #     start_month = int(sys.argv[2])
        #     end_year = int(sys.argv[3])
        #     end_month = int(sys.argv[4])
        #     download_range(start_year, start_month, end_year, end_month)
        #
        # else:
        #     print("Invalid number of arguments")
        #     sys.exit(1)
        download_range(2016, 3, 2026, 3)
    except ValueError as e:
        print(f"Error: Invalid arguments. {e}")
        # sys.exit(1)
