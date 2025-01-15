import requests
from bs4 import BeautifulSoup
import os
import re
import zipfile
from io import BytesIO
from urllib.parse import urljoin, urlparse
import time

def sanitize_filename(filename):
    """清理文件名，移除非法字符."""
    return re.sub(r'[\\/:*?"<>|]', "", filename)

def download_image(image_url, output_dir, i, max_retries=3, timeout=30):
    """下载单个图片，带有重试机制."""
    for attempt in range(max_retries):
        try:
            img_response = requests.get(image_url, stream=True, timeout=timeout)
            img_response.raise_for_status()

            # 获取图片文件名
            parsed_url = urlparse(image_url)
            image_name = os.path.basename(parsed_url.path)
            if not image_name:
                image_name = f"image_{i+1}"

            # 提取文件扩展名
            _, ext = os.path.splitext(image_name)
            if not ext:
                content_type = img_response.headers.get('content-type', '')
                if content_type.startswith('image/jpeg'):
                    ext = '.jpg'
                elif content_type.startswith('image/png'):
                    ext = '.png'
                elif content_type.startswith('image/gif'):
                    ext = '.gif'
                else:
                    ext = '.jpg'  # 默认jpg

            # 构建保存的文件名
            filename = f"{i+1:03d}{ext}"
            file_path = os.path.join(output_dir, filename)

            with open(file_path, "wb") as f:
                for chunk in img_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"    Downloaded {filename}")
            return True  # 下载成功，返回True
        except requests.exceptions.RequestException as e:
            print(f"    Error downloading {image_url} (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                return False # 下载失败，返回False
    return False # 所有重试都失败，返回False

def download_images(url, output_dir):
    """下载网页中的所有图片，并按顺序编号."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # 检查请求是否成功

        soup = BeautifulSoup(response.content, "html.parser")
        images = soup.find_all("img")

        image_urls = []
        for img in images:
          src = img.get('src')
          if src:
            # 处理相对路径和绝对路径
            image_url = urljoin(url, src)
            image_urls.append(image_url)

        if not image_urls:
            print(f"  No images found on {url}")
            return False

        print(f"  Found {len(image_urls)} images on {url}")

        for i, image_url in enumerate(image_urls):
           download_image(image_url, output_dir, i)
        return True
    except requests.exceptions.RequestException as e:
        print(f"  Error accessing {url}: {e}")
        return False

def create_zip(output_dir, zip_filename):
    """将指定目录下的文件打包成zip文件."""
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, output_dir))

def main():
    """主函数，读取 web.txt 文件中的网址并处理."""
    try:
        with open("web.txt", "r") as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Error: web.txt file not found.")
        return

    for url in urls:
        print(f"Processing: {url}")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.text.strip()
                title = sanitize_filename(title) # 清理标题
            else:
                title = "untitled"
        except requests.exceptions.RequestException as e:
            print(f"  Error getting title for {url}: {e}")
            title = "untitled"

        output_dir = f"{title}_images"
        os.makedirs(output_dir, exist_ok=True)
        if download_images(url, output_dir):
            zip_filename = f"{title}.zip"
            create_zip(output_dir, zip_filename)
            print(f"  Created {zip_filename}")
            # 清理临时文件夹
            for root, _, files in os.walk(output_dir, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                os.rmdir(root)
        else:
            print(f"  Skipping ZIP creation for {url}")

if __name__ == "__main__":
    main()
