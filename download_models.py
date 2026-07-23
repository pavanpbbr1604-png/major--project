import os
import urllib.request

def download_file(url, dest_path):
    print(f"Downloading {url} to {dest_path}...")
    
    # Progress callback
    def report_hook(block_num, block_size, total_size):
        read_so_far = block_num * block_size
        if total_size > 0:
            percent = read_so_far * 1e2 / total_size
            s = f"\rProgress: {percent:.1f}% ({read_so_far / (1024*1024):.1f} MB of {total_size / (1024*1024):.1f} MB)"
            print(s, end="")
        else:
            print(f"\rDownloaded {read_so_far / (1024*1024):.1f} MB", end="")
            
    urllib.request.urlretrieve(url, dest_path, reporthook=report_hook)
    print("\nDownload complete.")

def main():
    models_dir = "models"
    os.makedirs(models_dir, exist_ok=True)
    
    # Model URLs
    model_urls = {
        "yolov8s.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.pt",
        "yolov8x.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8x.pt"
    }
    
    for filename, url in model_urls.items():
        dest = os.path.join(models_dir, filename)
        if not os.path.exists(dest):
            try:
                download_file(url, dest)
            except Exception as e:
                print(f"Error downloading {filename}: {e}")
        else:
            print(f"{filename} already exists at {dest}.")

if __name__ == "__main__":
    main()
