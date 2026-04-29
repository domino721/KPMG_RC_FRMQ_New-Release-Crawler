import requests
import json
import os
import time
import datetime
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from bs4 import BeautifulSoup

# Selenium setup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# For robust requests with retries
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    options.add_argument('--disable-blink-features=AutomationControlled')

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"Driver Init Error: {e}")
        return None

class JsonStorage:
    def __init__(self, filepath: str = "history.json"):
        self.filepath = filepath
        self.seen_items: Dict[str, Dict[str, str]] = self._load()

    def _load(self) -> Dict[str, Dict[str, str]]:
        if not os.path.exists(self.filepath):
            return {}
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {item: {'date': '', 'title': ''} for item in data}
                elif isinstance(data, dict):
                    converted_data = {}
                    for item_id, value in data.items():
                        if isinstance(value, str):
                            converted_data[item_id] = {'date': value, 'title': ''}
                        elif isinstance(value, dict) and 'date' in value:
                            converted_data[item_id] = {'date': value.get('date', ''), 'title': value.get('title', '')}
                        else:
                            converted_data[item_id] = {'date': '', 'title': ''}
                    return converted_data
                return {}
        except (json.JSONDecodeError, IOError):
            return {}

    def save(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.seen_items, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Error saving history: {e}")

    def is_new(self, item_id: str, current_date_str: str, current_title_str: str) -> bool:
        if item_id not in self.seen_items:
            return True
        stored_item_data = self.seen_items[item_id]
        stored_date = stored_item_data.get('date', '')
        stored_title = stored_item_data.get('title', '')
        if stored_date != current_date_str or stored_title != current_title_str:
            return True
        return False

    def add(self, item_id: str, current_date_str: str, current_title_str: str):
        self.seen_items[item_id] = {'date': current_date_str, 'title': current_title_str}

class ConsoleNotifier:
    def notify(self, source: str, items: List[Dict[str, Any]]):
        for item in items:
            title = item.get('title', 'No Title')
            link = item.get('link', 'No Link')
            date = item.get('date', 'Unknown Date')
            message = (
                f"\n[NEW ALERT] Source: {source}\n"
                f"Title: {title}\n"
                f"Date: {date}\n"
                f"Link: {link}\n"
                f"{'-'*40}"
            )
            print(message)

class EmailNotifier(ConsoleNotifier):
    def __init__(self, sender_email: str, sender_password: str, recipient_emails: List[str]):
        super().__init__()
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_emails = recipient_emails
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def notify(self, source: str, new_items: List[Dict[str, Any]], filtered_out_items: List[Dict[str, Any]] = None):
        if filtered_out_items is None:
            filtered_out_items = []

        if new_items:
            for item in new_items:
                super().notify(item.get('source', source), [item])

        msg = MIMEMultipart()
        msg['From'] = self.sender_email

        num_new_items = len(new_items)
        num_filtered_out_items = len(filtered_out_items)

        if not new_items:
            subject = "[알림] 오늘자, 새로운 ESG 및 AI 관련 소식이 없습니다."
        else:
            subject_parts = []
            if num_new_items > 0:
                subject_parts.append(f"{num_new_items} 건 탐색")
            if num_filtered_out_items > 0:
                subject_parts.append(f"{num_filtered_out_items} 건 참고자료")
            subject = f"[알림] {source}: {', '.join(subject_parts)}"

        html_body_content = """
        <html>
        <head>
            <style>
                body { font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', '맑은 고딕', '맑은 고딕(제목)', '맑은 고딕(본문)','KoPub돋움체 Medium', 'Apple Color Emoji', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; font-size: 14px; color: #333; line-height: 1.6; }
                ul { list-style-type: none; padding: 0; margin: 0; }
                li { margin-bottom: 8px; }
                a { color: #0056b3; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .date { font-size: 12px; color: #777; margin-left: 10px; }
                .footer { margin-top: 30px; font-size: 12px; color: #888; border-top: 1px solid #eee; padding-top: 15px; text-align: center; }
                .main-section { margin-bottom: 25px; padding: 15px; border: 2px solid #555; border-radius: 8px; background-color: #f9f9f9; }
                .main-section-title { font-size: 16px; font-weight: bold; color: #333; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
                .reference-section { margin-top: 25px; border-top: 1px dashed #ccc; padding-top: 20px; }
                .reference-section-title { font-size: 15px; font-weight: bold; color: #555; margin-bottom: 10px; }
            </style>
        </head>
        <body>
        """

        if new_items:
            html_body_content += """
            <div style="font-size: 18px; font-weight: bold; margin-bottom: 20px; color: #000;"> ESG 관련 주요기관 최신 보도자료:</div>
            """
            grouped_new_items: Dict[str, List[Dict[str, Any]]] = {}
            for item in new_items:
                item_source = item.get('source', 'Unknown Source')
                if item_source not in grouped_new_items:
                    grouped_new_items[item_source] = []
                grouped_new_items[item_source].append(item)

            for item_source, source_items in grouped_new_items.items():
                source_items.sort(key=lambda x: x.get('date', ''), reverse=True)
                html_body_content += f"""
                <div class="main-section">
                    <div class="main-section-title">{item_source}</div>
                    <ul>
                """
                for item in source_items:
                    title = item.get('title', 'No Title')
                    link = item.get('link', 'No Link')
                    date = item.get('date', 'Unknown Date')
                    html_body_content += f"""
                        <li> <span style="font-weight: bold;"><a href="{link}" style="color: #0056b3; text-decoration: none;">{title}</a></span> / <span style="font-size: 12px; color: #777;">{date}</span></li>
                    """
                html_body_content += """
                    </ul>
                </div>
                """
        else:
            html_body_content += """
            <div style="font-size: 16px; font-weight: bold; margin-bottom: 20px;">오늘자 주요기관 보도자료에서 새로운 ESG 및 AI 관련 소식이 없습니다.</div>
            """

        if filtered_out_items:
            html_body_content += """
            <div class="reference-section">
                <div class="reference-section-title">(참고) ESG & AI 외 보도자료 (금융위원회 / 금융감독원)</div>
                <ul>
            """
            filtered_out_items.sort(key=lambda x: x.get('date', ''), reverse=True)
            for item in filtered_out_items:
                title = item.get('title', 'No Title')
                link = item.get('link', 'No Link')
                html_body_content += f"""
                    <li style="font-size: 12px;"> <a href="{link}" style="color: #0056b3; text-decoration: none;">{title}</a></li>
                """
            html_body_content += """
                </ul>
            </div>
            """

        html_body_content += """
            <div class="footer">
                <p>--</p>
                <p>주요기관: 금융위원회, 금융감독원, PCAF Korea(Kosif), BCBS, PCAF, NGFS, FSB.</p>
            </div>
        </body>
        </html>
        """

        msg['Subject'] = subject
        msg.attach(MIMEText(html_body_content, 'html'))

        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            text = msg.as_string()
            for recipient_email in self.recipient_emails:
                msg['To'] = recipient_email
                server.sendmail(self.sender_email, recipient_email, text)
            server.quit()
            print(f"[EmailNotifier] Emails sent successfully.")
        except Exception as e:
            print(f"[EmailNotifier] Failed to send email: {e}")

class BaseScraper(ABC):
    def __init__(self, name: str):
        self.name = name
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = self._create_retrying_session()

    def _create_retrying_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _make_request(self, url: str, timeout: int = 20):
        try:
            response = self.session.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"[{self.name}] Request failed for {url}: {e}")
            return None

    @abstractmethod
    def get_new_items(self) -> List[Dict[str, Any]]:
        pass

class FsbScraper(BaseScraper):
    def __init__(self):
        super().__init__("FSB")
        self.url = "https://www.fsb.org/publications/?policy_area%5B%5D=15&policy_area%5B%5D=31"

    def get_new_items(self) -> List[Dict[str, Any]]:
        items = []
        unique_items_data: Dict[str, Dict[str, str]] = {}
        try:
            response = self._make_request(self.url)
            if response is None: return items
            soup = BeautifulSoup(response.content, 'html.parser')
            links = soup.find_all('a')
            for a in links:
                href = a.get('href')
                text = a.get_text(strip=True)
                if not href or len(text) < 5: continue
                full_link = href if href.startswith('http') else f"https://www.fsb.org{href}"
                if not re.search(r'/\d{4}/\d{2}/', full_link): continue
                date_from_url = ''
                match_url_date = re.search(r'/(\d{4})/(\d{2})/', full_link)
                if match_url_date:
                    y, m = match_url_date.groups()
                    date_from_url = f"{y}-{m}-01"
                date_from_text = ''
                parent_to_search = a.find_parent()
                for _ in range(5):
                    if not parent_to_search: break
                    block_text = parent_to_search.get_text(" ", strip=True)
                    match = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})', block_text, re.IGNORECASE)
                    if match:
                         try:
                             d_str = f"{match.group(1)} {match.group(2)} {match.group(3)}"
                             try: parsed = datetime.datetime.strptime(d_str, "%d %B %Y")
                             except ValueError:
                                 try: parsed = datetime.datetime.strptime(d_str, "%d %b %Y")
                                 except ValueError: parsed = None
                             if parsed:
                                 date_from_text = parsed.strftime("%Y-%m-%d")
                                 break
                         except: pass
                    parent_to_search = parent_to_search.parent
                current_item_date = date_from_text if date_from_text else date_from_url
                if full_link not in unique_items_data:
                    unique_items_data[full_link] = {'title': text, 'date': current_item_date}
                else:
                    if len(text) > len(unique_items_data[full_link]['title']):
                         unique_items_data[full_link]['title'] = text
            for link, data in unique_items_data.items():
                items.append({'id': link, 'title': data['title'], 'link': link, 'date': data['date']})
        except Exception as e:
            print(f"Error scraping FSB: {e}")
        return items

class BcbsScraper(BaseScraper):
    def __init__(self):
        super().__init__("BCBS")
        self.url = "https://www.bis.org/bcbs/publications.htm?m=75&topics=Climate-related+financial+risks&topics=Disclosure"

    def get_new_items(self) -> List[Dict[str, Any]]:
        items = []
        driver = get_driver()
        if not driver: return items
        try:
            driver.get(self.url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "tr")))
            time.sleep(3)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            rows = soup.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if not cells: continue
                date_str = ''
                if len(cells) > 0:
                    text = cells[0].get_text(strip=True)
                    try:
                        parsed = datetime.datetime.strptime(text, "%d %b %Y")
                        date_str = parsed.strftime("%Y-%m-%d")
                    except: pass
                a_tag = row.find('a')
                if not a_tag: continue
                href = a_tag.get('href')
                if not href: continue
                if '/publ/' in href or '/bcbs/' in href:
                    title = a_tag.get_text(strip=True)
                    if len(title) > 10:
                        full_link = href if href.startswith('http') else f"https://www.bis.org{href}"
                        items.append({'id': full_link, 'title': title, 'link': full_link, 'date': date_str})
        except Exception as e:
            print(f"Error scraping BCBS: {e}")
        finally:
            driver.quit()
        return items

class NgfsScraper(BaseScraper):
    def __init__(self):
        super().__init__("NGFS")
        self.url = "https://www.ngfs.net/en/press-release"

    def get_new_items(self) -> List[Dict[str, Any]]:
        items = []
        try:
            response = self._make_request(self.url)
            if response is None: return items
            soup = BeautifulSoup(response.content, 'html.parser')
            links = soup.find_all('a', href=True)
            seen_links = set()
            for a in links:
                href = a.get('href')
                text = a.get_text(strip=True)
                if not href or not text or "/en/press-release/" not in href or "?page=" in href: continue
                if href in seen_links: continue
                seen_links.add(href)
                full_link = href if href.startswith('http') else f"https://www.ngfs.net{href}"
                date_str = ''
                parent = a.find_parent()
                for _ in range(5):
                    if not parent: break
                    block_text = parent.get_text(" ", strip=True)
                    match = re.search(r'(\d{1,2})(?:st|nd|rd|th)? of (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{4})', block_text, re.IGNORECASE)
                    if match:
                        try:
                            d_str = f"{match.group(1)} {match.group(2)} {match.group(3)}"
                            parsed_date = datetime.datetime.strptime(d_str, "%d %b %Y")
                            date_str = parsed_date.strftime("%Y-%m-%d")
                            break
                        except: pass
                    parent = parent.parent
                if date_str == '':
                    match_year = re.search(r'(202[3-9])', text)
                    if match_year: date_str = f"{match_year.group(1)}-01-01"
                items.append({'id': full_link, 'title': text, 'link': full_link, 'date': date_str})
        except Exception as e:
            print(f"Error scraping NGFS: {e}")
        return items

class PcafScraper(BaseScraper):
    def __init__(self):
        super().__init__("PCAF")
        self.url = "https://carbonaccountingfinancials.com/en/resources#resources"

    def get_new_items(self) -> List[Dict[str, Any]]:
        items = []
        try:
            response = self._make_request(self.url)
            if response is None: return items
            soup = BeautifulSoup(response.content, 'html.parser')
            links = soup.find_all('a')
            for a in links:
                title = a.get_text(strip=True)
                link = a.get('href')
                if not link or not title: continue
                if any(k in title.lower() for k in ["financed emissions", "facilitated emissions", "standard"]) or "/en/video/" in link:
                    full_link = link if link.startswith('http') else f"https://carbonaccountingfinancials.com{link}"
                    date_str = ''
                    match = re.search(r'\((\d{4})\)', title)
                    if match: date_str = f"{match.group(1)}-01-01"
                    else:
                        video_date_match = re.search(r'/video/(\d{4})-\w+', link)
                        if video_date_match: date_str = f"{video_date_match.group(1)}-01-01"
                    items.append({'id': full_link, 'title': title, 'link': full_link, 'date': date_str})
        except Exception as e:
            print(f"Error scraping PCAF: {e}")
        return items

class KosifScraper(BaseScraper):
    def __init__(self):
        super().__init__("PCAF Korea (Kosif)")
        self.url = "https://kosif.org/bbs/board.php?bo_table=s2_9_2"

    def get_new_items(self) -> List[Dict[str, Any]]:
        items = []
        driver = get_driver()
        if not driver: return items
        try:
            driver.get(self.url)
            time.sleep(15)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            rows = soup.find_all('tr')
            for row in rows:
                link_tag = row.find('a', href=True)
                if not link_tag or 'wr_id=' not in link_tag.get('href'): continue
                href = link_tag.get('href')
                date_str = ''
                cells = row.find_all('td')
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if (len(text) == 10 or len(text) == 8) and ('-' in text or '.' in text):
                        sep = '-' if '-' in text else '.'
                        parts = text.split(sep)
                        if len(parts) == 3 and all(p.isdigit() for p in parts):
                            year = parts[0] if len(parts[0]) == 4 else '20' + parts[0]
                            date_str = f"{year}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
                            break
                items.append({'id': href, 'title': link_tag.get_text(strip=True), 'link': href, 'date': date_str})
        except Exception as e:
            print(f"Error scraping Kosif: {e}")
        finally:
            driver.quit()
        return items

class FscScraper(BaseScraper):
    def __init__(self):
        super().__init__("금융위원회")
        self.url = "https://www.fsc.go.kr/no010101"

    def get_new_items(self) -> List[Dict[str, Any]]:
        items = []
        try:
            response = self._make_request(self.url)
            if response is None: return items
            soup = BeautifulSoup(response.content, 'html.parser')
            links = soup.find_all('a', href=True)
            seen_links = set()
            for a in links:
                href = a.get('href')
                if not href or '/no010101/' not in href: continue
                path_part = href.split('?')[0]
                if not path_part.split('/')[-1].isdigit() or href in seen_links: continue
                seen_links.add(href)
                title = a.get_text(strip=True)
                if not title: continue
                full_link = href if href.startswith('http') else f"https://www.fsc.go.kr{href}"
                date_str = ''
                row_container = a.find_parent('tr')
                if row_container:
                    row_text = row_container.get_text(" ", strip=True)
                    match = re.search(r'(\d{4}[-.]\d{2}[-.]\d{2})', row_text)
                    if match: date_str = match.group(1).replace('.', '-')
                items.append({'id': full_link, 'title': title, 'link': full_link, 'date': date_str})
        except Exception as e:
            print(f"Error scraping FSC: {e}")
        return items

class FssScraper(BaseScraper):
    def __init__(self):
        super().__init__("금융감독원")
        self.url = "https://www.fss.or.kr/fss/bbs/B0000188/list.do?menuNo=200218"

    def get_new_items(self) -> List[Dict[str, Any]]:
        items = []
        try:
            response = self._make_request(self.url)
            if response is None: return items
            soup = BeautifulSoup(response.content, 'html.parser')
            rows = soup.find_all('tr')
            for row in rows:
                link_tag = row.find('a', href=True)
                if not link_tag or 'view.do' not in link_tag.get('href') or 'nttId=' not in link_tag.get('href'): continue
                href = link_tag.get('href')
                title = link_tag.get_text(strip=True)
                full_link = href if href.startswith('http') else f"https://www.fss.or.kr{href}"
                date_str = ''
                cells = row.find_all('td')
                for cell in cells:
                    text = cell.get_text(strip=True)
                    match = re.search(r'(\d{4}[-.]\d{2}[-.]\d{2})', text)
                    if match:
                        date_str = match.group(1).replace('.', '-')
                        break
                items.append({'id': full_link, 'title': title, 'link': full_link, 'date': date_str})
        except Exception as e:
            print(f"Error scraping FSS: {e}")
        return items

def job():
    print(f"[{datetime.datetime.now()}] Starting crawler job...")
    history_file = os.getenv('HISTORY_FILE', 'history.json')
    storage = JsonStorage(filepath=history_file)
    
    sender_email = os.getenv('GMAIL_USER')
    sender_password = os.getenv('GMAIL_APP_PASSWORD')
    recipients_str = os.getenv('RELEASE_CRAWLER_RECIPIENTS')
    recipient_emails = [email.strip() for email in recipients_str.split(',')] if recipients_str else []

    if not recipient_emails:
        # Fallback to hardcoded list if env var is not set (optional)
        recipient_emails = [
            "noheulhong@kr.kpmg.com", "taeyikim@kr.kpmg.com", "yurimkoo@kr.kpmg.com",
            "inhyelee@kr.kpmg.com", "taemusun@kr.kpmg.com", "woochuljung@kr.kpmg.com",
            "minhocho@kr.kpmg.com"
        ]

    notifiers = [ConsoleNotifier()]
    email_notifier = None
    if sender_email and sender_password and recipient_emails:
        email_notifier = EmailNotifier(sender_email, sender_password, recipient_emails)
        print("[EmailNotifier] Email notifications are ENABLED.")
    else:
        print("[EmailNotifier] Email credentials not fully configured. Skipping email notifications.")

    scrapers = [FscScraper(), FssScraper(), KosifScraper(), BcbsScraper(), PcafScraper(), NgfsScraper(), FsbScraper()]
    all_new_items_consolidated = []
    all_filtered_out_items_consolidated = []
    keywords_for_fss_fsc = ["ESG", "기후", "전환", "녹색", "택소노미", "Taxonomy", "NDC", "탄소", "AI", "인공지능", "모형", "리스크", "Risk", "RMF", "MRM", "빅데이터", "데이터", "ML", "모델", "머신러닝", "DL", "딥러닝", "심사", "대출"]

    for scraper in scrapers:
        try:
            items = scraper.get_new_items()
            print(f"[{scraper.name}] Found {len(items)} items.")
            items_to_email_for_current_scraper = []
            for item in items:
                item_id = item.get('id') or item.get('link')
                item_date = item.get('date', '')
                original_item_title = item.get('title', '')
                cleaned_title = re.sub(r'금일\s*등록된\s*게시글', '', original_item_title).strip()
                item['title'] = cleaned_title
                if not item_id: continue

                if storage.is_new(item_id, item_date, cleaned_title):
                    item['source'] = scraper.name
                    for notifier in notifiers:
                        notifier.notify(scraper.name, [item])

                    if scraper.name in ["금융위원회", "금융감독원"]:
                        matched_keyword = any(k.lower() in cleaned_title.lower() for k in keywords_for_fss_fsc)
                        if matched_keyword:
                            items_to_email_for_current_scraper.append(item)
                        else:
                            all_filtered_out_items_consolidated.append(item)
                    else:
                        items_to_email_for_current_scraper.append(item)
                    storage.add(item_id, item_date, cleaned_title)

            all_new_items_consolidated.extend(items_to_email_for_current_scraper)
        except Exception as e:
            print(f"Error checking {scraper.name}: {e}")

    if email_notifier:
        email_notifier.notify('주요기관 보도자료', all_new_items_consolidated, all_filtered_out_items_consolidated)

    storage.save()
    print("Job finished.")

if __name__ == "__main__":
    job()
