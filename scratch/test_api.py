import requests
import os

def test_api():
    print("=== TESTING FLASK WEB API ===")
    
    url = "http://localhost:5000/analyze?tiled=true&imgsz=2560"
    file_path = "test_image1.jpg"
    
    if not os.path.exists(file_path):
        print(f"[ERROR] Test image {file_path} not found locally.")
        return
        
    try:
        with open(file_path, "rb") as img_file:
            files = {"image": img_file}
            print(f"Uploading {file_path} to {url}...")
            response = requests.post(url, files=files)
            
        print(f"HTTP Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("API Response Summary:")
            print(f"  Status: {result.get('status')}")
            print(f"  Filename: {result.get('filename')}")
            print(f"  Count: {result.get('counting', {}).get('total_count')}")
            print(f"  Density: {result.get('density', {}).get('density_percentage'):.2f}%")
            print(f"  Reliability Score: {result.get('reliability', {}).get('reliability_score'):.4f}")
            print(f"  Crowd Level: {result.get('classification', {}).get('crowd_level')}")
            print("[PASS] End-to-end Flask API and pipeline execution successful!")
        else:
            print(f"[FAIL] Server returned error: {response.text}")
    except Exception as e:
        print(f"[FAIL] Request failed: {e}")

if __name__ == "__main__":
    test_api()
