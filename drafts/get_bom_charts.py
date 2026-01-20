import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin

MSLP_URL = "https://www.bom.gov.au/australia/charts/synoptic_col.shtml"
SAT_URL = "https://www.bom.gov.au/australia/satellite/"
SAVE_DIR = "bom_images"
os.makedirs(SAVE_DIR, exist_ok=True)

# Fake a browser request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

response_1 = requests.get(MSLP_URL, headers=headers)
if response_1.status_code != 200:
    raise Exception(f"Failed to fetch page: {response_1.status_code}")
soup_1 = BeautifulSoup(response_1.text, "lxml")

response_2 = requests.get(SAT_URL, headers=headers)
if response_2.status_code != 200:
    raise Exception(f"Failed to fetch page: {response_2.status_code}")
soup_2 = BeautifulSoup(response_2.text, "lxml")

# Find all <img> tags with .png in src
png_links = []
for img in soup_1.find_all("img", src=True):
    src = img['src']
    filename = os.path.basename(src)
    if src.lower().endswith(".png") and filename.startswith("IDY"):
        full_url = urljoin(MSLP_URL, src)
        png_links.append(full_url)
for img in soup_2.find_all("img", src=True):
    src = img['src']    
    filename = os.path.basename(src)
    if src.lower().endswith(".jpg"):
        full_url_2 = urljoin(SAT_URL, src)
        png_links.append(full_url_2)


if not png_links:
    print("No PNG links found on the page.")
else:
    print(f"Found {len(png_links)} PNG images. Downloading...")

for link in png_links:
    filename = os.path.join(SAVE_DIR, link.split("/")[-1])
    print(f"Downloading {link} → {filename}")
    r = requests.get(link, headers=headers)
    if r.status_code == 200:
        with open(filename, "wb") as f:
            f.write(r.content)
    else:
        print(f"Failed to download {link}: {r.status_code}")

print("Download complete.")

