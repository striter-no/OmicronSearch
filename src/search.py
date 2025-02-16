from googlesearch import search as googleSearch
import aiohttp
from aiohttp_socks import ProxyConnector
import asyncio
from bs4 import BeautifulSoup
from colorama import Fore
from typing import Dict, Any

class GoogleSearcher():
    def __init__(self):
        pass

    async def _fetch_url_content(
        self,
        session: aiohttp.ClientSession,
        url: str,
        proxy: dict[str, Any],
        index: int
    ) -> tuple[str, str]:
        # print(f"\r{Fore.LIGHTBLUE_EX}--> Gaining site: #{index}{Fore.RESET}", end="")
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return url, ""

                html_content = await response.text()
                
                # Создаем объект BeautifulSoup
                soup = BeautifulSoup(html_content, "html.parser")
                
                # Удаляем все скрипты и стили
                for script in soup(["script", "style"]):
                    script.decompose()
                    
                # Получаем текст и очищаем его
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                text = ' '.join(chunk for chunk in lines if chunk)
                # print(f"\r{Fore.LIGHTBLUE_EX}--> Gained site: #{index}{Fore.RESET}", end=" "*15)
                return url, text
        except Exception as ex:
            # print(f"\nError while getting {url}: {str(ex)}")
            return url, ""

    async def search(
        self,
        query: str,
        num_results: int,
        advanced_mode: bool = False,
        proxy: dict[str, Any] = {}
    ) -> dict[str, str]:
        results: dict[str, str] = {}
        urls = list(googleSearch(query.strip().strip('"'), num_results=num_results, advanced=advanced_mode))
        
        # Создаем connector для SOCKS прокси
        proxy_url = f"{proxy['protocol']}://{proxy['user']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}"
        connector = ProxyConnector.from_url(proxy_url)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [
                self._fetch_url_content(session, url, proxy, i+1)
                for i, url in enumerate(urls)
            ]
            completed = await asyncio.gather(*tasks)
            
            results = dict(completed)
        
        # print("\rGained all sites")
        return results